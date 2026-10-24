import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, check_in
from app.models.order import Order


class TicketStatus(enum.StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketIntent(enum.StrEnum):
    LATE_DELIVERY = "late_delivery"
    DAMAGED_ITEM = "damaged_item"
    WRONG_ITEM = "wrong_item"
    REFUND_STATUS = "refund_status"
    OTHER = "other"


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(check_in("status", TicketStatus), name="ck_tickets_status"),
        CheckConstraint(check_in("priority", TicketPriority), name="ck_tickets_priority"),
        CheckConstraint(check_in("intent", TicketIntent), name="ck_tickets_intent"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="RESTRICT"), index=True
    )
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(30),
        default=TicketStatus.OPEN.value,
        server_default=TicketStatus.OPEN.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(10),
        default=TicketPriority.MEDIUM.value,
        server_default=TicketPriority.MEDIUM.value,
    )
    intent: Mapped[str | None] = mapped_column(String(30))  # set later by the AI router
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    order: Mapped[Order] = relationship()
    messages: Mapped[list["TicketMessage"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TicketMessage.created_at",
    )
