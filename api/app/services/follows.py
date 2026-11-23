"""Follow service: directed follow edges between students (follow/unfollow +
counts). Only app students can be followed."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.follow import Follow
from ..models.user import User
from .exceptions import ConflictError, NotFoundError


async def _user_by_login(session: AsyncSession, login: str) -> User:
    user = (
        await session.execute(select(User).where(User.login == login))
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundError("Studente non trovato")
    return user


async def follow(session: AsyncSession, *, follower: User, login: str) -> tuple[User, bool]:
    """Follow ``login``. Returns (target, created) — created is False if already
    following (idempotent). Can't follow yourself."""
    target = await _user_by_login(session, login)
    if target.id == follower.id:
        raise ConflictError("Nun te poi seguì da solo.")
    exists = await session.scalar(
        select(func.count(Follow.id)).where(
            Follow.follower_id == follower.id, Follow.followee_id == target.id
        )
    )
    if exists:
        return target, False
    session.add(Follow(follower_id=follower.id, followee_id=target.id))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()  # raced with a concurrent follow
        return target, False
    return target, True


async def unfollow(session: AsyncSession, *, follower: User, login: str) -> None:
    target = await _user_by_login(session, login)
    existing = (
        await session.execute(
            select(Follow).where(
                Follow.follower_id == follower.id, Follow.followee_id == target.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        await session.delete(existing)
        await session.commit()


async def stats(session: AsyncSession, *, user_id: int, viewer_id: int) -> tuple[int, int, bool]:
    """(followers, following, viewer_is_following)."""
    followers = await session.scalar(
        select(func.count(Follow.id)).where(Follow.followee_id == user_id)
    )
    following = await session.scalar(
        select(func.count(Follow.id)).where(Follow.follower_id == user_id)
    )
    is_following = await session.scalar(
        select(func.count(Follow.id)).where(
            Follow.follower_id == viewer_id, Follow.followee_id == user_id
        )
    )
    return int(followers or 0), int(following or 0), bool(is_following)
