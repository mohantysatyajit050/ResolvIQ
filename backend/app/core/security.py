import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# recommended() = Argon2, with safe default settings
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Turn a plain password into a salted Argon2 hash."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a typed password against a stored hash."""
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID, expires_delta: timedelta | None = None) -> str:
    """Make a signed token that holds only: who (sub), made at (iat), ends at (exp)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": str(user_id), "iat": now, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id inside a valid token.

    Raises jwt.InvalidTokenError if the token is bad, tampered with, or expired.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],  # never trust the algorithm named in the token
        options={"require": ["exp", "iat", "sub"]},
    )
    try:
        return uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise jwt.InvalidTokenError("bad subject") from None
