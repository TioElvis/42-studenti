"""User service: upsert the local student record from a 42 profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User


@dataclass(frozen=True)
class IntraProfile:
    """The subset of the 42 ``/me`` payload we persist (plus the campus ids used
    once at login to gate access — not stored)."""

    intra_id: int
    login: str
    email: str | None
    display_name: str | None
    avatar_url: str | None
    campus: str | None
    campus_ids: frozenset[int] = frozenset()


async def upsert_from_intra(session: AsyncSession, profile: IntraProfile) -> User:
    """Create or update the local user keyed by their stable 42 ``intra_id``."""
    result = await session.execute(select(User).where(User.intra_id == profile.intra_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(intra_id=profile.intra_id, login=profile.login)
        session.add(user)

    # Refresh mutable profile fields on every login.
    user.login = profile.login
    user.email = profile.email
    user.display_name = profile.display_name
    user.avatar_url = profile.avatar_url
    user.campus = profile.campus

    # Track login activity (42 exposes no login counter, so we keep our own).
    user.login_count = (user.login_count or 0) + 1
    user.last_login_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(user)
    return user


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)
