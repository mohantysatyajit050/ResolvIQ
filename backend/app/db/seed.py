"""Fill the development database with fake but realistic data.

Run from the backend folder:
    uv run python -m app.db.seed            (adds data, skips if products already exist)
    uv run python -m app.db.seed --reset    (wipes shop data, then seeds again)
"""

import random
import sys
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Address,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    SenderType,
    Ticket,
    TicketMessage,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)

SEED_EMAIL_SUFFIX = "@resolviq.dev"
DEV_PASSWORD = "DevPass123"  # development only; every seeded user gets this password

LATE_SUBJECT = "Order is 5 days late"
DAMAGED_SUBJECT = "Phone screen cracked on arrival"
NOT_RECEIVED_SUBJECT = "Refund for an order I never received"

PHONE_NAME = "Smartphone X1 5G (128GB)"
EARBUDS_NAME = "Wireless Earbuds Pro"
TABLET_NAME = "Tablet 10-inch 128GB"

# (name, category, price in paise)
PRODUCTS = [
    (PHONE_NAME, "Phones", 1_799_900),
    (EARBUDS_NAME, "Audio", 129_900),
    ("Induction Cooktop 2000W", "Kitchen", 249_900),
    ("Mixer Grinder 750W", "Kitchen", 349_900),
    ("Smart TV 43-inch 4K", "TV", 2_799_900),
    ("Running Shoes", "Footwear", 189_900),
    ("Slim Fit Jeans", "Clothing", 249_900),
    ("Steel Water Bottle 1L", "Home", 69_900),
    ("Power Bank 20000mAh", "Accessories", 179_900),
    ("Smartwatch Active", "Wearables", 399_900),
    ("Laptop 15.6-inch", "Computers", 4_599_900),
    (TABLET_NAME, "Tablets", 2_500_000),  # exactly 25,000 rupees
]

CITIES = [
    ("Mumbai", "Maharashtra"),
    ("Pune", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Bengaluru", "Karnataka"),
    ("Hyderabad", "Telangana"),
    ("Chennai", "Tamil Nadu"),
    ("Kolkata", "West Bengal"),
    ("Ahmedabad", "Gujarat"),
    ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"),
    ("Kochi", "Kerala"),
]

# (min, max) days since the order was placed, for each status
DAYS_SINCE_ORDER = {
    OrderStatus.PLACED: (0, 1),
    OrderStatus.SHIPPED: (2, 4),
    OrderStatus.OUT_FOR_DELIVERY: (4, 6),
    OrderStatus.DELIVERED: (8, 40),
    OrderStatus.CANCELLED: (3, 20),
}

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)


def phone() -> str:
    return "+91" + str(random.randint(6_000_000_000, 9_999_999_999))


def make_user(name: str, email: str, role: UserRole, password_hash: str) -> User:
    return User(
        name=name,
        email=email,
        password_hash=password_hash,
        role=role.value,
        phone=phone(),
    )


def make_address(user: User) -> Address:
    city, state = random.choice(CITIES)
    return Address(
        user_id=user.id,
        address_line=f"{random.randint(1, 250)}, {fake.last_name()} Road",
        city=city,
        state=state,
        pincode=str(random.randint(100_000, 999_999)),
        is_default=True,
    )


def make_order(
    now: datetime,
    customer: User,
    address: Address,
    lines: list[tuple[Product, int]],
    status: OrderStatus,
    ordered_days_ago: int,
    expected_in_days: int,
    delivered_days_ago: int | None = None,
) -> Order:
    """expected_in_days is negative when the expected date is already in the past."""
    items = [
        OrderItem(
            product_id=product.id,
            quantity=quantity,
            unit_price_paise=product.price_paise,  # price snapshot
        )
        for product, quantity in lines
    ]
    delivered_at = None
    if delivered_days_ago is not None:
        delivered_at = now - timedelta(days=delivered_days_ago)
    return Order(
        user_id=customer.id,
        shipping_address_id=address.id,
        status=status.value,
        total_paise=sum(item.quantity * item.unit_price_paise for item in items),
        ordered_at=now - timedelta(days=ordered_days_ago),
        expected_delivery_date=(now + timedelta(days=expected_in_days)).date(),
        delivered_at=delivered_at,
        items=items,
    )


def random_order(
    now: datetime, customer: User, address: Address, products: list[Product]
) -> Order:
    lines = [
        (random.choice(products), random.randint(1, 2))
        for _ in range(random.randint(1, 3))
    ]
    status = random.choices(
        [
            OrderStatus.DELIVERED,
            OrderStatus.SHIPPED,
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.PLACED,
            OrderStatus.CANCELLED,
        ],
        weights=[60, 12, 8, 12, 8],
    )[0]
    days = random.randint(*DAYS_SINCE_ORDER[status])
    delivered_days_ago = None
    if status is OrderStatus.DELIVERED:
        delivered_days_ago = days - 5 - random.choice([0, 1])
    return make_order(
        now,
        customer,
        address,
        lines,
        status,
        ordered_days_ago=days,
        expected_in_days=5 - days,
        delivered_days_ago=delivered_days_ago,
    )


def make_ticket(
    now: datetime,
    customer: User,
    order: Order,
    subject: str,
    description: str,
    status: TicketStatus,
    priority: TicketPriority,
    minutes_ago: int,
    assigned_agent: User | None = None,
    replies: tuple = (),
) -> Ticket:
    """replies is a list of (sender_type, sender_user_or_None, text)."""
    created = now - timedelta(minutes=minutes_ago)
    messages = [
        TicketMessage(
            sender_id=customer.id,
            sender_type=SenderType.CUSTOMER.value,
            body=description,
            created_at=created,
        )
    ]
    for index, (sender_type, sender, body) in enumerate(replies, start=1):
        messages.append(
            TicketMessage(
                sender_id=sender.id if sender else None,
                sender_type=sender_type.value,
                body=body,
                created_at=created + timedelta(minutes=30 * index),
            )
        )
    updated = created + timedelta(minutes=30 * len(replies))
    finished = status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
    return Ticket(
        user_id=customer.id,
        order_id=order.id,
        assigned_agent_id=assigned_agent.id if assigned_agent else None,
        subject=subject,
        description=description,
        status=status.value,
        priority=priority.value,
        created_at=created,
        updated_at=updated,
        resolved_at=updated if finished else None,
        messages=messages,
    )


