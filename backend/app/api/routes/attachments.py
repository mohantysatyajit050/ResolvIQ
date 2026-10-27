import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.attachment import AttachmentRead
from app.services import attachment_service, ticket_service

router = APIRouter(prefix="/tickets", tags=["attachments"])


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    ticket_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload one evidence file. In production also limit the request size at the proxy."""
    # read one byte more than the limit, so "too big" is detected without loading a huge file
    data = file.file.read(settings.max_upload_bytes + 1)
    try:
        attachment = attachment_service.add_attachment(
            db, current_user, ticket_id, file.filename, data
        )
    except ticket_service.TicketNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        ) from None
    except ticket_service.TicketClosedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This ticket is closed"
        ) from None
    except attachment_service.EmptyFileError:
        raise HTTPException(status_code=422, detail="The file is empty") from None
    except attachment_service.FileTooLargeError:
        raise HTTPException(status_code=413, detail="The file is too large") from None
    except attachment_service.UnsupportedFileTypeError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, WebP and PDF files are accepted",
        ) from None
    except attachment_service.TooManyAttachmentsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ticket already has the maximum number of files",
        ) from None
    except attachment_service.StorageUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not available right now",
        ) from None
    return attachment_service.to_read(attachment)


@router.get("/{ticket_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The files on a ticket, each with a fresh temporary download link."""
    try:
        attachments = attachment_service.list_attachments(db, current_user, ticket_id)
    except ticket_service.TicketNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        ) from None
    return [attachment_service.to_read(attachment) for attachment in attachments]
