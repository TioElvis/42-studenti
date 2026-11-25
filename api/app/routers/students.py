"""Student search endpoint (autocomplete over app students)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Response

from ..deps import CurrentUser, IntraStatsDep, SessionDep, SettingsDep
from ..intra_stats import CLUSTER_DAYS
from ..schemas.stats import StatsOut
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


@router.get("/stats", response_model=StatsOut)
async def students_stats(
    user: CurrentUser,
    session: SessionDep,
    settings: SettingsDep,
    intra_stats: IntraStatsDep,
    response: Response,
) -> StatsOut:
    """Leaderboards: followers + Daje (live, our DB) and wallet + cluster time
    (42 snapshot, refreshed in the background — never fetched per request)."""
    students = await students_service.recent_students(session, limit=settings.stats_max_users)
    by_login = {u.login: u for u in students}
    snap = intra_stats.get(list(by_login))  # may kick off a background refresh
    out = StatsOut(
        followers=await students_service.top_followers(session),
        daje=await students_service.top_daje(session),
        intra_ready=snap is not None,
        intra_updated_at=snap.updated_at if snap else None,
        cluster_days=CLUSTER_DAYS,
    )
    if snap is not None:
        out.wallet = students_service.rank_from_snapshot(snap.wallet, by_login)
        out.cluster = students_service.rank_from_snapshot(snap.cluster, by_login)
    # Short private cache: the live rankings shouldn't be stale for long.
    response.headers["Cache-Control"] = "private, max-age=30"
    return out
