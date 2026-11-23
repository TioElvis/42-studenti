"""Student search: find app students by login or display name.

Covers students who've used the app (all 42 Roma). To reach a 42 Roma student
who isn't in the app yet, the frontend jumps to their exact login via the
42-driven profile.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..schemas.user import UserPublic

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
