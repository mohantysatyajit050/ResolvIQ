import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem
from app.models.user import User
from app.services.access import sees_everything


class OrderNotFoundError(Exception):
    """The order does not exist, or the user may not see it (we never say which)."""


def visible_orders(user: User) -> Select:
    """Every order query starts here, so the ownership rule lives in one place."""
    stmt = select(Order)
    if not sees_everything(user):
        stmt = stmt.where(Order.user_id == user.id)
    return stmt


def list_orders(
    db: Session, user: User, limit: int, offset: int
) -> tuple[list[Order], int]:
    base = visible_orders(user)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    orders = db.scalars(
        base.order_by(Order.ordered_at.desc(), Order.id).limit(limit).offset(offset)
    ).all()
    return list(orders), total


def get_order(db: Session, user: User, order_id: uuid.UUID) -> Order:
    stmt = (
        visible_orders(user)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.shipping_address),
        )
        .execution_options(populate_existing=True)
    )
    order = db.scalar(stmt)
    if order is None:
        raise OrderNotFoundError
    return order
