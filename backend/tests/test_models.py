import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Address,
    Order,
    OrderItem,
    Product,
    Ticket,
    TicketMessage,
    UserRole,
)


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def make_address(db, user, pincode="411001"):
    address = Address(
        user_id=user.id,
        address_line="12, Station Road",
        city="Pune",
        state="Maharashtra",
        pincode=pincode,
    )
    db.add(address)
    db.commit()
    return address


def make_product(db):
    product = Product(name="Test Phone", category="Phones", price_paise=1_500_000)
    db.add(product)
    db.commit()
    return product


def make_order(db, user, address, product, quantity=2):
    order = Order(
        user_id=user.id,
        shipping_address_id=address.id,
        status="placed",
        total_paise=quantity * product.price_paise,
        items=[
            OrderItem(
                product_id=product.id,
                quantity=quantity,
                unit_price_paise=product.price_paise,
            )
        ],
    )
    db.add(order)
    db.commit()
    return order


def make_ticket(db, user, order):
    ticket = Ticket(
        user_id=user.id,
        order_id=order.id,
        subject="Where is my order?",
        description="It is late.",
    )
    db.add(ticket)
    db.commit()
    return ticket


def test_order_items_are_reachable_through_the_order(db_session, make_user):
    user = make_user()
    order = make_order(
        db_session, user, make_address(db_session, user), make_product(db_session)
    )
    db_session.expire_all()  # force a fresh read from the database
    loaded = db_session.get(Order, order.id)
    assert len(loaded.items) == 1
    assert loaded.items[0].product.name == "Test Phone"
    assert loaded.shipping_address.city == "Pune"


def test_deleting_an_order_deletes_its_items(db_session, make_user):
    user = make_user()
    order = make_order(
        db_session, user, make_address(db_session, user), make_product(db_session)
    )
    db_session.delete(order)
    db_session.commit()
    assert count(db_session, Order) == 0
    assert count(db_session, OrderItem) == 0


def test_cannot_delete_a_user_who_has_orders(db_session, make_user):
    user = make_user()
    make_order(
        db_session, user, make_address(db_session, user), make_product(db_session)
    )
    db_session.delete(user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cannot_delete_an_order_that_has_a_ticket(db_session, make_user):
    user = make_user()
    order = make_order(
        db_session, user, make_address(db_session, user), make_product(db_session)
    )
    make_ticket(db_session, user, order)
    db_session.delete(order)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_a_ticket_deletes_its_messages(db_session, make_user):
    user = make_user()
    order = make_order(
        db_session, user, make_address(db_session, user), make_product(db_session)
    )
    ticket = make_ticket(db_session, user, order)
    db_session.add(
        TicketMessage(
            ticket_id=ticket.id, sender_id=user.id, sender_type="customer", body="Hello"
        )
    )
    db_session.commit()
    assert count(db_session, TicketMessage) == 1

    db_session.delete(ticket)
    db_session.commit()
    assert count(db_session, TicketMessage) == 0


def test_deleting_a_user_without_orders_deletes_their_addresses(db_session, make_user):
    user = make_user()
    make_address(db_session, user)
    db_session.delete(user)
    db_session.commit()
    assert count(db_session, Address) == 0


def test_order_with_unknown_user_is_rejected(db_session, make_user):
    user = make_user()
    address = make_address(db_session, user)
    db_session.add(
        Order(
            user_id=uuid.uuid4(),  # no such user
            shipping_address_id=address.id,
            status="placed",
            total_paise=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_invalid_order_status_is_rejected(db_session, make_user):
    user = make_user()
    address = make_address(db_session, user)
    db_session.add(
        Order(
            user_id=user.id,
            shipping_address_id=address.id,
            status="teleported",
            total_paise=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_invalid_pincode_is_rejected(db_session, make_user):
    user = make_user()
    with pytest.raises(IntegrityError):
        make_address(db_session, user, pincode="12")
    db_session.rollback()


def test_ticket_defaults(db_session, make_user):
    user = make_user()
    order = make_order(
        db_session, user, make_address(db_session, user), make_product(db_session)
    )
    ticket = make_ticket(db_session, user, order)
    db_session.refresh(ticket)
    assert ticket.status == "open"
    assert ticket.priority == "medium"
    assert ticket.intent is None
    assert ticket.assigned_agent_id is None
    assert ticket.created_at is not None


def test_deleting_an_agent_keeps_tickets_and_messages(db_session, make_user):
    customer = make_user(email="customer@example.com")
    agent = make_user(email="agent@example.com", role=UserRole.AGENT)
    order = make_order(
        db_session, customer, make_address(db_session, customer), make_product(db_session)
    )
    ticket = make_ticket(db_session, customer, order)
    ticket.assigned_agent_id = agent.id
    message = TicketMessage(
        ticket_id=ticket.id, sender_id=agent.id, sender_type="agent", body="On it"
    )
    db_session.add(message)
    db_session.commit()

    db_session.delete(agent)
    db_session.commit()

    db_session.refresh(ticket)
    db_session.refresh(message)
    assert ticket.assigned_agent_id is None
    assert message.sender_id is None
