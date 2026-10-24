import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Address(Base):
    __tablename__ = "addresses"
    __table_args__ = (
        CheckConstraint("pincode ~ '^[1-9][0-9]{5}$'", name="ck_addresses_pincode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    address_line: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    pincode: Mapped[str] = mapped_column(String(6))
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
