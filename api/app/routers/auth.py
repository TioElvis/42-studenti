"""42 OAuth2 (Authorization Code) login, handled entirely server-side.

Flow:
    GET /auth/42           -> redirect to 42's authorize page (with CSRF state)
    GET /auth/42/callback  -> exchange code, fetch /me, upsert user, set cookie
    POST /auth/logout      -> clear the session cookie

The 42 access token never leaves this backend: we use it once to read /me and
then issue OUR OWN signed JWT in an httpOnly cookie. Outbound calls go only to
the fixed 42 hosts below (no user-controlled URLs -> no SSRF).
"""

from __future__ import annotations

import hmac
import logging
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse

from .. import intra_user
from ..deps import SessionDep, SettingsDep
from ..intra_user import TokenBundle
from ..ratelimit import auth_rate_limiter
from ..security import clear_auth_cookie, create_access_token, set_auth_cookie
from ..services import users as users_service
from ..services.users import IntraProfile

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

AUTHORIZE_URL = "https://api.intra.42.fr/oauth/authorize"
TOKEN_URL = "https://api.intra.42.fr/oauth/token"
ME_URL = "https://api.intra.42.fr/v2/me"
STATE_COOKIE = "oauth_state"


@router.get("/42", dependencies=[Depends(auth_rate_limiter)])
async def login_with_42(settings: SettingsDep) -> RedirectResponse:
    """Kick off the 42 OAuth flow."""
    if not settings.forty_two_uid:
        # Misconfiguration, not a client error we want to detail.
        return _redirect_with_error(settings, "config")

    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.forty_two_uid,
        "redirect_uri": settings.forty_two_callback_url,
        "response_type": "code",
        "scope": settings.oauth_scope,
        "state": state,
    }
    response = RedirectResponse(
        url=f"{AUTHORIZE_URL}?{urlencode(params)}", status_code=status.HTTP_302_FOUND
    )
    # Short-lived, httpOnly state cookie for CSRF protection on the callback.
    response.set_cookie(
        key=STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/auth",
    )
    return response


@router.get("/42/callback", dependencies=[Depends(auth_rate_limiter)])
async def callback(
    request: Request,
    settings: SettingsDep,
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Handle 42's redirect back: validate, exchange, upsert, set cookie."""
    if error or not code or not state:
        return _redirect_with_error(settings, "denied")

    expected_state = request.cookies.get(STATE_COOKIE)
    if not expected_state or not hmac.compare_digest(expected_state, state):
        return _redirect_with_error(settings, "state")

    try:
        bundle = await _exchange_code(settings, code)
        profile = await _fetch_profile(bundle.access_token)
    except AuthFlowError:
        logger.warning("42 OAuth callback failed during token/profile exchange")
        return _redirect_with_error(settings, "oauth")

    # Access is restricted to students of our campus (42 Roma). Deny by default:
    # if the campus can't be confirmed from /me, the login is refused.
    if settings.forty_two_campus_id not in profile.campus_ids:
        logger.info("Login refused: user %s is not on campus %s", profile.login,
                    settings.forty_two_campus_id)
        return _redirect_with_error(settings, "campus")

    user = await users_service.upsert_from_intra(session, profile)
    # Keep the 42 user token (encrypted) so we can act on 42 on their behalf.
    intra_user.apply_tokens(user, bundle)
    await session.commit()
    jwt_token = create_access_token(settings, user_id=user.id, login=user.login)

    response = RedirectResponse(url=settings.frontend_url, status_code=status.HTTP_302_FOUND)
    set_auth_cookie(response, settings, jwt_token)
    response.delete_cookie(STATE_COOKIE, path="/auth")
    return response


@router.post("/logout", dependencies=[Depends(auth_rate_limiter)])
async def logout(response: Response, settings: SettingsDep) -> dict[str, str]:
    clear_auth_cookie(response, settings)
    return {"detail": "A presto, regà!"}


# --- internals ---------------------------------------------------------------


class AuthFlowError(Exception):
    """Internal: a step of the OAuth exchange failed."""


def _redirect_with_error(settings, reason: str) -> RedirectResponse:
    # Generic, non-leaky signal the login page can turn into romanesco copy.
    return RedirectResponse(
        url=f"{settings.frontend_url}/?auth_error={reason}",
        status_code=status.HTTP_302_FOUND,
    )


async def _exchange_code(settings, code: str) -> TokenBundle:
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.forty_two_uid,
        "client_secret": settings.forty_two_secret,
        "code": code,
        "redirect_uri": settings.forty_two_callback_url,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(TOKEN_URL, data=data)
    if resp.status_code != 200:
        raise AuthFlowError("token exchange rejected")
    payload = resp.json()
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise AuthFlowError("token response missing access_token")
    return TokenBundle(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        expires_in=int(payload.get("expires_in", 7200)),
    )


async def _fetch_profile(token: str) -> IntraProfile:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        raise AuthFlowError("profile fetch rejected")
    return _parse_me(resp.json())


def _parse_me(data: dict) -> IntraProfile:
    intra_id = data.get("id")
    login = data.get("login")
    if not isinstance(intra_id, int) or not isinstance(login, str):
        raise AuthFlowError("unexpected /me payload")
    return IntraProfile(
        intra_id=intra_id,
        login=login,
        email=data.get("email"),
        display_name=data.get("displayname") or data.get("usual_full_name"),
        avatar_url=_extract_avatar(data),
        campus=_extract_campus(data),
        campus_ids=_extract_campus_ids(data),
    )


def _extract_campus_ids(data: dict) -> frozenset[int]:
    """All campus ids the user belongs to (from ``campus`` and ``campus_users``)."""
    ids: set[int] = set()
    for c in data.get("campus", []) or []:
        if isinstance(c, dict) and isinstance(c.get("id"), int):
            ids.add(c["id"])
    for cu in data.get("campus_users", []) or []:
        if isinstance(cu, dict) and isinstance(cu.get("campus_id"), int):
            ids.add(cu["campus_id"])
    return frozenset(ids)


def _extract_avatar(data: dict) -> str | None:
    image = data.get("image")
    if isinstance(image, dict):
        link = image.get("link")
        if isinstance(link, str):
            return link
        versions = image.get("versions")
        if isinstance(versions, dict):
            for key in ("medium", "small", "large", "micro"):
                if isinstance(versions.get(key), str):
                    return versions[key]
    if isinstance(data.get("image_url"), str):
        return data["image_url"]
    return None


def _extract_campus(data: dict) -> str | None:
    campuses = data.get("campus")
    if not isinstance(campuses, list) or not campuses:
        return None
    primary_id = None
    for cu in data.get("campus_users", []) or []:
        if isinstance(cu, dict) and cu.get("is_primary"):
            primary_id = cu.get("campus_id")
            break
    if primary_id is not None:
        for c in campuses:
            if isinstance(c, dict) and c.get("id") == primary_id:
                return c.get("name")
    first = campuses[0]
    return first.get("name") if isinstance(first, dict) else None
