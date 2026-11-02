import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.ticket import (
    AssignRequest,
    MessageCreate,
    MessageRead,
    PriorityChange,
    StatusChange,
    TicketCreate,
    TicketDetail,
    TicketSummary,
)
from app.services import order_service, ticket_service
from app.services.access import sees_everything
from app.services.ticket_state import InvalidTransitionError

router = APIRouter(prefix="/tickets", tags=["tickets"])

# Support staff only. Anyone else gets 403, because the endpoint exists but not for their role.
STAFF = require_role(UserRole.AGENT, UserRole.ADMIN)


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


def _cannot_manage() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the assigned agent or an admin can do this",
    )


def _detail(ticket: Ticket, user: User) -> TicketDetail:
    """The full ticket, plus the status buttons this user may use."""
    detail = TicketDetail.model_validate(ticket)
    return detail.model_copy(
        update={
            "allowed_next_statuses": ticket_service.allowed_status_changes(ticket, user)
        }
    )


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    """A logged-in customer opens a ticket for one of their own orders."""
    try:
        ticket = ticket_service.create_ticket(db, current_user, data)
    except order_service.OrderNotFoundError:
        raise _not_found("Order") from None
    except ticket_service.ActiveTicketExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order already has an open ticket",
        ) from None
    return _detail(ticket, current_user)


@router.get("", response_model=Page[TicketSummary])
def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    assigned_to: Literal["me", "unassigned"] | None = None,
    q: str | None = Query(default=None, max_length=100),
    sort: Literal["newest", "oldest", "updated", "priority"] = "newest",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Customers see their own tickets. Agents and admins see all of them.

    Filtering, sorting and paging all happen in the database.
    """
    if assigned_to is not None and not sees_everything(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only support staff can filter by assignee",
        )
    filters = ticket_service.TicketFilters(
        status=status_filter,
        priority=priority,
        assigned_to=assigned_to,
        search=q,
        sort=sort,
    )
    tickets, total = ticket_service.list_tickets(
        db, current_user, filters, limit, offset
    )
    return Page[TicketSummary](
        items=[TicketSummary.model_validate(ticket) for ticket in tickets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        ticket = ticket_service.get_ticket(db, current_user, ticket_id)
    except ticket_service.TicketNotFoundError:
        # same answer for "not yours" and "does not exist"
        raise _not_found("Ticket") from None
    return _detail(ticket, current_user)


@router.post(
    "/{ticket_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    ticket_id: uuid.UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return ticket_service.add_message(db, current_user, ticket_id, data.body)
    except ticket_service.TicketNotFoundError:
        raise _not_found("Ticket") from None
    except ticket_service.TicketClosedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This ticket is closed"
        ) from None
    except ticket_service.ActiveTicketExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another ticket is already open for this order",
        ) from None


@router.post("/{ticket_id}/assign", response_model=TicketDetail)
def assign_ticket(
    ticket_id: uuid.UUID,
    data: AssignRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF),
):
    """Take a ticket. An agent can only assign it to themselves; an admin may name anyone."""
    agent_id = data.agent_id if data else None
    try:
        ticket = ticket_service.assign_ticket(db, current_user, ticket_id, agent_id)
    except ticket_service.TicketNotFoundError:
        raise _not_found("Ticket") from None
    except ticket_service.AssignNotAllowedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can assign a ticket to someone else",
        ) from None
    except ticket_service.InvalidAssigneeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That user cannot be assigned tickets",
        ) from None
    except ticket_service.AlreadyAssignedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ticket is already assigned to another agent",
        ) from None
    return _detail(ticket, current_user)


@router.post("/{ticket_id}/unassign", response_model=TicketDetail)
def unassign_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF),
):
    """Give a ticket back to the queue."""
    try:
        ticket = ticket_service.unassign_ticket(db, current_user, ticket_id)
    except ticket_service.TicketNotFoundError:
        raise _not_found("Ticket") from None
    except ticket_service.NotTicketManagerError:
        raise _cannot_manage() from None
    return _detail(ticket, current_user)


@router.post("/{ticket_id}/status", response_model=TicketDetail)
def change_status(
    ticket_id: uuid.UUID,
    data: StatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF),
):
    """Move a ticket along the status flow. The state machine decides what is allowed."""
    try:
        ticket = ticket_service.change_ticket_status(
            db, current_user, ticket_id, data.status
        )
    except ticket_service.TicketNotFoundError:
        raise _not_found("Ticket") from None
    except ticket_service.NotTicketManagerError:
        raise _cannot_manage() from None
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from None
    return _detail(ticket, current_user)


@router.patch("/{ticket_id}/priority", response_model=TicketDetail)
def change_priority(
    ticket_id: uuid.UUID,
    data: PriorityChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(STAFF),
):
    try:
        ticket = ticket_service.change_ticket_priority(
            db, current_user, ticket_id, data.priority
        )
    except ticket_service.TicketNotFoundError:
        raise _not_found("Ticket") from None
    except ticket_service.NotTicketManagerError:
        raise _cannot_manage() from None
    return _detail(ticket, current_user)
