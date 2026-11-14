"""Tests for the order lookup tool. They use the real test database, no LLM."""

import dataclasses
from datetime import date, datetime, timezone

from app.agent.order_lookup import (
    ItemFacts,
    LookupFailure,
    OrderFacts,
    lookup_order,
)
from tests.factories import make_order, make_ticket

TODAY = date(2026, 11, 14)


def _ticket_for_order(db, make_user, *, status, expected=None, delivered_at=None):
    """A customer, their order (with the given dates) and a ticket about it."""
    customer = make_user(email="customer@example.com")
    order = make_order(db, customer, status=status)
    order.expected_delivery_date = expected
    order.delivered_at = delivered_at
    db.commit()
    return make_ticket(db, customer, order)


def test_on_time_delivery_returns_facts_with_zero_days_late(db_session, make_user):
    ticket = _ticket_for_order(
        db_session,
        make_user,
        status="delivered",
        expected=date(2026, 11, 10),
        delivered_at=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
    )

    result = lookup_order(db_session, ticket, today=TODAY)

    assert result.found
    assert result.failure is None
    facts = result.facts
    assert facts.order_id == ticket.order_id
    assert facts.status == "delivered"
    assert facts.days_late == 0
    assert facts.total_paise == 1_500_000
    assert len(facts.items) == 1
    assert facts.items[0].product_name == "Test Phone"
    assert facts.items[0].quantity == 1
    assert facts.items[0].unit_price_paise == 1_500_000


def test_late_delivery_counts_days_after_expected_date(db_session, make_user):
    ticket = _ticket_for_order(
        db_session,
        make_user,
        status="delivered",
        expected=date(2026, 11, 10),
        delivered_at=datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc),
    )

    result = lookup_order(db_session, ticket, today=TODAY)

    assert result.facts.days_late == 4


def test_undelivered_order_past_expected_date_is_late_until_today(db_session, make_user):
    ticket = _ticket_for_order(
        db_session, make_user, status="shipped", expected=date(2026, 11, 10)
    )

    result = lookup_order(db_session, ticket, today=TODAY)

    assert result.facts.days_late == 4


def test_order_not_yet_due_is_not_late(db_session, make_user):
    ticket = _ticket_for_order(
        db_session, make_user, status="shipped", expected=date(2026, 11, 20)
    )

    result = lookup_order(db_session, ticket, today=TODAY)

    assert result.facts.days_late == 0


def test_cancelled_order_has_no_days_late(db_session, make_user):
    ticket = _ticket_for_order(
        db_session, make_user, status="cancelled", expected=date(2026, 11, 10)
    )

    result = lookup_order(db_session, ticket, today=TODAY)

    assert result.facts.days_late is None


def test_order_without_expected_date_has_no_days_late(db_session, make_user):
    ticket = _ticket_for_order(db_session, make_user, status="placed", expected=None)

    result = lookup_order(db_session, ticket, today=TODAY)

    assert result.facts.days_late is None


def test_other_customers_order_is_not_found(db_session, make_user):
    owner = make_user(email="owner@example.com")
    other = make_user(email="other@example.com")
    order = make_order(db_session, owner)
    # a tampered ticket: it belongs to "other" but points at the owner's order
    ticket = make_ticket(db_session, other, order)

    result = lookup_order(db_session, ticket, today=TODAY)

    assert not result.found
    assert result.facts is None
    assert result.failure == LookupFailure.ORDER_NOT_FOUND


def test_order_with_no_items_is_a_failure(db_session, make_user):
    customer = make_user(email="customer@example.com")
    order = make_order(db_session, customer)
    order.items.clear()
    db_session.commit()
    ticket = make_ticket(db_session, customer, order)

    result = lookup_order(db_session, ticket, today=TODAY)

    assert not result.found
    assert result.failure == LookupFailure.NO_ITEMS


def test_facts_do_not_include_address_or_user_data():
    forbidden = {"shipping_address", "address", "user_id", "email", "name", "phone"}
    order_fields = {f.name for f in dataclasses.fields(OrderFacts)}
    item_fields = {f.name for f in dataclasses.fields(ItemFacts)}

    assert not order_fields & forbidden
    assert not item_fields & forbidden
