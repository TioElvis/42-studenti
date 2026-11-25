"""Student search endpoint (autocomplete over app students)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response

from ..deps import CurrentUser, SessionDep, SettingsDep
from ..schemas.user import StudentPage, UserPublic
from ..services import students as students_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=list[UserPublic])
async def search_students(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
    q: str = Query("", max_length=64),
    limit: int = Query(20, ge=1, le=50),
) -> list[UserPublic]:
    """Find app students by login or display name (min 2 chars; else empty)."""
    results = await students_service.search(session, q=q, limit=limit)
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
    return results


@router.get("/page", response_model=StudentPage)
async def students_page(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
    q: str = Query("", max_length=64),
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(20, ge=1, le=50),
) -> StudentPage:
    """Paginated directory of app students; ``q`` (2+ chars) filters it."""
    result = await students_service.list_page(session, q=q, page=page, page_size=page_size)
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
    return result
