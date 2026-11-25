"""Student search: find app students by login or display name.

Covers students who've used the app (all 42 Roma). To reach a 42 Roma student
who isn't in the app yet, the frontend jumps to their exact login via the
42-driven profile.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..schemas.user import StudentPage, UserPublic

MIN_QUERY = 2


async def search(session: AsyncSession, *, q: str, limit: int) -> list[UserPublic]:
    q = q.strip()
    if len(q) < MIN_QUERY:
        return []
    # Escape LIKE wildcards in user input so they match literally.
    esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{esc}%"
    rows = await session.execute(
        select(User)
        .where(
            or_(
                User.login.ilike(pattern, escape="\\"),
                User.display_name.ilike(pattern, escape="\\"),
            )
        )
        .order_by(User.login)
        .limit(limit)
    )
    return [UserPublic.model_validate(u) for u in rows.scalars().all()]


def _like_filter(q: str):
    """LIKE filter for a 2+ char query (wildcards escaped), else ``None``."""
    q = q.strip()
    if len(q) < MIN_QUERY:
        return None
    esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{esc}%"
    return or_(
        User.login.ilike(pattern, escape="\\"),
        User.display_name.ilike(pattern, escape="\\"),
    )


async def list_page(
    session: AsyncSession, *, q: str = "", page: int = 1, page_size: int = 20
) -> StudentPage:
    """The students directory, ordered by login, one page at a time.

    A query shorter than ``MIN_QUERY`` is ignored (lists everyone). ``page`` is
    1-based and clamped to the last page, so a stale page number never 404s.
    """
    where = _like_filter(q)
    count_stmt = select(func.count(User.id))
    if where is not None:
        count_stmt = count_stmt.where(where)
    total = int(await session.scalar(count_stmt) or 0)
    pages = max(1, -(-total // page_size))
    page = min(max(1, page), pages)

    stmt = select(User).order_by(User.login).offset((page - 1) * page_size).limit(page_size)
    if where is not None:
        stmt = stmt.where(where)
    rows = await session.execute(stmt)
    return StudentPage(
        items=[UserPublic.model_validate(u) for u in rows.scalars().all()],
        total=total,
        page=page,
        pages=pages,
    )
