import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, check_in
from app.models.address import Address
from app.models.product import Product


class OrderStatus(enum.StrEnum):
    PLACED = "placed"
    SHIPPED = "shipped"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(check_in("status", OrderStatus), name="ck_orders_status"),
        CheckConstraint("total_paise >= 0", name="ck_orders_total"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    shipping_address_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=OrderStatus.PLACED.value,
        server_default=OrderStatus.PLACED.value,
        index=True,
    )
    total_paise: Mapped[int] = mapped_column(BigInteger)
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expected_delivery_date: Mapped[date | None] = mapped_column(Date)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    shipping_address: Mapped[Address] = relationship()


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity"),
        CheckConstraint("unit_price_paise >= 0", name="ck_order_items_price"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT")
    )
    quantity: Mapped[int] = mapped_column(Integer)
    # price at the time of the order; later product price changes must not change it
    unit_price_paise: Mapped[int] = mapped_column(BigInteger)

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
