from pydantic import BaseModel, Field

from app.models.ticket import TicketIntent, TicketPriority


class RouterResult(BaseModel):
    """What the intent router must return. Any other value is rejected."""

    intent: TicketIntent
    priority: TicketPriority
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=500)
