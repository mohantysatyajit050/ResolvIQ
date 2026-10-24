import uuid

from sqlalchemy import BigInteger, CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_paise >= 0", name="ck_products_price"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100), index=True)
    price_paise: Mapped[int] = mapped_column(BigInteger)  # 1 rupee = 100 paise
    description: Mapped[str | None] = mapped_column(Text)
