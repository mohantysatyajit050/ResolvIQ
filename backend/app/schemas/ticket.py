import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.ticket import TicketIntent, TicketPriority, TicketStatus
from app.models.ticket_message import SenderType
from app.schemas.order import OrderRead

Subject = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
LongText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]


class TicketCreate(BaseModel):
    """Body of POST /tickets. user_id, status and priority are set by the server."""

    model_config = ConfigDict(extra="forbid")

    order_id: uuid.UUID
    subject: Subject
    description: LongText


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: LongText


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sender_id: uuid.UUID | None
    sender_type: SenderType
    body: str
    created_at: datetime


class CustomerBrief(BaseModel):
    """Who raised the ticket. Customers only ever see themselves here."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone: str | None


class AgentBrief(BaseModel):
    """The agent on a ticket: the name only, never the email or phone."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class AssignRequest(BaseModel):
    """Body of POST /tickets/{id}/assign. Empty means "assign it to me"."""

    model_config = ConfigDict(extra="forbid")

    agent_id: uuid.UUID | None = None  # only an admin may name someone else


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: TicketStatus


class PriorityChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: TicketPriority


class TicketSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    order_id: uuid.UUID
    assigned_agent_id: uuid.UUID | None
    subject: str
    status: TicketStatus
    priority: TicketPriority
    intent: TicketIntent | None
    sla_due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    customer: CustomerBrief
    assigned_agent: AgentBrief | None


class TicketDetail(TicketSummary):
    description: str
    order: OrderRead
    messages: list[MessageRead]
    # What the caller may move this ticket to. The page shows exactly these buttons.
    allowed_next_statuses: list[TicketStatus] = Field(default_factory=list)
