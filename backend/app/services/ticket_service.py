import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import Select, case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.ticket_message import SenderType, TicketMessage
from app.models.user import User, UserRole
from app.schemas.ticket import TicketCreate
from app.services import order_service, ticket_state
from app.services.access import sees_everything
from app.services.ticket_state import Actor

FINISHED_STATUSES = (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value)

TicketSort = Literal["newest", "oldest", "updated", "priority"]
AssignedFilter = Literal["me", "unassigned"]

# urgent first when sorting by priority
PRIORITY_RANK = case(
    {
        TicketPriority.URGENT.value: 4,
        TicketPriority.HIGH.value: 3,
        TicketPriority.MEDIUM.value: 2,
        TicketPriority.LOW.value: 1,
    },
    value=Ticket.priority,
    else_=0,
)


class TicketNotFoundError(Exception):
    """The ticket does not exist, or the user may not see it (we never say which)."""


class ActiveTicketExistsError(Exception):
    """The order already has an active ticket."""


class TicketClosedError(Exception):
    """Nobody can reply on a closed ticket."""


class NotTicketManagerError(Exception):
    """Only the assigned agent (or an admin) may change this ticket."""


class AssignNotAllowedError(Exception):
    """An agent may only assign a ticket to themselves."""


class InvalidAssigneeError(Exception):
    """The chosen person does not exist or cannot take tickets."""


class AlreadyAssignedError(Exception):
    """Someone else already took this ticket."""


@dataclass(frozen=True)
class TicketFilters:
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_to: AssignedFilter | None = None
    search: str | None = None
    sort: TicketSort = "newest"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _escape_like(text_value: str) -> str:
    """Make % and _ match as plain characters inside a LIKE search."""
    return (
        text_value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


def _order_by(sort: TicketSort):
    if sort == "oldest":
        return (Ticket.created_at.asc(), Ticket.id)
    if sort == "updated":
        return (Ticket.updated_at.desc(), Ticket.id)
    if sort == "priority":
        return (PRIORITY_RANK.desc(), Ticket.created_at.asc(), Ticket.id)
    return (Ticket.created_at.desc(), Ticket.id)


def visible_tickets(user: User) -> Select:
    """Every ticket query starts here, so the ownership rule lives in one place."""
    stmt = select(Ticket)
    if not sees_everything(user):
        stmt = stmt.where(Ticket.user_id == user.id)
    return stmt


def list_tickets(
    db: Session,
    user: User,
    filters: TicketFilters,
    limit: int,
    offset: int,
) -> tuple[list[Ticket], int]:
    """Filtering, sorting and paging all happen in the database."""
    base = visible_tickets(user)
    if filters.status is not None:
        base = base.where(Ticket.status == filters.status.value)
    if filters.priority is not None:
        base = base.where(Ticket.priority == filters.priority.value)
    if filters.assigned_to == "me":
        base = base.where(Ticket.assigned_agent_id == user.id)
    elif filters.assigned_to == "unassigned":
        base = base.where(Ticket.assigned_agent_id.is_(None))
    if filters.search and filters.search.strip():
        # the text travels as a query parameter, never inside the SQL text itself
        pattern = f"%{_escape_like(filters.search.strip())}%"
        base = base.join(Ticket.customer).where(
            or_(
                Ticket.subject.ilike(pattern, escape="\\"),
                User.name.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
            )
        )

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    tickets = db.scalars(
        base.options(
            selectinload(Ticket.customer), selectinload(Ticket.assigned_agent)
        )
        .order_by(*_order_by(filters.sort))
        .limit(limit)
        .offset(offset)
    ).all()
    return list(tickets), total


def get_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> Ticket:
    stmt = (
        visible_tickets(user)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.messages),
            selectinload(Ticket.customer),
            selectinload(Ticket.assigned_agent),
            selectinload(Ticket.order)
            .selectinload(Order.items)
            .selectinload(OrderItem.product),
            selectinload(Ticket.order).selectinload(Order.shipping_address),
        )
        .execution_options(populate_existing=True)
    )
    ticket = db.scalar(stmt)
    if ticket is None:
        raise TicketNotFoundError
    return ticket


def can_manage(ticket: Ticket, user: User) -> bool:
    """Only the assigned agent, or an admin, may change a ticket's status or priority."""
    if user.role == UserRole.ADMIN.value:
        return True
    return user.role == UserRole.AGENT.value and ticket.assigned_agent_id == user.id


def allowed_status_changes(ticket: Ticket, user: User) -> list[TicketStatus]:
    """The buttons the page may show this user for this ticket."""
    if not can_manage(ticket, user):
        return []
    return ticket_state.allowed_next(TicketStatus(ticket.status), Actor.AGENT)


