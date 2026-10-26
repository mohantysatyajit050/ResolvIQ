import uuid

from app.models import UserRole
from tests.factories import auth_header, make_order


def test_orders_require_login(client):
    assert client.get("/orders").status_code == 401


def test_customer_sees_only_own_orders(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    mine = [make_order(db_session, asha), make_order(db_session, asha)]
    make_order(db_session, ravi)

    response = client.get("/orders", headers=auth_header(asha))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {str(order.id) for order in mine}


def test_order_detail_includes_items_and_address(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha, quantity=2)

    response = client.get(f"/orders/{order.id}", headers=auth_header(asha))
    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["product"]["name"] == "Test Phone"
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["line_total_paise"] == 3_000_000
    assert body["shipping_address"]["pincode"] == "411001"


def test_customer_cannot_read_another_customers_order(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    ravi_order = make_order(db_session, ravi)

    response = client.get(f"/orders/{ravi_order.id}", headers=auth_header(asha))
    assert response.status_code == 404


def test_someone_elses_order_looks_the_same_as_a_missing_one(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    ravi_order = make_order(db_session, ravi)

    theirs = client.get(f"/orders/{ravi_order.id}", headers=auth_header(asha))
    missing = client.get(f"/orders/{uuid.uuid4()}", headers=auth_header(asha))
    assert theirs.status_code == missing.status_code == 404
    assert theirs.json() == missing.json()


def test_agent_can_read_any_order(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = make_user(email="agent@example.com", role=UserRole.AGENT)
    order = make_order(db_session, asha)

    response = client.get(f"/orders/{order.id}", headers=auth_header(agent))
    assert response.status_code == 200
    assert response.json()["id"] == str(order.id)


def test_invalid_order_id_returns_422(client, make_user):
    asha = make_user(email="asha@example.com")
    response = client.get("/orders/not-a-uuid", headers=auth_header(asha))
    assert response.status_code == 422


def test_orders_are_paginated(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    for _ in range(3):
        make_order(db_session, asha)

    first = client.get("/orders?limit=2&offset=0", headers=auth_header(asha)).json()
    assert len(first["items"]) == 2
    assert first["total"] == 3

    second = client.get("/orders?limit=2&offset=2", headers=auth_header(asha)).json()
    assert len(second["items"]) == 1
