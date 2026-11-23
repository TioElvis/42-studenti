"""Notification service: create (fan-out on events), list, mark-read, settings."""

from __future__ import annotations

from sqlalchemy import and_, func, or_, select, update
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


async def create_post_notifications(
    session: AsyncSession, *, post_id: int, author_id: int
) -> None:
    """Notify everyone eligible for a new post: `notify_posts='all'`, plus the
    author's followers with `notify_posts='followed'` (never the author)."""
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
        return
    session.add_all(
        [
            Notification(
                recipient_id=rid, actor_id=author_id, type=NotificationType.POST, post_id=post_id
            )
            for rid in recipients
        ]
    )
    await session.commit()


async def create_comment_notifications(
    session: AsyncSession, *, post_id: int, actor_id: int, parent_comment_id: int | None
) -> None:
    """Notify the post author (comment) and, for a reply, the parent's author."""
    post = await session.get(Post, post_id)
    if post is None:
        return
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


async def create_follow_notification(
    session: AsyncSession, *, followee: User, actor_id: int
) -> None:
    if not followee.notify_follows:
        return
    session.add(
        Notification(recipient_id=followee.id, actor_id=actor_id, type=NotificationType.FOLLOW)
    )
    await session.commit()


async def list_notifications(
    session: AsyncSession, *, user_id: int, cursor: int | None, limit: int
) -> NotificationPage:
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    stmt = (
        select(Notification)
        .options(selectinload(Notification.actor))
        .where(Notification.recipient_id == user_id)
        .order_by(Notification.id.desc())
        .limit(limit + 1)
    )
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
            Notification.recipient_id == user_id, Notification.is_read.is_(False)
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
