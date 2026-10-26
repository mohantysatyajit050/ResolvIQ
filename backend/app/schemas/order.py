import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.order import OrderStatus


class AddressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    address_line: str
    city: str
    state: str
    pincode: str


class ProductBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product: ProductBrief
    quantity: int
    unit_price_paise: int

    @computed_field
    @property
    def line_total_paise(self) -> int:
        return self.quantity * self.unit_price_paise


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    status: OrderStatus
    total_paise: int
    ordered_at: datetime
    expected_delivery_date: date | None
    delivered_at: datetime | None


class OrderRead(OrderSummary):
    shipping_address: AddressRead
    items: list[OrderItemRead]
