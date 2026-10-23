import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest

# Checked when the email does not exist, so "unknown email" and "wrong password"
# take about the same time and an attacker cannot tell them apart.
_DUMMY_HASH = hash_password("not-a-real-password")


class EmailAlreadyRegisteredError(Exception):
    """Raised when someone registers with an email that already exists."""


class InvalidCredentialsError(Exception):
    """Wrong email or wrong password (we never say which)."""


class AccountDisabledError(Exception):
    """The password was right, but the account is switched off."""


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


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


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Return the user if email and password are right, otherwise raise."""
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)  # spend the same time as a real check
        raise InvalidCredentialsError
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise AccountDisabledError
    return user
