"""Acting on 42 *on behalf of a student*, using their stored user token.

The 42 ``events_users`` write endpoints need a resource-owner (user) token, not
the app client-credentials token. We keep the student's token encrypted on the
``User`` row; this module decrypts it, refreshes it when expired (the OAuth
authorization-code refresh, which the API client does not do), and then performs
the sign-up/cancel through the vendored ``intra42`` client built from that
token (:meth:`AsyncClient.from_access_token`). The client pins every request to
the 42 host and maps HTTP errors to typed exceptions, which we translate to the
two domain errors below.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from intra42 import AsyncClient
from intra42.exceptions import (
    AuthenticationError,
    FortyTwoAPIError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from . import crypto
from .config import Settings
from .models.user import User

logger = logging.getLogger("app.intra_user")

TOKEN_URL = "https://api.intra.42.fr/oauth/token"
_REFRESH_LEEWAY = timedelta(seconds=60)
_HTTP_TIMEOUT = 10.0


class IntraAuthRequired(Exception):
    """The student has no usable 42 token — they must (re)log in with 42."""


class IntraApiError(Exception):
    """42 rejected the request for a non-auth reason (e.g. event full)."""


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str | None
    expires_in: int


def apply_tokens(user: User, bundle: TokenBundle) -> None:
    """Encrypt and store a fresh token bundle on the user (no commit)."""
    user.intra_access_token_enc = crypto.encrypt(bundle.access_token)
    user.intra_refresh_token_enc = (
        crypto.encrypt(bundle.refresh_token) if bundle.refresh_token else None
    )
    user.intra_token_expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=max(0, bundle.expires_in)
    )


def _needs_refresh(user: User) -> bool:
    if user.intra_token_expires_at is None:
        return True
    expires = user.intra_token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= expires - _REFRESH_LEEWAY


async def _refresh(session: AsyncSession, settings: Settings, user: User) -> str:
    enc = user.intra_refresh_token_enc
    refresh_token = crypto.decrypt(enc) if enc else None
    if not refresh_token:
        raise IntraAuthRequired("No refresh token on file")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.forty_two_uid,
        "client_secret": settings.forty_two_secret,
    }
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        logger.warning("42 token refresh failed (status %s)", resp.status_code)
        raise IntraAuthRequired("Token refresh rejected")
    payload = resp.json()
    access = payload.get("access_token")
    if not isinstance(access, str) or not access:
        raise IntraAuthRequired("Refresh response missing access_token")
    apply_tokens(
        user,
        TokenBundle(
            access_token=access,
            refresh_token=payload.get("refresh_token") or refresh_token,
            expires_in=int(payload.get("expires_in", 7200)),
        ),
    )
    await session.commit()
    return access


async def _valid_access_token(session: AsyncSession, settings: Settings, user: User) -> str:
    if _needs_refresh(user):
        return await _refresh(session, settings, user)
    enc = user.intra_access_token_enc
    token = crypto.decrypt(enc) if enc else None
    if not token:
        raise IntraAuthRequired("No access token on file")
    return token


async def subscribe_to_event(
    session: AsyncSession, settings: Settings, user: User, event_id: int
) -> int:
    """Register the student to a 42 event; return the 42 events_user id."""
    token = await _valid_access_token(session, settings, user)
    async with AsyncClient.from_access_token(token, timeout=_HTTP_TIMEOUT) as client:
        try:
            registration = await client.events_users.subscribe(
                event_id=event_id, user_id=user.intra_id
            )
            return int(registration.id)
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise IntraAuthRequired("42 rejected the token (scope or expiry)") from exc
        except ValidationError as exc:
            # 422 is usually "already registered" — recover the existing id.
            existing = await _find_registration(client, event_id, user.intra_id)
            if existing is not None:
                return existing
            raise IntraApiError(
                "Iscrizione rifiutata da 42 (evento pieno o già iscritto)"
            ) from exc
        except FortyTwoAPIError as exc:
            logger.warning("42 events_users subscribe failed: %s", exc)
            raise IntraApiError("42 non ha accettato l'iscrizione") from exc


async def unsubscribe_from_event(
    session: AsyncSession, settings: Settings, user: User, events_user_id: int
) -> None:
    """Cancel a 42 registration by its events_user id."""
    token = await _valid_access_token(session, settings, user)
    async with AsyncClient.from_access_token(token, timeout=_HTTP_TIMEOUT) as client:
        try:
            await client.events_users.unsubscribe(events_user_id)
        except NotFoundError:
            return  # Already gone on 42 — treat as success.
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise IntraAuthRequired("42 rejected the token (scope or expiry)") from exc
        except FortyTwoAPIError as exc:
            logger.warning("42 events_users unsubscribe failed: %s", exc)
            raise IntraApiError("42 non ha accettato la cancellazione") from exc


async def _find_registration(
    client: AsyncClient, event_id: int, user_intra_id: int
) -> int | None:
    """Look up an existing registration id via the user-token client."""
    try:
        rows = await client.events_users.filter(
            event_id=event_id, user_id=user_intra_id
        ).all()
    except FortyTwoAPIError:
        return None
    return int(rows[0].id) if rows else None
