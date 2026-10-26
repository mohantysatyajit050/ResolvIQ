from app.core.security import create_access_token
from app.models import (
    Address,
    Order,
    OrderItem,
    Product,
    Ticket,
    TicketMessage,
    TicketStatus,
    User,
)


def auth_header(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def make_address(db, user, pincode="411001") -> Address:
    address = Address(
        user_id=user.id,
        address_line="12, Station Road",
        city="Pune",
        state="Maharashtra",
        pincode=pincode,
    )
    db.add(address)
    db.commit()
    return address


def make_product(db, name="Test Phone", price_paise=1_500_000) -> Product:
    product = Product(name=name, category="Phones", price_paise=price_paise)
    db.add(product)
    db.commit()
    return product


def make_order(db, user, quantity=1, status="placed") -> Order:
    address = make_address(db, user)
    product = make_product(db)
    order = Order(
        user_id=user.id,
        shipping_address_id=address.id,
        status=status,
        total_paise=quantity * product.price_paise,
        items=[
            OrderItem(
                product_id=product.id,
                quantity=quantity,
                unit_price_paise=product.price_paise,
            )
        ],
    )
    db.add(order)
    db.commit()
    return order


def make_ticket(
    db,
    user,
    order,
    status=TicketStatus.OPEN,
    subject="Where is my order?",
    description="It is late.",
) -> Ticket:
    ticket = Ticket(
        user_id=user.id,
        order_id=order.id,
        subject=subject,
        description=description,
        status=status.value,
        messages=[
            TicketMessage(sender_id=user.id, sender_type="customer", body=description)
        ],
    )
    db.add(ticket)
    db.commit()
    return ticket
