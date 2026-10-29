from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.cookies import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SAFE_METHODS,
    csrf_matches,
)
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services import user_service

# auto_error=False so that we send our own 401 (the same in every FastAPI version)
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Who is calling? Read the token (header first, then cookie) and load the user fresh."""
    token: str | None = credentials.credentials if credentials else None
    used_cookie = False
    if token is None:
        token = request.cookies.get(ACCESS_COOKIE_NAME)
        used_cookie = token is not None
    if token is None:
        raise _unauthorized()

    # A browser sends cookies by itself, so a cookie login needs CSRF protection on writes.
    # A Bearer header is never added by the browser on its own, so it needs no CSRF check.
    if used_cookie and request.method not in SAFE_METHODS:
        if not csrf_matches(
            request.cookies.get(CSRF_COOKIE_NAME),
            request.headers.get(CSRF_HEADER_NAME),
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing or invalid",
            )

    try:
        user_id = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid or expired token") from None

    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise _unauthorized("Invalid or expired token")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


def require_role(*allowed: UserRole) -> Callable[..., User]:
    """Use as: Depends(require_role(UserRole.AGENT, UserRole.ADMIN))."""
    allowed_values = {role.value for role in allowed}

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return checker
