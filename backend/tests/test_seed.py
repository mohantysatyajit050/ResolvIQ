from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.seed import (
    DAMAGED_SUBJECT,
    DEV_PASSWORD,
    LATE_SUBJECT,
    NOT_RECEIVED_SUBJECT,
    PRODUCTS,
    seed,
)
from app.models import Order, Product, Ticket, User


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def order_of_ticket(db, subject):
    ticket = db.scalar(select(Ticket).where(Ticket.subject == subject))
    return db.get(Order, ticket.order_id)


def test_seed_creates_users_products_orders_and_tickets(db_session):
    seed(db_session)
    assert count(db_session, User) == 7  # 1 admin, 1 agent, 5 customers
    assert count(db_session, Product) == len(PRODUCTS)
    assert count(db_session, Order) == 18  # 3 scenarios + 3 for each of 5 customers
    assert count(db_session, Ticket) == 5


def test_late_order_scenario(db_session):
    seed(db_session)
    order = order_of_ticket(db_session, LATE_SUBJECT)
    assert order.status == "shipped"
    assert order.delivered_at is None
    assert order.expected_delivery_date < datetime.now(timezone.utc).date()


def test_damaged_phone_scenario(db_session):
    seed(db_session)
    order = order_of_ticket(db_session, DAMAGED_SUBJECT)
    assert order.status == "delivered"
    assert order.delivered_at is not None
    assert "Smartphone" in order.items[0].product.name


def test_never_received_scenario(db_session):
    seed(db_session)
    order = order_of_ticket(db_session, NOT_RECEIVED_SUBJECT)
    assert order.status == "delivered"  # the system says delivered, the customer says no
    assert order.delivered_at is not None
    assert order.total_paise == 2_500_000  # 25,000 rupees


def test_every_ticket_belongs_to_the_owner_of_its_order(db_session):
    seed(db_session)
    for ticket in db_session.scalars(select(Ticket)):
        order = db_session.get(Order, ticket.order_id)
        assert ticket.user_id == order.user_id


def test_seeding_twice_does_not_duplicate_data(db_session):
    seed(db_session)
    users, orders = count(db_session, User), count(db_session, Order)
    seed(db_session)
    assert count(db_session, User) == users
    assert count(db_session, Order) == orders


def test_seeded_customer_can_log_in(client, db_session):
    seed(db_session)
    response = client.post(
        "/auth/login",
        json={"email": "customer1@resolviq.dev", "password": DEV_PASSWORD},
    )
    assert response.status_code == 200
