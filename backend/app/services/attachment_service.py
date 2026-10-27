import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath

import filetype
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attachment import Attachment
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User
from app.schemas.attachment import AttachmentRead
from app.services import storage_service, ticket_service

logger = logging.getLogger(__name__)

# What we accept, decided from the real bytes of the file,
# never from the file name or from the Content-Type the client sends.
ALLOWED_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


class EmptyFileError(Exception):
    """The uploaded file has no content."""


class FileTooLargeError(Exception):
    """The file is bigger than the allowed size."""


class UnsupportedFileTypeError(Exception):
    """The real type of the file is not on the allowed list."""


class TooManyAttachmentsError(Exception):
    """The ticket already has the maximum number of files."""


class StorageUnavailableError(Exception):
    """Object storage could not be reached or refused the file."""


def detect_content_type(data: bytes) -> str | None:
    """Look at the first bytes of the file. Returns an allowed type or None."""
    kind = filetype.guess(data[:8192])
    if kind is not None and kind.mime in ALLOWED_TYPES:
        return kind.mime
    return None


def _clean_file_name(raw: str | None, extension: str) -> str:
    """A safe name for display. The real file is stored under a random key."""
    name = PureWindowsPath(raw or "").name  # drops folders, for both / and \
    name = PurePosixPath(name).name
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    if not name:
        return f"file.{extension}"
    return name[:200]


def _get_visible_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> Ticket:
    """Same ownership rule as everywhere else: customers only reach their own tickets."""
    ticket = db.scalar(
        ticket_service.visible_tickets(user).where(Ticket.id == ticket_id)
    )
    if ticket is None:
        raise ticket_service.TicketNotFoundError
    return ticket


def _remove_stored_file(key: str) -> None:
    """Best effort. A failed cleanup must not hide the original error."""
    try:
        storage_service.delete_object(key)
    except Exception:
        logger.exception(
            "Could not delete orphaned file %s; a cleanup job must remove it", key
        )


def add_attachment(
    db: Session,
    user: User,
    ticket_id: uuid.UUID,
    file_name: str | None,
    data: bytes,
) -> Attachment:
    """Check the file, store it, then save its row. Undo the file if the row fails."""
    ticket = _get_visible_ticket(db, user, ticket_id)  # 404 if it is not theirs
    if ticket.status == TicketStatus.CLOSED.value:
        raise ticket_service.TicketClosedError

    if not data:
        raise EmptyFileError
    if len(data) > settings.max_upload_bytes:
        raise FileTooLargeError
    content_type = detect_content_type(data)
    if content_type is None:
        raise UnsupportedFileTypeError

    existing = (
        db.scalar(
            select(func.count())
            .select_from(Attachment)
            .where(Attachment.ticket_id == ticket.id)
        )
        or 0
    )
    if existing >= settings.max_attachments_per_ticket:
        raise TooManyAttachmentsError

    attachment_id = uuid.uuid4()
    extension = ALLOWED_TYPES[content_type]
    key = f"tickets/{ticket.id}/{attachment_id}.{extension}"

    try:
        storage_service.put_object(key, data, content_type)  # file first
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Storage upload failed for %s", key)
        raise StorageUnavailableError from exc

    attachment = Attachment(
        id=attachment_id,
        ticket_id=ticket.id,
        uploaded_by=user.id,
        storage_key=key,
        file_name=_clean_file_name(file_name, extension),
        content_type=content_type,
        size_bytes=len(data),
    )
    db.add(attachment)
    ticket.updated_at = datetime.now(timezone.utc)
    try:
        db.commit()  # row second
    except Exception:
        db.rollback()
        _remove_stored_file(key)  # do not leave an orphan behind
        raise
    db.refresh(attachment)
    return attachment


def list_attachments(db: Session, user: User, ticket_id: uuid.UUID) -> list[Attachment]:
    ticket = _get_visible_ticket(db, user, ticket_id)
    return list(
        db.scalars(
            select(Attachment)
            .where(Attachment.ticket_id == ticket.id)
            .order_by(Attachment.created_at, Attachment.id)
        )
    )


def to_read(attachment: Attachment) -> AttachmentRead:
    """Add a fresh signed download link. Signing is local maths, so it is cheap."""
    expires_in = settings.download_url_expire_seconds
    url = storage_service.presigned_download_url(
        attachment.storage_key, attachment.content_type, expires_in=expires_in
    )
    return AttachmentRead(
        id=attachment.id,
        ticket_id=attachment.ticket_id,
        uploaded_by=attachment.uploaded_by,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        created_at=attachment.created_at,
        download_url=url,
        download_url_expires_in=expires_in,
    )
