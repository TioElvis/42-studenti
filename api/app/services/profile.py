"""Profile service: identity + figures read live from 42; in-app activity from
our DB.

Access is restricted to the 42 Roma campus: the 42 profile is fetched first and
rejected (404) if the student isn't on our campus — so we never reveal profiles
outside 42 Roma, and nothing about the profile is stored.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..intra import EventsProvider, IntraUserNotFound
from ..models.comment import Comment
from ..models.like import PostLike
from ..models.post import Post
from ..models.rsvp import PostRSVP
from ..models.user import User
from ..schemas.profile import ActivityStats, Intra42Info, ProfileOut, ProjectInfo
from . import follows as follows_service
from .exceptions import NotFoundError


async def get_profile(
    session: AsyncSession,
    *,
    settings: Settings,
    provider: EventsProvider,
    viewer: User,
    login: str,
) -> ProfileOut:
    try:
        info = await provider.user_profile(login)
    except IntraUserNotFound as exc:
        raise NotFoundError("Studente non trovato") from exc
    # (EventsUnavailableError propagates → the router maps it to 503.)

    # 42 Roma only — treat a non-campus student as "not found" (don't disclose).
    if settings.forty_two_campus_id not in info.campus_ids:
        raise NotFoundError("Studente non trovato")

    # In-app activity / social are only known for students who've used the app.
    local = (
        await session.execute(select(User).where(User.login == info.login))
    ).scalar_one_or_none()
    is_me = info.login == viewer.login
    if local is not None:
        activity = await _activity(session, user_id=local.id, logins=local.login_count)
        followers, following, is_following = await follows_service.stats(
            session, user_id=local.id, viewer_id=viewer.id
        )
    else:
        activity = ActivityStats(posts=0, comments=0, daje_received=0, rsvps=0, logins=0)
        followers, following, is_following = 0, 0, False

    return ProfileOut(
        login=info.login,
        display_name=info.display_name,
        avatar_url=info.avatar_url,
        campus=info.campus,
        is_me=is_me,
        activity=activity,
        followers=followers,
        following=following,
        is_following=is_following,
        followable=local is not None and not is_me,
        intra=Intra42Info(
            level=info.level,
            grade=info.grade,
            correction_point=info.correction_point,
            wallet=info.wallet,
            location=info.location,
            pool=info.pool,
            joined=info.joined,
            projects=[
                ProjectInfo(name=p.name, status=p.status, mark=p.mark, validated=p.validated)
                for p in info.projects
            ],
            achievements=list(info.achievements),
        ),
    )


async def _activity(session: AsyncSession, *, user_id: int, logins: int) -> ActivityStats:
    posts = await session.scalar(select(func.count(Post.id)).where(Post.author_id == user_id))
    comments = await session.scalar(
        select(func.count(Comment.id)).where(Comment.author_id == user_id)
    )
    daje = await session.scalar(
        select(func.count(PostLike.id))
        .join(Post, Post.id == PostLike.post_id)
        .where(Post.author_id == user_id)
    )
    rsvps = await session.scalar(
        select(func.count(PostRSVP.id)).where(PostRSVP.user_id == user_id)
    )
    return ActivityStats(
        posts=int(posts or 0),
        comments=int(comments or 0),
        daje_received=int(daje or 0),
        rsvps=int(rsvps or 0),
        logins=int(logins or 0),
    )
