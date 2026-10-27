import uuid

import pytest
from botocore.exceptions import EndpointConnectionError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models import Attachment, TicketStatus, UserRole
from app.services import storage_service
from tests.factories import auth_header, make_order, make_ticket

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"0" * 64
NOT_AN_IMAGE = b"MZ this is a program, not a picture"


class FakeStorage:
    """Stands in for real storage, so these tests are fast and need no Docker service."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.fail_next_put = False

    def put_object(self, key, data, content_type):
        if self.fail_next_put:
            self.fail_next_put = False
            raise EndpointConnectionError(endpoint_url="http://storage.test")
        self.objects[key] = (data, content_type)

    def delete_object(self, key):
        self.objects.pop(key, None)

    def presigned_download_url(self, key, content_type, expires_in=300):
        return f"https://storage.test/{key}?X-Amz-Expires={expires_in}&X-Amz-Signature=fake"


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    fake = FakeStorage()
    monkeypatch.setattr(storage_service, "put_object", fake.put_object)
    monkeypatch.setattr(storage_service, "delete_object", fake.delete_object)
    monkeypatch.setattr(
        storage_service, "presigned_download_url", fake.presigned_download_url
    )
    return fake


def new_ticket(db, user, **kwargs):
    return make_ticket(db, user, make_order(db, user), **kwargs)


def upload(client, ticket, user, data=PNG, name="photo.png", content_type="image/png"):
    return client.post(
        f"/tickets/{ticket.id}/attachments",
        files={"file": (name, data, content_type)},
        headers=auth_header(user),
    )


def count_attachments(db) -> int:
    return db.scalar(select(func.count()).select_from(Attachment))


# ---------- uploading ----------


def test_upload_png_success(client, db_session, make_user, storage):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    response = upload(client, ticket, asha)
    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(PNG)
    assert body["file_name"] == "photo.png"
    assert body["ticket_id"] == str(ticket.id)
    assert body["uploaded_by"] == str(asha.id)
    assert body["download_url"].startswith("https://storage.test/")
    assert body["download_url_expires_in"] == settings.download_url_expire_seconds

    (key,) = storage.objects
    assert key.startswith(f"tickets/{ticket.id}/")
    assert key.endswith(".png")
    assert "photo" not in key  # the user's file name is never part of the key
    assert storage.objects[key] == (PNG, "image/png")
    assert count_attachments(db_session) == 1


def test_real_type_comes_from_the_bytes_not_the_name(
    client, db_session, make_user, storage
):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    # the name and the Content-Type both say PNG, but the bytes are a JPEG
    response = upload(client, ticket, asha, data=JPEG, name="evidence.png")
    assert response.status_code == 201
    assert response.json()["content_type"] == "image/jpeg"
    (key,) = storage.objects
    assert key.endswith(".jpg")


def test_pdf_is_accepted(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)
    response = upload(
        client, ticket, asha, data=PDF, name="receipt.pdf", content_type="application/pdf"
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == "application/pdf"


def test_renamed_program_is_rejected(client, db_session, make_user, storage):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    response = upload(
        client, ticket, asha, data=NOT_AN_IMAGE, name="photo.jpg", content_type="image/jpeg"
    )
    assert response.status_code == 415
    assert storage.objects == {}
    assert count_attachments(db_session) == 0


def test_file_that_is_too_large_returns_413(
    client, db_session, make_user, storage, monkeypatch
):
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    response = upload(client, ticket, asha, data=PNG + b"0" * 100)
    assert response.status_code == 413
    assert storage.objects == {}


def test_empty_file_returns_422(client, db_session, make_user, storage):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    response = upload(client, ticket, asha, data=b"")
    assert response.status_code == 422
    assert storage.objects == {}


def test_too_many_files_returns_409(
    client, db_session, make_user, storage, monkeypatch
):
    monkeypatch.setattr(settings, "max_attachments_per_ticket", 2)
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    assert upload(client, ticket, asha).status_code == 201
    assert upload(client, ticket, asha).status_code == 201
    assert upload(client, ticket, asha).status_code == 409
    assert len(storage.objects) == 2


def test_customer_cannot_upload_to_another_customers_ticket(
    client, db_session, make_user, storage
):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    ravi_ticket = new_ticket(db_session, ravi)

    response = upload(client, ravi_ticket, asha)
    assert response.status_code == 404
    assert storage.objects == {}
    assert count_attachments(db_session) == 0


def test_agent_can_upload_to_any_ticket(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    agent = make_user(email="agent@example.com", role=UserRole.AGENT)
    ticket = new_ticket(db_session, asha)

    response = upload(client, ticket, agent)
    assert response.status_code == 201
    assert response.json()["uploaded_by"] == str(agent.id)


def test_cannot_upload_to_closed_ticket(client, db_session, make_user, storage):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha, status=TicketStatus.CLOSED)

    response = upload(client, ticket, asha)
    assert response.status_code == 409
    assert storage.objects == {}


def test_upload_requires_login(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)
    response = client.post(
        f"/tickets/{ticket.id}/attachments",
        files={"file": ("photo.png", PNG, "image/png")},
    )
    assert response.status_code == 401


def test_file_name_is_cleaned(client, db_session, make_user, storage):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    response = upload(client, ticket, asha, name="../../etc/passwd.png")
    assert response.status_code == 201
    assert response.json()["file_name"] == "passwd.png"
    (key,) = storage.objects
    assert "passwd" not in key
    assert ".." not in key


# ---------- when something fails ----------


def test_database_failure_removes_the_stored_file(
    client, db_session, make_user, storage, monkeypatch
):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)

    def broken_commit():
        raise SQLAlchemyError("database is down")

    monkeypatch.setattr(db_session, "commit", broken_commit)
    with pytest.raises(SQLAlchemyError):
        upload(client, ticket, asha)
    assert storage.objects == {}  # no orphan file is left behind


def test_storage_failure_returns_503_and_saves_nothing(
    client, db_session, make_user, storage
):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)
    storage.fail_next_put = True

    response = upload(client, ticket, asha)
    assert response.status_code == 503
    assert count_attachments(db_session) == 0


# ---------- listing ----------


def test_list_attachments_returns_download_links(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)
    upload(client, ticket, asha)
    upload(client, ticket, asha, data=PDF, name="receipt.pdf", content_type="application/pdf")

    response = client.get(f"/tickets/{ticket.id}/attachments", headers=auth_header(asha))
    assert response.status_code == 200
    items = response.json()
    assert [item["content_type"] for item in items] == ["image/png", "application/pdf"]
    assert all(item["download_url"].startswith("https://storage.test/") for item in items)


def test_customer_cannot_list_another_customers_attachments(
    client, db_session, make_user
):
    asha = make_user(email="asha@example.com")
    ravi = make_user(email="ravi@example.com")
    ravi_ticket = new_ticket(db_session, ravi)
    upload(client, ravi_ticket, ravi)

    response = client.get(
        f"/tickets/{ravi_ticket.id}/attachments", headers=auth_header(asha)
    )
    assert response.status_code == 404
    missing = client.get(
        f"/tickets/{uuid.uuid4()}/attachments", headers=auth_header(asha)
    )
    assert response.json() == missing.json()  # nothing reveals that the ticket exists


def test_list_requires_login(client, db_session, make_user):
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)
    assert client.get(f"/tickets/{ticket.id}/attachments").status_code == 401


def test_deleting_a_ticket_removes_rows_but_not_stored_files(
    client, db_session, make_user, storage
):
    """The database cascades to the rows. Storage does not know about it, so a
    cleanup job would be needed if tickets were ever deleted."""
    asha = make_user(email="asha@example.com")
    ticket = new_ticket(db_session, asha)
    upload(client, ticket, asha)
    assert count_attachments(db_session) == 1

    db_session.delete(ticket)
    db_session.commit()
    assert count_attachments(db_session) == 0
    assert len(storage.objects) == 1
