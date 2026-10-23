from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.core.config import settings
from app.core.security import create_access_token
from app.main import app as fastapi_app
from app.models.user import User, UserRole

PASSWORD = "StrongPass123"
AGENT_ONLY = "/_test/agent-only"

# A small test-only route, so require_role can be tested before real agent routes exist.
_test_router = APIRouter()


@_test_router.get(AGENT_ONLY)
def _agent_only(user: User = Depends(require_role(UserRole.AGENT, UserRole.ADMIN))):
    return {"email": user.email}


fastapi_app.include_router(_test_router)


def auth_header(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def login(client, email: str, password: str = PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


# ---------- login ----------


def test_login_success(client, make_user):
    make_user(email="asha@example.com")
    response = login(client, "asha@example.com")
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_expire_minutes * 60
    assert body["access_token"]


def test_token_contains_only_safe_claims(client, make_user):
    user = make_user(email="asha@example.com")
    token = login(client, "asha@example.com").json()["access_token"]
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == str(user.id)
    assert set(payload) == {"sub", "iat", "exp"}  # no password, no hash, no role


def test_login_email_is_case_insensitive(client, make_user):
    make_user(email="asha@example.com")
    assert login(client, "ASHA@Example.com").status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(client, make_user):
    make_user(email="asha@example.com")
    wrong_password = login(client, "asha@example.com", "WrongPass999")
    unknown_email = login(client, "nobody@example.com")
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_disabled_account_cannot_login(client, make_user):
    make_user(email="asha@example.com", is_active=False)
    assert login(client, "asha@example.com").status_code == 403


# ---------- /auth/me and get_current_user ----------


def test_me_with_valid_token(client, make_user):
    user = make_user(email="asha@example.com")
    response = client.get("/auth/me", headers=auth_header(user))
    assert response.status_code == 200
    assert response.json()["email"] == "asha@example.com"
    assert "password_hash" not in response.json()


def test_me_without_token_returns_401(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_garbage_token_returns_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_token_signed_with_wrong_secret_is_rejected(client, make_user):
    user = make_user(email="asha@example.com")
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=5)},
        "x" * 64,
        algorithm="HS256",
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_unsigned_token_is_rejected(client, make_user):
    user = make_user(email="asha@example.com")
    now = datetime.now(timezone.utc)
    unsigned = jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=5)},
        None,
        algorithm="none",
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {unsigned}"})
    assert response.status_code == 401


def test_expired_token_is_rejected(client, make_user):
    user = make_user(email="asha@example.com")
    expired = create_access_token(user.id, expires_delta=timedelta(seconds=-10))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_token_of_deleted_user_is_rejected(client, make_user, db_session):
    user = make_user(email="asha@example.com")
    headers = auth_header(user)
    db_session.delete(user)
    db_session.commit()
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_disabled_user_with_valid_token_gets_403(client, make_user, db_session):
    user = make_user(email="asha@example.com")
    headers = auth_header(user)
    user.is_active = False
    db_session.commit()
    assert client.get("/auth/me", headers=headers).status_code == 403


# ---------- require_role ----------


def test_agent_route_without_token_returns_401(client):
    assert client.get(AGENT_ONLY).status_code == 401


def test_customer_cannot_use_agent_route(client, make_user):
    user = make_user(email="customer@example.com", role=UserRole.CUSTOMER)
    assert client.get(AGENT_ONLY, headers=auth_header(user)).status_code == 403


def test_agent_can_use_agent_route(client, make_user):
    user = make_user(email="agent@example.com", role=UserRole.AGENT)
    assert client.get(AGENT_ONLY, headers=auth_header(user)).status_code == 200


def test_admin_can_use_agent_route(client, make_user):
    user = make_user(email="admin@example.com", role=UserRole.ADMIN)
    assert client.get(AGENT_ONLY, headers=auth_header(user)).status_code == 200


def test_role_change_takes_effect_immediately(client, make_user, db_session):
    user = make_user(email="agent@example.com", role=UserRole.AGENT)
    headers = auth_header(user)
    assert client.get(AGENT_ONLY, headers=headers).status_code == 200

    user.role = UserRole.CUSTOMER.value  # an admin demotes the user
    db_session.commit()
    assert client.get(AGENT_ONLY, headers=headers).status_code == 403
