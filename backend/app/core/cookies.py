import hmac
import secrets

from fastapi import Response

from app.core.config import settings

# Cookies are shared across ports on localhost, so these names are specific to ResolvIQ.
ACCESS_COOKIE_NAME = "resolviq_session"
CSRF_COOKIE_NAME = "resolviq_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Browsers can send these without the user doing anything on our site, so they never change data.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_matches(cookie_value: str | None, header_value: str | None) -> bool:
    """Compare in constant time, so the check cannot leak anything through timing."""
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value.encode(), header_value.encode())


def set_session_cookies(response: Response, access_token: str) -> None:
    max_age = settings.access_token_expire_minutes * 60
    # The session cookie: JavaScript can never read it (httponly).
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    # The CSRF cookie: the page must read it and send it back as a header, so not httponly.
    response.set_cookie(
        CSRF_COOKIE_NAME,
        new_csrf_token(),
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    for name, httponly in ((ACCESS_COOKIE_NAME, True), (CSRF_COOKIE_NAME, False)):
        response.delete_cookie(
            name,
            path="/",
            secure=settings.cookie_secure,
            httponly=httponly,
            samesite=settings.cookie_samesite,
        )
