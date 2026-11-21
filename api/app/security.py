"""Session JWT issuing/verification and auth-cookie helpers.

This is OUR signed session token, never the 42 access token (which never
leaves the backend). The algorithm is pinned on both sign and verify so a
token can't downgrade to ``alg: none`` or an unexpected algorithm.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Response
from jose import JWTError, jwt

from .config import Settings


class TokenError(Exception):
    """Raised when a session token is missing, malformed or expired."""


def create_access_token(settings: Settings, *, user_id: int, login: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "login": login,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
        "iss": "42-roma-studenti",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> int:
    """Return the user id from a valid token, else raise ``TokenError``."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer="42-roma-studenti",
            options={"require": ["exp", "sub", "iss"]},
        )
    except JWTError as exc:
        raise TokenError("Invalid or expired session token") from exc
    sub = payload.get("sub")
    if not sub or not str(sub).isdigit():
        raise TokenError("Token subject is missing or malformed")
    return int(sub)


def set_auth_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        domain=settings.cookie_domain,
        path="/",
    )


def clear_auth_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        domain=settings.cookie_domain,
        path="/",
    )
