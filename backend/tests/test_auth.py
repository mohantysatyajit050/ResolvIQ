from sqlalchemy import select

from app.models.user import User

VALID = {
    "name": "Asha Rao",
    "email": "asha@example.com",
    "password": "StrongPass123",
    "phone": "+919876543210",
}


def test_register_success(client):
    response = client.post("/auth/register", json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "asha@example.com"
    assert body["role"] == "customer"
    assert body["is_active"] is True
    assert "id" in body and "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_password_is_stored_as_argon2_hash(client, db_session):
    client.post("/auth/register", json=VALID)
    user = db_session.scalar(select(User).where(User.email == "asha@example.com"))
    assert user.password_hash != VALID["password"]
    assert user.password_hash.startswith("$argon2")


def test_duplicate_email_returns_409(client):
    client.post("/auth/register", json=VALID)
    response = client.post("/auth/register", json=VALID)
    assert response.status_code == 409


def test_email_is_case_insensitive(client):
    client.post("/auth/register", json=VALID)
    other = {**VALID, "email": "ASHA@Example.com"}
    assert client.post("/auth/register", json=other).status_code == 409


def test_role_in_request_is_rejected(client):
    response = client.post("/auth/register", json={**VALID, "role": "admin"})
    assert response.status_code == 422


def test_short_password_rejected(client):
    response = client.post("/auth/register", json={**VALID, "password": "short"})
    assert response.status_code == 422


def test_invalid_email_rejected(client):
    response = client.post("/auth/register", json={**VALID, "email": "not-an-email"})
    assert response.status_code == 422


def test_phone_is_optional(client):
    data = {key: value for key, value in VALID.items() if key != "phone"}
    response = client.post("/auth/register", json=data)
    assert response.status_code == 201
    assert response.json()["phone"] is None
