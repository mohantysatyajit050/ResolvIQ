import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.ticket import TicketStatus
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.ticket import (
    MessageCreate,
    MessageRead,
    TicketCreate,
    TicketDetail,
    TicketSummary,
)
from app.services import order_service, ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _not_found(what: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{what} not found")


@router.post("", response_model=TicketDetail, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    """A logged-in customer opens a ticket for one of their own orders."""
    try:
        return ticket_service.create_ticket(db, current_user, data)
    except order_service.OrderNotFoundError:
        raise _not_found("Order") from None
    except ticket_service.ActiveTicketExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order already has an open ticket",
        ) from None


@router.get("", response_model=Page[TicketSummary])
def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Customers see their own tickets. Agents and admins see all of them."""
    tickets, total = ticket_service.list_tickets(
        db, current_user, status_filter, limit, offset
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
        return ticket_service.get_ticket(db, current_user, ticket_id)
    except ticket_service.TicketNotFoundError:
        # same answer for "not yours" and "does not exist"
        raise _not_found("Ticket") from None


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
