import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, check_in
from app.models.ticket import TicketIntent


class Policy(Base):
    """One chunk (one '## section') of a policy document.

    Day 15 adds the embedding column used for search.
    """

    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint(check_in("applies_to", TicketIntent), name="ck_policies_applies_to"),
        CheckConstraint("version >= 1", name="ck_policies_version"),
        CheckConstraint("chunk_index >= 0", name="ck_policies_chunk_index"),
        UniqueConstraint(
            "slug", "version", "chunk_index", name="uq_policies_slug_version_chunk"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(200))
    section: Mapped[str] = mapped_column(String(200))
    chunk_index: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default=text("1")
    )
    applies_to: Mapped[str] = mapped_column(String(30), index=True)
    content: Mapped[str] = mapped_column(Text)
    # fingerprint of title + applies_to + heading + content, to spot changed chunks
    content_hash: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
