"""FastAPI dependencies: settings, auth gate, and the events provider."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.exceptions import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .database import get_session
from .intra import EventsProvider
from .models.user import User
from .security import TokenError, decode_access_token
from .services import users as users_service

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]

_NOT_AUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Non sei autenticato. Accedi con 42 pe' entrà in cluster.",
)


async def get_current_user(
    request: Request, settings: SettingsDep, session: SessionDep
) -> User:
    """Resolve the authenticated student from the signed session cookie.

    Deny-by-default: any missing/invalid token or unknown user is a 401.
    """
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise _NOT_AUTHENTICATED
    try:
        user_id = decode_access_token(settings, token)
    except TokenError as exc:
        raise _NOT_AUTHENTICATED from exc
    user = await users_service.get_by_id(session, user_id)
    if user is None:
        raise _NOT_AUTHENTICATED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# --- Events provider singleton (one in-process cache for the whole app) ---
_events_provider: EventsProvider | None = None


def get_events_provider(settings: SettingsDep) -> EventsProvider:
    global _events_provider
    if _events_provider is None:
        _events_provider = EventsProvider(settings)
    return _events_provider


EventsProviderDep = Annotated[EventsProvider, Depends(get_events_provider)]
