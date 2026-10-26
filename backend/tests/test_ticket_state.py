from datetime import datetime, timezone

import pytest

from app.models import Ticket, TicketStatus
from app.services.ticket_state import (
    ALLOWED_TRANSITIONS,
    Actor,
    InvalidTransitionError,
    can_transition,
    change_status,
)

S = TicketStatus
A = Actor

ALLOWED = [
    (S.OPEN, S.INVESTIGATING, A.SYSTEM),
    (S.INVESTIGATING, S.WAITING_FOR_CUSTOMER, A.AI),
    (S.WAITING_FOR_CUSTOMER, S.INVESTIGATING, A.CUSTOMER),
    (S.INVESTIGATING, S.WAITING_FOR_APPROVAL, A.AI),
    (S.INVESTIGATING, S.RESOLVED, A.AI),
    (S.WAITING_FOR_APPROVAL, S.RESOLVED, A.AGENT),
    (S.WAITING_FOR_APPROVAL, S.INVESTIGATING, A.AGENT),
    (S.RESOLVED, S.INVESTIGATING, A.CUSTOMER),
    (S.RESOLVED, S.CLOSED, A.SYSTEM),
    (S.INVESTIGATING, S.ESCALATED, A.AI),
    (S.ESCALATED, S.RESOLVED, A.AGENT),
]

FORBIDDEN = [
    (S.CLOSED, S.OPEN, A.SYSTEM),  # closed is the end
    (S.OPEN, S.RESOLVED, A.AI),  # cannot skip investigating
    (S.INVESTIGATING, S.RESOLVED, A.CUSTOMER),  # customers cannot resolve
    (S.WAITING_FOR_APPROVAL, S.RESOLVED, A.CUSTOMER),
    (S.RESOLVED, S.INVESTIGATING, A.AGENT),  # only the customer reopens
    (S.CLOSED, S.INVESTIGATING, A.CUSTOMER),  # closed tickets stay closed
]


@pytest.mark.parametrize(("current", "new", "actor"), ALLOWED)
def test_allowed_arrows(current, new, actor):
    assert can_transition(current, new, actor)


def test_there_are_exactly_eleven_arrows():
    assert len(ALLOWED_TRANSITIONS) == 11


@pytest.mark.parametrize(("current", "new", "actor"), FORBIDDEN)
def test_forbidden_moves(current, new, actor):
    assert not can_transition(current, new, actor)


def test_resolving_sets_resolved_at():
    ticket = Ticket(status="investigating")
    change_status(ticket, S.RESOLVED, A.AI)
    assert ticket.status == "resolved"
    assert ticket.resolved_at is not None


def test_reopening_clears_resolved_at():
    ticket = Ticket(status="resolved", resolved_at=datetime.now(timezone.utc))
    change_status(ticket, S.INVESTIGATING, A.CUSTOMER)
    assert ticket.status == "investigating"
    assert ticket.resolved_at is None


def test_refused_move_leaves_the_ticket_unchanged():
    ticket = Ticket(status="closed")
    with pytest.raises(InvalidTransitionError):
        change_status(ticket, S.OPEN, A.SYSTEM)
    assert ticket.status == "closed"
