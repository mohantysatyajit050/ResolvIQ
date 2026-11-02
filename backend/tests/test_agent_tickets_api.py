import uuid
from datetime import datetime, timedelta, timezone

from app.models import TicketStatus, UserRole
from tests.factories import auth_header, make_order, make_ticket

NOW = datetime.now(timezone.utc)


def get(client, user, path):
    return client.get(path, headers=auth_header(user))


def post(client, user, path, body=None):
    return client.post(path, json=body, headers=auth_header(user))


def patch(client, user, path, body):
    return client.patch(path, json=body, headers=auth_header(user))


def staff(make_user, email="agent@example.com", name="Agent One"):
    return make_user(email=email, role=UserRole.AGENT, name=name)


def ticket_for(db, customer, **kwargs):
    return make_ticket(db, customer, make_order(db, customer), **kwargs)


def subjects(response):
    return [item["subject"] for item in response.json()["items"]]


# ---------- filters, search and sorting (done in the database) ----------


def test_agent_filters_by_priority(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket_for(db_session, asha, subject="Urgent one", priority="urgent")
    ticket_for(db_session, asha, subject="Low one", priority="low")

    response = get(client, agent, "/tickets?priority=urgent")
    assert subjects(response) == ["Urgent one"]


def test_agent_filters_mine_and_unassigned(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    other = staff(make_user, email="agent2@example.com", name="Agent Two")
    ticket_for(db_session, asha, subject="Mine", assigned_agent=agent)
    ticket_for(db_session, asha, subject="Theirs", assigned_agent=other)
    ticket_for(db_session, asha, subject="Free")

    assert subjects(get(client, agent, "/tickets?assigned_to=me")) == ["Mine"]
    assert subjects(get(client, agent, "/tickets?assigned_to=unassigned")) == ["Free"]


def test_search_matches_subject_and_customer_name(client, db_session, make_user):
    priya = make_user(email="priya@example.com", name="Priya Nair")
    ravi = make_user(email="ravi@example.com", name="Ravi Kumar")
    agent = staff(make_user)
    ticket_for(db_session, priya, subject="Cracked screen")
    ticket_for(db_session, ravi, subject="Late parcel")

    assert subjects(get(client, agent, "/tickets?q=screen")) == ["Cracked screen"]
    assert subjects(get(client, agent, "/tickets?q=ravi")) == ["Late parcel"]


def test_search_treats_percent_and_underscore_as_plain_text(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket_for(db_session, asha, subject="Late parcel")

    assert get(client, agent, "/tickets?q=%25").json()["total"] == 0
    assert get(client, agent, "/tickets?q=_").json()["total"] == 0


def test_sort_by_priority_then_oldest_first(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket_for(db_session, asha, subject="A low", priority="low",
               created_at=NOW - timedelta(hours=3))
    ticket_for(db_session, asha, subject="B urgent", priority="urgent",
               created_at=NOW - timedelta(hours=1))
    ticket_for(db_session, asha, subject="C high", priority="high",
               created_at=NOW - timedelta(hours=2))
    ticket_for(db_session, asha, subject="D high older", priority="high",
               created_at=NOW - timedelta(hours=4))

    response = get(client, agent, "/tickets?sort=priority")
    assert subjects(response) == ["B urgent", "D high older", "C high", "A low"]


def test_sort_oldest_and_newest(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket_for(db_session, asha, subject="Older", created_at=NOW - timedelta(hours=2))
    ticket_for(db_session, asha, subject="Newer", created_at=NOW - timedelta(hours=1))

    assert subjects(get(client, agent, "/tickets?sort=oldest")) == ["Older", "Newer"]
    assert subjects(get(client, agent, "/tickets?sort=newest")) == ["Newer", "Older"]


def test_customer_cannot_use_the_assignee_filter(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket_for(db_session, asha)
    response = get(client, asha, "/tickets?assigned_to=me")
    assert response.status_code == 403


def test_list_shows_customer_and_assigned_agent(client, db_session, make_user):
    asha = make_user(email="asha@example.com", name="Asha Rao")
    agent = staff(make_user, name="Dev Agent")
    ticket_for(db_session, asha, assigned_agent=agent)

    item = get(client, agent, "/tickets").json()["items"][0]
    assert item["customer"]["name"] == "Asha Rao"
    assert item["customer"]["email"] == "asha@example.com"
    assert item["assigned_agent"]["name"] == "Dev Agent"


def test_customer_sees_the_agent_name_but_not_the_agent_email(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user, name="Dev Agent")
    ticket = ticket_for(db_session, asha, assigned_agent=agent)

    body = get(client, asha, f"/tickets/{ticket.id}").json()
    assert set(body["assigned_agent"]) == {"id", "name"}
    assert body["assigned_agent"]["name"] == "Dev Agent"
    assert "agent@example.com" not in str(body)


# ---------- assigning ----------


def test_agent_takes_an_open_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(db_session, asha)

    response = post(client, agent, f"/tickets/{ticket.id}/assign")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "investigating"
    assert body["assigned_agent_id"] == str(agent.id)
    assert body["allowed_next_statuses"] == ["waiting_for_customer", "resolved"]


def test_assigning_keeps_the_status_of_a_ticket_that_is_not_open(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(db_session, asha, status=TicketStatus.WAITING_FOR_CUSTOMER)

    body = post(client, agent, f"/tickets/{ticket.id}/assign").json()
    assert body["status"] == "waiting_for_customer"
    assert body["assigned_agent_id"] == str(agent.id)


def test_second_agent_cannot_take_an_assigned_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    first = staff(make_user)
    second = staff(make_user, email="agent2@example.com", name="Agent Two")
    ticket = ticket_for(db_session, asha)

    assert post(client, first, f"/tickets/{ticket.id}/assign").status_code == 200
    response = post(client, second, f"/tickets/{ticket.id}/assign")
    assert response.status_code == 409
    db_session.refresh(ticket)
    assert ticket.assigned_agent_id == first.id


def test_assigning_to_yourself_twice_is_fine(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(db_session, asha)

    assert post(client, agent, f"/tickets/{ticket.id}/assign").status_code == 200
    response = post(client, agent, f"/tickets/{ticket.id}/assign")
    assert response.status_code == 200
    assert response.json()["status"] == "investigating"


def test_admin_can_reassign_to_another_agent(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    other = staff(make_user, email="agent2@example.com", name="Agent Two")
    admin = make_user(email="admin@example.com", role=UserRole.ADMIN)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=other
    )

    response = post(
        client, admin, f"/tickets/{ticket.id}/assign", {"agent_id": str(agent.id)}
    )
    assert response.status_code == 200
    assert response.json()["assigned_agent_id"] == str(agent.id)


def test_agent_cannot_assign_a_ticket_to_someone_else(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    other = staff(make_user, email="agent2@example.com", name="Agent Two")
    ticket = ticket_for(db_session, asha)

    response = post(
        client, agent, f"/tickets/{ticket.id}/assign", {"agent_id": str(other.id)}
    )
    assert response.status_code == 403


def test_a_customer_cannot_be_assigned_a_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    admin = make_user(email="admin@example.com", role=UserRole.ADMIN)
    ticket = ticket_for(db_session, asha)

    response = post(
        client, admin, f"/tickets/{ticket.id}/assign", {"agent_id": str(asha.id)}
    )
    assert response.status_code == 422


def test_customer_cannot_assign(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = ticket_for(db_session, asha)

    response = post(client, asha, f"/tickets/{ticket.id}/assign")
    assert response.status_code == 403
    db_session.refresh(ticket)
    assert ticket.assigned_agent_id is None


def test_assigning_an_unknown_ticket_returns_404(client, make_user):
    agent = staff(make_user)
    response = post(client, agent, f"/tickets/{uuid.uuid4()}/assign")
    assert response.status_code == 404


def test_assigned_agent_can_give_the_ticket_back(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    response = post(client, agent, f"/tickets/{ticket.id}/unassign")
    assert response.status_code == 200
    assert response.json()["assigned_agent"] is None


def test_other_agent_cannot_unassign(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    other = staff(make_user, email="agent2@example.com", name="Agent Two")
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    response = post(client, other, f"/tickets/{ticket.id}/unassign")
    assert response.status_code == 403


# ---------- changing the status ----------


def test_assigned_agent_can_resolve(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    response = post(
        client, agent, f"/tickets/{ticket.id}/status", {"status": "resolved"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None


def test_status_change_needs_the_ticket_to_be_assigned(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(db_session, asha, status=TicketStatus.INVESTIGATING)

    response = post(
        client, agent, f"/tickets/{ticket.id}/status", {"status": "resolved"}
    )
    assert response.status_code == 403


def test_other_agent_cannot_change_the_status(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    other = staff(make_user, email="agent2@example.com", name="Agent Two")
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=other
    )

    response = post(
        client, agent, f"/tickets/{ticket.id}/status", {"status": "resolved"}
    )
    assert response.status_code == 403


def test_invalid_status_change_returns_409(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    response = post(
        client, agent, f"/tickets/{ticket.id}/status", {"status": "closed"}
    )
    assert response.status_code == 409


def test_ai_only_arrow_is_refused_for_an_agent(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    response = post(
        client,
        agent,
        f"/tickets/{ticket.id}/status",
        {"status": "waiting_for_approval"},
    )
    assert response.status_code == 409


def test_admin_can_change_the_status_of_any_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    other = staff(make_user, email="agent2@example.com", name="Agent Two")
    admin = make_user(email="admin@example.com", role=UserRole.ADMIN)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=other
    )

    response = post(
        client,
        admin,
        f"/tickets/{ticket.id}/status",
        {"status": "waiting_for_customer"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "waiting_for_customer"


def test_customer_cannot_change_the_status(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = ticket_for(db_session, asha, status=TicketStatus.INVESTIGATING)

    response = post(
        client, asha, f"/tickets/{ticket.id}/status", {"status": "resolved"}
    )
    assert response.status_code == 403


def test_unknown_status_value_returns_422(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    response = post(
        client, agent, f"/tickets/{ticket.id}/status", {"status": "teleported"}
    )
    assert response.status_code == 422


# ---------- changing the priority ----------


def test_assigned_agent_can_change_the_priority(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    response = patch(
        client, agent, f"/tickets/{ticket.id}/priority", {"priority": "urgent"}
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "urgent"


def test_other_agent_cannot_change_the_priority(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    other = staff(make_user, email="agent2@example.com", name="Agent Two")
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=other
    )

    response = patch(
        client, agent, f"/tickets/{ticket.id}/priority", {"priority": "urgent"}
    )
    assert response.status_code == 403


def test_customer_cannot_change_the_priority(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = ticket_for(db_session, asha)

    response = patch(
        client, asha, f"/tickets/{ticket.id}/priority", {"priority": "urgent"}
    )
    assert response.status_code == 403


# ---------- what the detail page receives ----------


def test_agent_detail_has_the_customer_card_and_the_allowed_buttons(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com", name="Asha Rao")
    agent = staff(make_user)
    free = ticket_for(db_session, asha, status=TicketStatus.INVESTIGATING)
    mine = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    not_mine = get(client, agent, f"/tickets/{free.id}").json()
    assert not_mine["allowed_next_statuses"] == []  # not assigned to this agent
    assert not_mine["customer"]["name"] == "Asha Rao"
    assert not_mine["customer"]["email"] == "asha@example.com"

    assigned = get(client, agent, f"/tickets/{mine.id}").json()
    assert assigned["allowed_next_statuses"] == ["waiting_for_customer", "resolved"]


def test_customer_detail_has_no_status_buttons(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = staff(make_user)
    ticket = ticket_for(
        db_session, asha, status=TicketStatus.INVESTIGATING, assigned_agent=agent
    )

    body = get(client, asha, f"/tickets/{ticket.id}").json()
    assert body["allowed_next_statuses"] == []
