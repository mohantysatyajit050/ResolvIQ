from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest


class EmailAlreadyRegisteredError(Exception):
    """Raised when someone registers with an email that already exists."""


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_customer(db: Session, data: RegisterRequest) -> User:
    """Create a new customer. The role is set here, never taken from the request."""
    if get_user_by_email(db, data.email):
        raise EmailAlreadyRegisteredError

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        phone=data.phone,
        role=UserRole.CUSTOMER.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # two people registered the same email at the same moment
        db.rollback()
        raise EmailAlreadyRegisteredError from None
    db.refresh(user)
    return user
