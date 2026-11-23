"""Student search endpoint (autocomplete over app students)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response

from ..deps import CurrentUser, SessionDep, SettingsDep
from ..schemas.user import UserPublic
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
