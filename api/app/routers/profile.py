"""Profile: the signed-in student's own profile and other students' profiles.

Identity + figures are read live from 42 (restricted to the 42 Roma campus);
in-app activity is computed from our DB.
"""

from __future__ import annotations

from fastapi import APIRouter, Path, Response, status
from fastapi.exceptions import HTTPException

from ..deps import CurrentUser, EventsProviderDep, SessionDep, SettingsDep
from ..intra import EventsUnavailableError
from ..models.user import User
from ..schemas.profile import ProfileOut
from ..services import profile as profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


async def _profile(session, settings, provider, viewer: User, login: str, response: Response):
    try:
        result = await profile_service.get_profile(
            session, settings=settings, provider=provider, viewer=viewer, login=login
        )
    except EventsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profilo 42 non disponibile proprio mo'. Riprova tra poco.",
        ) from exc
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
    return result


@router.get("", response_model=ProfileOut)
async def my_profile(
    session: SessionDep,
    user: CurrentUser,
    provider: EventsProviderDep,
    settings: SettingsDep,
    response: Response,
) -> ProfileOut:
    """The signed-in student's own profile."""
    return await _profile(session, settings, provider, user, user.login, response)


@router.get("/{login}", response_model=ProfileOut)
async def student_profile(
    session: SessionDep,
    user: CurrentUser,
    provider: EventsProviderDep,
    settings: SettingsDep,
    response: Response,
    login: str = Path(..., min_length=1, max_length=64),
) -> ProfileOut:
    """Another 42 Roma student's profile (404 if they aren't 42 Roma)."""
    return await _profile(session, settings, provider, user, login, response)
