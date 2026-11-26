"""Notification service: create (fan-out on events), list, mark-read, settings."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.comment import Comment
from ..models.enums import NotificationType, PostNotify
from ..models.follow import Follow
from ..models.notification import Notification
from ..models.post import Post
from ..models.user import User
from ..schemas.notification import (
    NotificationOut,
    NotificationPage,
    NotificationSettings,
    NotificationSettingsUpdate,
)
from ..schemas.user import UserPublic

MAX_PAGE_SIZE = 50

# Notifications older than this are hidden from reads and periodically purged.
NOTIFICATION_RETENTION_DAYS = 30
_PURGE_EVERY_SECONDS = 3600.0
# In-process throttle for the global purge (matches the app's other in-process
# singletons like the rate limiter / WS manager). Idempotent if it double-runs.
# Starts far in the past so the first purge runs promptly (``time.monotonic()``
# can be small just after boot, which a 0.0 start would wrongly throttle).
_last_purge_monotonic = -1e9


def _retention_cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=NOTIFICATION_RETENTION_DAYS)


async def _maybe_purge(session: AsyncSession) -> None:
    """Delete notifications past the retention window, at most once per hour."""
    global _last_purge_monotonic
    now = time.monotonic()
    if now - _last_purge_monotonic < _PURGE_EVERY_SECONDS:
        return
    _last_purge_monotonic = now
    await session.execute(delete(Notification).where(Notification.created_at < _retention_cutoff()))
    await session.commit()


async def create_post_notifications(
    session: AsyncSession, *, post_id: int, author_id: int
) -> list[int]:
    """Notify everyone eligible for a new post: `notify_posts='all'`, plus the
    author's followers with `notify_posts='followed'` (never the author).
    Like the other ``create_*`` functions, returns the new notification ids."""
    followers = select(Follow.follower_id).where(Follow.followee_id == author_id)
    rows = await session.execute(
        select(User.id).where(
            User.id != author_id,
            or_(
                User.notify_posts == PostNotify.ALL,
                and_(User.notify_posts == PostNotify.FOLLOWED, User.id.in_(followers)),
            ),
        )
    )
    recipients = [rid for (rid,) in rows.all()]
    if not recipients:
        return []
    notifs = [
        Notification(
            recipient_id=rid, actor_id=author_id, type=NotificationType.POST, post_id=post_id
        )
        for rid in recipients
    ]
    session.add_all(notifs)
    await session.commit()
    return [n.id for n in notifs]


async def create_comment_notifications(
    session: AsyncSession, *, post_id: int, actor_id: int, parent_comment_id: int | None
) -> list[int]:
    """Notify the post author (comment) and, for a reply, the parent's author."""
    post = await session.get(Post, post_id)
    if post is None:
        return []
    notifs: list[Notification] = []
    if post.author_id != actor_id:
        author = await session.get(User, post.author_id)
        if author is not None and author.notify_comments:
            notifs.append(
                Notification(
                    recipient_id=post.author_id,
                    actor_id=actor_id,
                    type=NotificationType.COMMENT,
                    post_id=post_id,
                )
            )
    if parent_comment_id is not None:
        parent = await session.get(Comment, parent_comment_id)
        # Skip if the parent author is the actor or already notified (= post author).
        if parent is not None and parent.author_id not in (actor_id, post.author_id):
            pa = await session.get(User, parent.author_id)
            if pa is not None and pa.notify_comments:
                notifs.append(
                    Notification(
                        recipient_id=parent.author_id,
                        actor_id=actor_id,
                        type=NotificationType.REPLY,
                        post_id=post_id,
                    )
                )
    if notifs:
        session.add_all(notifs)
        await session.commit()
    return [n.id for n in notifs]


async def create_follow_notification(
    session: AsyncSession, *, followee: User, actor_id: int
) -> list[int]:
    if not followee.notify_follows:
        return []
    notif = Notification(
        recipient_id=followee.id, actor_id=actor_id, type=NotificationType.FOLLOW
    )
    session.add(notif)
    await session.commit()
    return [notif.id]


async def list_notifications(
    session: AsyncSession,
    *,
    user_id: int,
    cursor: int | None,
    limit: int,
    kinds: set[NotificationType] | None = None,
) -> NotificationPage:
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    await _maybe_purge(session)
    stmt = (
        select(Notification)
        .options(selectinload(Notification.actor))
        .where(
            Notification.recipient_id == user_id,
            Notification.created_at >= _retention_cutoff(),
        )
        .order_by(Notification.id.desc())
        .limit(limit + 1)
    )
    if kinds:
        stmt = stmt.where(Notification.type.in_(kinds))
    if cursor is not None:
        stmt = stmt.where(Notification.id < cursor)
    rows = (await session.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [
        NotificationOut(
            id=n.id,
            type=n.type.value,
            actor=UserPublic.model_validate(n.actor),
            post_id=n.post_id,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in rows
    ]
    next_cursor = items[-1].id if (has_more and items) else None
    unread = await unread_count(session, user_id)
    return NotificationPage(items=items, next_cursor=next_cursor, unread=unread)


async def unread_count(session: AsyncSession, user_id: int) -> int:
    count = await session.scalar(
        select(func.count(Notification.id)).where(
            Notification.recipient_id == user_id,
            Notification.is_read.is_(False),
            Notification.created_at >= _retention_cutoff(),
        )
    )
    return int(count or 0)


async def mark_all_read(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(Notification)
        .where(Notification.recipient_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await session.commit()


def settings_of(user: User) -> NotificationSettings:
    return NotificationSettings(
        notify_posts=user.notify_posts,
        notify_comments=user.notify_comments,
        notify_follows=user.notify_follows,
    )


async def update_settings(
    session: AsyncSession, *, user: User, data: NotificationSettingsUpdate
) -> NotificationSettings:
    fields = data.model_dump(exclude_unset=True)
    if "notify_posts" in fields and fields["notify_posts"] is not None:
        user.notify_posts = fields["notify_posts"]
    if "notify_comments" in fields and fields["notify_comments"] is not None:
        user.notify_comments = fields["notify_comments"]
    if "notify_follows" in fields and fields["notify_follows"] is not None:
        user.notify_follows = fields["notify_follows"]
    await session.commit()
    return settings_of(user)
