import enum
from datetime import datetime, timezone

from app.models.ticket import Ticket, TicketStatus


class Actor(enum.StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"  # support agents and admins
    AI = "ai"
    SYSTEM = "system"  # timers and background jobs


class InvalidTransitionError(Exception):
    """The ticket may not move from its current status to the requested one."""


S = TicketStatus
A = Actor

# Every allowed arrow of the ticket status flow, and who may take it.
# Anything that is not listed here is refused.
ALLOWED_TRANSITIONS: dict[tuple[TicketStatus, TicketStatus], frozenset[Actor]] = {
    (S.OPEN, S.INVESTIGATING): frozenset({A.SYSTEM}),  # 1
    (S.INVESTIGATING, S.WAITING_FOR_CUSTOMER): frozenset({A.AI, A.AGENT}),  # 2
    (S.WAITING_FOR_CUSTOMER, S.INVESTIGATING): frozenset({A.CUSTOMER}),  # 3
    (S.INVESTIGATING, S.WAITING_FOR_APPROVAL): frozenset({A.AI}),  # 4
    (S.INVESTIGATING, S.RESOLVED): frozenset({A.AI}),  # 5
    (S.WAITING_FOR_APPROVAL, S.RESOLVED): frozenset({A.AGENT}),  # 6
    (S.WAITING_FOR_APPROVAL, S.INVESTIGATING): frozenset({A.AGENT}),  # 7
    (S.RESOLVED, S.INVESTIGATING): frozenset({A.CUSTOMER}),  # 8
    (S.RESOLVED, S.CLOSED): frozenset({A.SYSTEM}),  # 9
    (S.INVESTIGATING, S.ESCALATED): frozenset({A.AI, A.SYSTEM}),  # 10
    (S.ESCALATED, S.RESOLVED): frozenset({A.AGENT}),  # 11
}


def can_transition(current: TicketStatus, new: TicketStatus, actor: Actor) -> bool:
    return actor in ALLOWED_TRANSITIONS.get((current, new), frozenset())


def change_status(ticket: Ticket, new_status: TicketStatus, actor: Actor) -> None:
    """The only place where a ticket status may change."""
    current = TicketStatus(ticket.status)
    if not can_transition(current, new_status, actor):
        raise InvalidTransitionError(
            f"{actor.value} cannot move a ticket from {current.value} to {new_status.value}"
        )
    ticket.status = new_status.value
    if new_status is TicketStatus.RESOLVED:
        ticket.resolved_at = datetime.now(timezone.utc)
    elif current is TicketStatus.RESOLVED and new_status is TicketStatus.INVESTIGATING:
        ticket.resolved_at = None  # the ticket was reopened
