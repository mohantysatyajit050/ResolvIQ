from datetime import datetime, timedelta, timezone  # noqa: F401  (kept for readers of the tests)

from app.core.config import settings
from app.core.cookies import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from tests.factories import auth_header, make_order

PASSWORD = "StrongPass123"
NEW_TICKET = {"subject": "Order is late", "description": "It never arrived."}


def login(client, email: str):
    return client.post("/auth/login", json={"email": email, "password": PASSWORD})


def cookie_lines(response) -> dict[str, str]:
    """The Set-Cookie headers of a response, by cookie name, in lower case."""
    lines = response.headers.get_list("set-cookie")
    return {line.split("=", 1)[0]: line.lower() for line in lines}


def ticket_body(order) -> dict:
    return {**NEW_TICKET, "order_id": str(order.id)}


def test_login_sets_an_httponly_session_cookie(client, make_user):
    make_user(email="asha@example.com")
    session = cookie_lines(login(client, "asha@example.com"))[ACCESS_COOKIE_NAME]
    assert "httponly" in session
    assert "samesite=lax" in session
    assert "path=/" in session
    assert f"max-age={settings.access_token_expire_minutes * 60}" in session


def test_csrf_cookie_is_readable_by_javascript(client, make_user):
    make_user(email="asha@example.com")
    csrf = cookie_lines(login(client, "asha@example.com"))[CSRF_COOKIE_NAME]
    assert "httponly" not in csrf


def test_cookie_alone_authenticates_safe_requests(client, make_user):
    make_user(email="asha@example.com")
    login(client, "asha@example.com")  # the client keeps the cookies, like a browser
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "asha@example.com"


def test_cookie_write_without_csrf_header_is_refused(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    login(client, "asha@example.com")

    response = client.post("/tickets", json=ticket_body(order))
    assert response.status_code == 403
    assert "csrf" in response.json()["detail"].lower()


def test_cookie_write_with_matching_csrf_header_is_accepted(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    login(client, "asha@example.com")

    csrf = client.cookies.get(CSRF_COOKIE_NAME)
    response = client.post(
        "/tickets", json=ticket_body(order), headers={CSRF_HEADER_NAME: csrf}
    )
    assert response.status_code == 201


def test_cookie_write_with_wrong_csrf_header_is_refused(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    login(client, "asha@example.com")

    response = client.post(
        "/tickets", json=ticket_body(order), headers={CSRF_HEADER_NAME: "not-the-token"}
    )
    assert response.status_code == 403


def test_bearer_requests_do_not_need_a_csrf_token(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    order = make_order(db_session, asha)
    response = client.post(
        "/tickets", json=ticket_body(order), headers=auth_header(asha)
    )
    assert response.status_code == 201


def test_logout_clears_the_session(client, make_user):
    make_user(email="asha@example.com")
    login(client, "asha@example.com")
    assert client.get("/auth/me").status_code == 200

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_garbage_session_cookie_is_rejected(client):
    client.cookies.set(ACCESS_COOKIE_NAME, "garbage", domain="testserver")
    assert client.get("/auth/me").status_code == 401
