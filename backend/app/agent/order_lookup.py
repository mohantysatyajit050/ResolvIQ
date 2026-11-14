"""Order lookup tool: the order_lookup node of the agent. Plain code, no LLM.

Trust rules:
- The order always comes from ticket.order_id, never from the complaint text.
- The lookup runs as the ticket's owner, so the same ownership rule as the
  orders API applies. The agent never sees other people's orders.
- Only the facts a decision needs are returned. No address, no user data.
- Dates are turned into numbers here (days_late), so the LLM never does date math.
- A failed lookup is a result, not a crash. The graph decides to escalate.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.ticket import Ticket
from app.services.order_service import OrderNotFoundError, get_order


class LookupFailure(StrEnum):
    # missing or not owned by the ticket's customer (we never say which)
    ORDER_NOT_FOUND = "order_not_found"
    # an order with no items is broken data, so a human should look at it
    NO_ITEMS = "no_items"


@dataclass(frozen=True)
class ItemFacts:
    product_name: str
    quantity: int
    unit_price_paise: int


@dataclass(frozen=True)
class OrderFacts:
    order_id: uuid.UUID
    status: str
    ordered_at: datetime
    expected_delivery_date: date | None
    delivered_at: datetime | None
    # 0 = on time, None = not applicable (no expected date, cancelled or returned)
    days_late: int | None
    total_paise: int
    items: tuple[ItemFacts, ...]


@dataclass(frozen=True)
class OrderLookupResult:
    facts: OrderFacts | None = None
    failure: LookupFailure | None = None

    @property
    def found(self) -> bool:
        return self.facts is not None


def compute_days_late(order: Order, today: date) -> int | None:
    """How many days past the expected date the order arrived (or still has not)."""
    expected = order.expected_delivery_date
    if expected is None:
        return None
    if order.delivered_at is not None:
        end = order.delivered_at.date()
    elif order.status in (OrderStatus.CANCELLED, OrderStatus.RETURNED):
        return None  # no delivery is being waited for any more
    else:
        end = today
    return max((end - expected).days, 0)


def lookup_order(
    db: Session, ticket: Ticket, today: date | None = None
) -> OrderLookupResult:
    """Fetch the facts about the order this ticket is about."""
    today = today or datetime.now(timezone.utc).date()
    try:
        # run as the ticket's owner so the normal ownership rule applies
        order = get_order(db, ticket.customer, ticket.order_id)
    except OrderNotFoundError:
        return OrderLookupResult(failure=LookupFailure.ORDER_NOT_FOUND)

    if not order.items:
        return OrderLookupResult(failure=LookupFailure.NO_ITEMS)

    items = tuple(
        ItemFacts(
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price_paise=item.unit_price_paise,
        )
        for item in sorted(order.items, key=lambda i: i.product.name)
    )
    facts = OrderFacts(
        order_id=order.id,
        status=order.status,
        ordered_at=order.ordered_at,
        expected_delivery_date=order.expected_delivery_date,
        delivered_at=order.delivered_at,
        days_late=compute_days_late(order, today),
        total_paise=order.total_paise,
        items=items,
    )
    return OrderLookupResult(facts=facts)