def create_ticket(db: Session, user: User, data: TicketCreate) -> Ticket:
    """Open a ticket for one of the customer's own orders, with its first message."""
    order = order_service.get_order(db, user, data.order_id)  # raises if not theirs

    active = db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(Ticket.order_id == order.id, Ticket.status.not_in(FINISHED_STATUSES))
    )
    if active:
        raise ActiveTicketExistsError

    ticket = Ticket(
        user_id=user.id,  # from the token, never from the request
        order_id=order.id,
        subject=data.subject,
        description=data.description,
        messages=[
            TicketMessage(
                sender_id=user.id,
                sender_type=SenderType.CUSTOMER.value,
                body=data.description,
            )
        ],
    )
    db.add(ticket)
    try:
        db.commit()  # one transaction: the ticket and its first message, or neither
    except IntegrityError:
        # two requests passed the check at the same moment; the database stopped the second
        db.rollback()
        raise ActiveTicketExistsError from None
    return get_ticket(db, user, ticket.id)


def add_message(
    db: Session, user: User, ticket_id: uuid.UUID, body: str
) -> TicketMessage:
    """Add a reply. The server decides the sender type, never the client."""
    ticket = get_ticket(db, user, ticket_id)  # raises TicketNotFoundError if not visible
    if ticket.status == TicketStatus.CLOSED.value:
        raise TicketClosedError

    is_customer = not sees_everything(user)
    sender_type = SenderType.CUSTOMER if is_customer else SenderType.AGENT
    message = TicketMessage(
        sender_id=user.id, sender_type=sender_type.value, body=body
    )
    ticket.messages.append(message)
    ticket.updated_at = _now()

    customer_reply_moves_ticket = (
        TicketStatus.WAITING_FOR_CUSTOMER.value,
        TicketStatus.RESOLVED.value,
    )
    if is_customer and ticket.status in customer_reply_moves_ticket:
        # arrow 3 (waiting_for_customer -> investigating) or arrow 8 (reopen)
        ticket_state.change_status(ticket, TicketStatus.INVESTIGATING, Actor.CUSTOMER)

    try:
        db.commit()
    except IntegrityError:
        # reopening would create a second active ticket for the same order
        db.rollback()
        raise ActiveTicketExistsError from None
    db.refresh(message)
    return message


def assign_ticket(
    db: Session, user: User, ticket_id: uuid.UUID, agent_id: uuid.UUID | None
) -> Ticket:
    """Take a ticket. One atomic UPDATE decides the winner when two agents race."""
    ticket = get_ticket(db, user, ticket_id)  # 404 if it does not exist
    is_admin = user.role == UserRole.ADMIN.value
    target_id = agent_id or user.id
    if target_id != user.id and not is_admin:
        raise AssignNotAllowedError

    target = db.get(User, target_id)
    if (
        target is None
        or not target.is_active
        or target.role not in (UserRole.AGENT.value, UserRole.ADMIN.value)
    ):
        raise InvalidAssigneeError

    stmt = update(Ticket).where(Ticket.id == ticket.id)
    if not is_admin:
        # compare-and-set: an agent can only take a ticket that is free (or already theirs)
        stmt = stmt.where(
            or_(
                Ticket.assigned_agent_id.is_(None),
                Ticket.assigned_agent_id == target.id,
            )
        )
    result = db.execute(
        stmt.values(assigned_agent_id=target.id, updated_at=_now()).execution_options(
            synchronize_session=False
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise AlreadyAssignedError

    db.refresh(ticket)  # the UPDATE above did not go through the loaded object
    if ticket.status == TicketStatus.OPEN.value:
        # taking an open ticket starts the work (arrow 1)
        ticket_state.change_status(ticket, TicketStatus.INVESTIGATING, Actor.AGENT)
    db.commit()
    return get_ticket(db, user, ticket.id)


def unassign_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)
    if not can_manage(ticket, user):
        raise NotTicketManagerError
    ticket.assigned_agent_id = None
    ticket.updated_at = _now()
    db.commit()
    return get_ticket(db, user, ticket.id)


def change_ticket_status(
    db: Session, user: User, ticket_id: uuid.UUID, new_status: TicketStatus
) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)
    if not can_manage(ticket, user):
        raise NotTicketManagerError
    # raises InvalidTransitionError when the arrow does not exist for an agent
    ticket_state.change_status(ticket, new_status, Actor.AGENT)
    ticket.updated_at = _now()
    db.commit()
    return get_ticket(db, user, ticket.id)


def change_ticket_priority(
    db: Session, user: User, ticket_id: uuid.UUID, priority: TicketPriority
) -> Ticket:
    ticket = get_ticket(db, user, ticket_id)
    if not can_manage(ticket, user):
        raise NotTicketManagerError
    ticket.priority = priority.value
    ticket.updated_at = _now()
    db.commit()
    return get_ticket(db, user, ticket.id)
