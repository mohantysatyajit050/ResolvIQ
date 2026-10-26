import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import Ticket, TicketMessage, TicketStatus, UserRole
from tests.factories import auth_header, make_order, make_ticket

NEW_TICKET = {
    "subject": "Order is late",
    "description": "It was supposed to arrive 5 days ago.",
}


def count_tickets(db) -> int:
    return db.scalar(select(func.count()).select_from(Ticket))


def count_messages(db) -> int:
    return db.scalar(select(func.count()).select_from(TicketMessage))


def new_ticket_body(order, **overrides) -> dict:
    return {**NEW_TICKET, "order_id": str(order.id), **overrides}


# ---------- creating a ticket ----------


def test_create_ticket_success(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)

    response = client.post(
        "/tickets", json=new_ticket_body(order), headers=auth_header(asha)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["priority"] == "medium"
    assert body["intent"] is None
    assert body["user_id"] == str(asha.id)
    assert body["order_id"] == str(order.id)
    assert len(body["messages"]) == 1
    assert body["messages"][0]["sender_type"] == "customer"
    assert body["messages"][0]["body"] == NEW_TICKET["description"]
    assert body["order"]["id"] == str(order.id)


def test_create_ticket_for_someone_elses_order_returns_404_and_creates_nothing(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    ravi_order = make_order(db_session, ravi)

    response = client.post(
        "/tickets", json=new_ticket_body(ravi_order), headers=auth_header(asha)
    )
    assert response.status_code == 404
    assert count_tickets(db_session) == 0


def test_create_ticket_for_unknown_order_returns_404(client, make_user):
    asha = make_user(email="asha@example.com")
    body = {**NEW_TICKET, "order_id": str(uuid.uuid4())}
    response = client.post("/tickets", json=body, headers=auth_header(asha))
    assert response.status_code == 404


def test_second_active_ticket_for_same_order_returns_409(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    headers = auth_header(asha)

    first = client.post("/tickets", json=new_ticket_body(order), headers=headers)
    second = client.post("/tickets", json=new_ticket_body(order), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 409
    assert count_tickets(db_session) == 1


def test_new_ticket_allowed_after_previous_one_is_resolved(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    make_ticket(db_session, asha, order, status=TicketStatus.RESOLVED)

    response = client.post(
        "/tickets", json=new_ticket_body(order), headers=auth_header(asha)
    )
    assert response.status_code == 201


def test_client_cannot_set_user_id_status_or_priority(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    order = make_order(db_session, asha)

    for extra in (
        {"user_id": str(ravi.id)},
        {"status": "resolved"},
        {"priority": "urgent"},
    ):
        response = client.post(
            "/tickets",
            json=new_ticket_body(order, **extra),
            headers=auth_header(asha),
        )
        assert response.status_code == 422
    assert count_tickets(db_session) == 0


def test_agent_cannot_create_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = make_user(email="agent@example.com", role=UserRole.AGENT)
    order = make_order(db_session, asha)

    response = client.post(
        "/tickets", json=new_ticket_body(order), headers=auth_header(agent)
    )
    assert response.status_code == 403


def test_create_ticket_requires_login(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    response = client.post("/tickets", json=new_ticket_body(order))
    assert response.status_code == 401


def test_blank_subject_is_rejected(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    response = client.post(
        "/tickets",
        json=new_ticket_body(order, subject="   "),
        headers=auth_header(asha),
    )
    assert response.status_code == 422


# ---------- listing tickets ----------


def test_customer_sees_only_own_tickets(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    make_ticket(db_session, asha, make_order(db_session, asha), subject="Asha problem")
    make_ticket(
        db_session, ravi, make_order(db_session, ravi), subject="Ravi secret problem"
    )

    response = client.get("/tickets", headers=auth_header(asha))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [ticket["subject"] for ticket in body["items"]] == ["Asha problem"]
    assert "Ravi secret problem" not in response.text


def test_agent_sees_all_tickets(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    agent = make_user(email="agent@example.com", role=UserRole.AGENT)
    make_ticket(db_session, asha, make_order(db_session, asha))
    make_ticket(db_session, ravi, make_order(db_session, ravi))

    response = client.get("/tickets", headers=auth_header(agent))
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_status_filter(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    make_ticket(db_session, asha, make_order(db_session, asha), status=TicketStatus.OPEN)
    make_ticket(
        db_session, asha, make_order(db_session, asha), status=TicketStatus.RESOLVED
    )

    response = client.get("/tickets?status=resolved", headers=auth_header(asha))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "resolved"


def test_invalid_status_filter_returns_422(client, make_user):
    asha = make_user(email="asha@example.com")
    response = client.get("/tickets?status=teleported", headers=auth_header(asha))
    assert response.status_code == 422


def test_tickets_are_paginated(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    for _ in range(3):
        make_ticket(db_session, asha, make_order(db_session, asha))

    first = client.get("/tickets?limit=2&offset=0", headers=auth_header(asha)).json()
    assert len(first["items"]) == 2
    assert first["total"] == 3

    second = client.get("/tickets?limit=2&offset=2", headers=auth_header(asha)).json()
    assert len(second["items"]) == 1


# ---------- reading one ticket ----------


def test_ticket_detail_has_messages_and_order(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = make_ticket(db_session, asha, make_order(db_session, asha))

    response = client.get(f"/tickets/{ticket.id}", headers=auth_header(asha))
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "It is late."
    assert len(body["messages"]) == 1
    assert body["order"]["items"][0]["product"]["name"] == "Test Phone"


def test_customer_cannot_read_another_customers_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    ravi_ticket = make_ticket(db_session, ravi, make_order(db_session, ravi))

    theirs = client.get(f"/tickets/{ravi_ticket.id}", headers=auth_header(asha))
    missing = client.get(f"/tickets/{uuid.uuid4()}", headers=auth_header(asha))
    assert theirs.status_code == 404
    assert theirs.status_code == missing.status_code
    assert theirs.json() == missing.json()  # nothing reveals that the ticket exists


def test_agent_can_read_any_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = make_user(email="agent@example.com", role=UserRole.AGENT)
    ticket = make_ticket(db_session, asha, make_order(db_session, asha))

    response = client.get(f"/tickets/{ticket.id}", headers=auth_header(agent))
    assert response.status_code == 200
    assert response.json()["id"] == str(ticket.id)


# ---------- replying ----------


def test_customer_can_reply_to_own_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = make_ticket(db_session, asha, make_order(db_session, asha))

    response = client.post(
        f"/tickets/{ticket.id}/messages",
        json={"body": "Any update?"},
        headers=auth_header(asha),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sender_type"] == "customer"
    assert body["sender_id"] == str(asha.id)
    assert body["body"] == "Any update?"

    detail = client.get(f"/tickets/{ticket.id}", headers=auth_header(asha)).json()
    assert [message["body"] for message in detail["messages"]] == [
        "It is late.",
        "Any update?",
    ]


def test_customer_cannot_reply_to_another_customers_ticket(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    ravi_ticket = make_ticket(db_session, ravi, make_order(db_session, ravi))

    response = client.post(
        f"/tickets/{ravi_ticket.id}/messages",
        json={"body": "I am a stranger"},
        headers=auth_header(asha),
    )
    assert response.status_code == 404
    assert count_messages(db_session) == 1  # only Ravi's first message


def test_agent_reply_is_marked_as_agent_and_keeps_status(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    agent = make_user(email="agent@example.com", role=UserRole.AGENT)
    ticket = make_ticket(
        db_session,
        asha,
        make_order(db_session, asha),
        status=TicketStatus.INVESTIGATING,
    )

    response = client.post(
        f"/tickets/{ticket.id}/messages",
        json={"body": "We are checking."},
        headers=auth_header(agent),
    )
    assert response.status_code == 201
    assert response.json()["sender_type"] == "agent"
    db_session.refresh(ticket)
    assert ticket.status == "investigating"


def test_customer_reply_moves_waiting_for_customer_to_investigating(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    ticket = make_ticket(
        db_session,
        asha,
        make_order(db_session, asha),
        status=TicketStatus.WAITING_FOR_CUSTOMER,
    )

    response = client.post(
        f"/tickets/{ticket.id}/messages",
        json={"body": "Here is the photo."},
        headers=auth_header(asha),
    )
    assert response.status_code == 201
    db_session.refresh(ticket)
    assert ticket.status == "investigating"


def test_customer_reply_reopens_resolved_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = make_ticket(
        db_session, asha, make_order(db_session, asha), status=TicketStatus.RESOLVED
    )
    ticket.resolved_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.post(
        f"/tickets/{ticket.id}/messages",
        json={"body": "It is still broken."},
        headers=auth_header(asha),
    )
    assert response.status_code == 201
    db_session.refresh(ticket)
    assert ticket.status == "investigating"
    assert ticket.resolved_at is None


def test_cannot_reply_to_closed_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = make_ticket(
        db_session, asha, make_order(db_session, asha), status=TicketStatus.CLOSED
    )

    response = client.post(
        f"/tickets/{ticket.id}/messages",
        json={"body": "Hello?"},
        headers=auth_header(asha),
    )
    assert response.status_code == 409
    assert count_messages(db_session) == 1


def test_empty_message_is_rejected(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = make_ticket(db_session, asha, make_order(db_session, asha))

    response = client.post(
        f"/tickets/{ticket.id}/messages",
        json={"body": ""},
        headers=auth_header(asha),
    )
    assert response.status_code == 422


def test_ticket_endpoints_require_login(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = make_ticket(db_session, asha, make_order(db_session, asha))

    assert client.get("/tickets").status_code == 401
    assert client.get(f"/tickets/{ticket.id}").status_code == 401
    response = client.post(f"/tickets/{ticket.id}/messages", json={"body": "Hi"})
    assert response.status_code == 401


def test_reopening_is_refused_when_another_ticket_is_active(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    old = make_ticket(db_session, asha, order, status=TicketStatus.RESOLVED)
    make_ticket(db_session, asha, order, status=TicketStatus.OPEN, subject="Second")

    response = client.post(
        f"/tickets/{old.id}/messages",
        json={"body": "Still broken"},
        headers=auth_header(asha),
    )
    assert response.status_code == 409
    db_session.refresh(old)
    assert old.status == "resolved"
