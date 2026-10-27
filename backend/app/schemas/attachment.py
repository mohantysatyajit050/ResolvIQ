import uuid
from datetime import datetime

from pydantic import BaseModel


class AttachmentRead(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    uploaded_by: uuid.UUID | None
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime
    download_url: str  # a temporary signed link to this one file
    download_url_expires_in: int  # seconds until the link stops working
