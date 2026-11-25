"""Student search: find app students by login or display name.

Covers students who've used the app (all 42 Roma). To reach a 42 Roma student
who isn't in the app yet, the frontend jumps to their exact login via the
42-driven profile.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.follow import Follow
from ..models.like import PostLike
from ..models.post import Post
from ..models.user import User
from ..schemas.stats import StatRow
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


TOP_N = 10


def _row(u: User, value: int) -> StatRow:
    return StatRow(
        login=u.login, display_name=u.display_name, avatar_url=u.avatar_url, value=int(value)
    )


async def top_followers(session: AsyncSession, *, limit: int = TOP_N) -> list[StatRow]:
    """Students with the most followers (ties: login)."""
    n = func.count(Follow.id)
    rows = await session.execute(
        select(User, n)
        .join(Follow, Follow.followee_id == User.id)
        .group_by(User.id)
        .order_by(n.desc(), User.login)
        .limit(limit)
    )
    return [_row(u, c) for u, c in rows.all()]


async def top_daje(session: AsyncSession, *, limit: int = TOP_N) -> list[StatRow]:
    """Students with the most "Daje!" received on their posts. A student's own
    likes on their own posts don't count (ties: login)."""
    n = func.count(PostLike.id)
    rows = await session.execute(
        select(User, n)
        .join(Post, Post.author_id == User.id)
        .join(PostLike, PostLike.post_id == Post.id)
        .where(PostLike.user_id != Post.author_id)
        .group_by(User.id)
        .order_by(n.desc(), User.login)
        .limit(limit)
    )
    return [_row(u, c) for u, c in rows.all()]


async def recent_students(session: AsyncSession, *, limit: int) -> list[User]:
    """The students the 42 snapshot is built for: most recently active first."""
    rows = await session.execute(
        select(User).order_by(User.last_login_at.desc().nulls_last(), User.id).limit(limit)
    )
    return list(rows.scalars().all())


def rank_from_snapshot(
    values: dict[str, int], by_login: dict[str, User], *, limit: int = TOP_N
) -> list[StatRow]:
    """Top ``limit`` positive values among students we know (ties: login)."""
    ranked = sorted(
        ((lg, v) for lg, v in values.items() if v > 0 and lg in by_login),
        key=lambda kv: (-kv[1], kv[0]),
    )[:limit]
    return [_row(by_login[lg], v) for lg, v in ranked]
