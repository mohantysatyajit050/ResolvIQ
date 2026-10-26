import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_message import SenderType, TicketMessage
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services import order_service, ticket_state
from app.services.access import sees_everything
from app.services.ticket_state import Actor

FINISHED_STATUSES = (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value)


class TicketNotFoundError(Exception):
    """The ticket does not exist, or the user may not see it (we never say which)."""


class ActiveTicketExistsError(Exception):
    """The order already has an active ticket."""


class TicketClosedError(Exception):
    """Nobody can reply on a closed ticket."""


def visible_tickets(user: User) -> Select:
    """Every ticket query starts here, so the ownership rule lives in one place."""
    stmt = select(Ticket)
    if not sees_everything(user):
        stmt = stmt.where(Ticket.user_id == user.id)
    return stmt


def list_tickets(
    db: Session,
    user: User,
    status: TicketStatus | None,
    limit: int,
    offset: int,
) -> tuple[list[Ticket], int]:
    base = visible_tickets(user)
    if status is not None:
        base = base.where(Ticket.status == status.value)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    tickets = db.scalars(
        base.order_by(Ticket.created_at.desc(), Ticket.id).limit(limit).offset(offset)
    ).all()
    return list(tickets), total


def get_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> Ticket:
    stmt = (
        visible_tickets(user)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.messages),
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
    ticket.updated_at = datetime.now(timezone.utc)

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