def reset(db: Session) -> None:
    """Delete all shop data and the seeded users (children first, because of RESTRICT)."""
    for model in (TicketMessage, Ticket, OrderItem, Order, Address, Product):
        db.execute(delete(model))
    db.execute(delete(User).where(User.email.like(f"%{SEED_EMAIL_SUFFIX}")))
    db.commit()


def seed(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Product)):
        print("Products already exist, so nothing was added. Use --reset to start fresh.")
        return

    now = datetime.now(timezone.utc)
    password_hash = hash_password(DEV_PASSWORD)  # hashed once, reused for every user

    # users
    admin = make_user("Dev Admin", f"admin{SEED_EMAIL_SUFFIX}", UserRole.ADMIN, password_hash)
    agent = make_user("Dev Agent", f"agent{SEED_EMAIL_SUFFIX}", UserRole.AGENT, password_hash)
    customers = [
        make_user(fake.name(), f"customer{i}{SEED_EMAIL_SUFFIX}", UserRole.CUSTOMER, password_hash)
        for i in range(1, 6)
    ]
    db.add_all([admin, agent, *customers])
    db.flush()  # gives every row its id

    # products and addresses
    products = {
        name: Product(name=name, category=category, price_paise=price, description=f"{name} (demo product)")
        for name, category, price in PRODUCTS
    }
    addresses = {customer.id: make_address(customer) for customer in customers}
    db.add_all([*products.values(), *addresses.values()])
    db.flush()
    product_list = list(products.values())

    # orders: the 3 scenarios from the design, then random ones
    late = make_order(
        now, customers[0], addresses[customers[0].id],
        [(products[EARBUDS_NAME], 1)], OrderStatus.SHIPPED,
        ordered_days_ago=9, expected_in_days=-5,
    )
    damaged = make_order(
        now, customers[1], addresses[customers[1].id],
        [(products[PHONE_NAME], 1)], OrderStatus.DELIVERED,
        ordered_days_ago=8, expected_in_days=-3, delivered_days_ago=3,
    )
    not_received = make_order(
        now, customers[2], addresses[customers[2].id],
        [(products[TABLET_NAME], 1)], OrderStatus.DELIVERED,
        ordered_days_ago=12, expected_in_days=-6, delivered_days_ago=6,
    )
    orders = [late, damaged, not_received]
    for customer in customers:
        for _ in range(3):
            orders.append(random_order(now, customer, addresses[customer.id], product_list))
    db.add_all(orders)
    db.flush()

    def first_order_of(customer: User) -> Order:
        return next(order for order in orders if order.user_id == customer.id)

    # tickets
    tickets = [
        make_ticket(
            now, customers[0], late, LATE_SUBJECT,
            "My order was supposed to arrive 5 days ago and it is still not here. Where is it?",
            TicketStatus.OPEN, TicketPriority.MEDIUM, minutes_ago=120,
        ),
        make_ticket(
            now, customers[1], damaged, DAMAGED_SUBJECT,
            "I received my phone 3 days ago and the screen is cracked. I want a replacement or a refund.",
            TicketStatus.OPEN, TicketPriority.HIGH, minutes_ago=90,
        ),
        make_ticket(
            now, customers[2], not_received, NOT_RECEIVED_SUBJECT,
            "My account says the tablet was delivered, but I never received it. I want a full refund of 25,000 rupees.",
            TicketStatus.OPEN, TicketPriority.URGENT, minutes_ago=45,
        ),
        make_ticket(
            now, customers[3], first_order_of(customers[3]), "Item missing from my package",
            "One item was missing from my package.",
            TicketStatus.RESOLVED, TicketPriority.MEDIUM, minutes_ago=3000,
            assigned_agent=agent,
            replies=(
                (SenderType.AGENT, agent, "Sorry about that. The missing item has been sent and will arrive in 3 days."),
                (SenderType.CUSTOMER, customers[3], "Thank you, I received it."),
            ),
        ),
        make_ticket(
            now, customers[4], first_order_of(customers[4]), "Product stopped working",
            "The product stopped working after two days.",
            TicketStatus.WAITING_FOR_CUSTOMER, TicketPriority.MEDIUM, minutes_ago=600,
            assigned_agent=agent,
            replies=(
                (SenderType.AGENT, agent, "Please upload a photo or video that shows the problem."),
            ),
        ),
    ]
    db.add_all(tickets)
    db.commit()

    print("Seed complete.")
    print(f"  users: {len(customers) + 2}  products: {len(products)}  orders: {len(orders)}  tickets: {len(tickets)}")
    print(f"  every seeded user has the password '{DEV_PASSWORD}'")
    print(f"  admin{SEED_EMAIL_SUFFIX}  agent{SEED_EMAIL_SUFFIX}  customer1{SEED_EMAIL_SUFFIX} ... customer5{SEED_EMAIL_SUFFIX}")


def main() -> None:
    if settings.environment != "development":
        sys.exit("Seeding is only allowed when ENVIRONMENT=development.")
    with SessionLocal() as db:
        if "--reset" in sys.argv:
            reset(db)
        seed(db)


if __name__ == "__main__":
    main()
