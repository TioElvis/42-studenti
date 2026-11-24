"""Notifications: follow, new-post (followed/all), comment/reply, read, settings."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.database import get_sessionmaker
from app.models.enums import NotificationType, PostCategory, PostNotify
from app.models.notification import Notification
from app.models.user import User
from app.schemas.comment import CommentCreate
from app.schemas.notification import NotificationSettingsUpdate
from app.schemas.post import PostCreate
from app.services import follows as follows_svc
from app.services import notifications as notif_svc
from app.services import posts as posts_svc


async def _post(session, author, text):
    return await posts_svc.create_post(
        session, author=author, data=PostCreate(content=text, category=PostCategory.OFF_TOPIC)
    )


async def test_follow_creates_notification(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        target, _ = await follows_svc.follow(s, follower=alice, login="bob")
        await notif_svc.create_follow_notification(s, followee=target, actor_id=alice.id)
    async with maker() as s:
        assert await notif_svc.unread_count(s, bob.id) == 1
        page = await notif_svc.list_notifications(s, user_id=bob.id, cursor=None, limit=20)
        assert page.items[0].type == "follow" and page.items[0].actor.login == "alice"
        assert page.unread == 1


async def test_post_notifies_followers_and_all_not_author(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        carol = User(intra_id=1003, login="carol", notify_posts=PostNotify.ALL)
        s.add(carol)
        await s.commit()
        carol_id = carol.id
    async with maker() as s:
        await follows_svc.follow(s, follower=alice, login="bob")  # alice (FOLLOWED) follows bob
    async with maker() as s:
        post = await _post(s, bob, "ciao")
        await notif_svc.create_post_notifications(s, post_id=post.id, author_id=bob.id)
    async with maker() as s:
        assert await notif_svc.unread_count(s, alice.id) == 1  # follower w/ FOLLOWED
        assert await notif_svc.unread_count(s, carol_id) == 1  # ALL, no follow needed
        assert await notif_svc.unread_count(s, bob.id) == 0  # never the author


async def test_comment_and_reply_notifications(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        carol = User(intra_id=1004, login="carol2")
        s.add(carol)
        await s.commit()
        carol_id = carol.id
    async with maker() as s:
        post = await _post(s, alice, "post di alice")
        post_id = post.id
    async with maker() as s:
        bob_c = await posts_svc.add_comment(
            s, post_id=post_id, author=bob, data=CommentCreate(content="commento")
        )
        bob_comment_id = bob_c.id
        await notif_svc.create_comment_notifications(
            s, post_id=post_id, actor_id=bob.id, parent_comment_id=None
        )
    async with maker() as s:
        assert await notif_svc.unread_count(s, alice.id) == 1  # comment on her post
    async with maker() as s:
        carol = await s.get(User, carol_id)
        await posts_svc.add_comment(
            s, post_id=post_id, author=carol,
            data=CommentCreate(content="risposta", parent_id=bob_comment_id),
        )
        await notif_svc.create_comment_notifications(
            s, post_id=post_id, actor_id=carol_id, parent_comment_id=bob_comment_id
        )
    async with maker() as s:
        assert await notif_svc.unread_count(s, alice.id) == 2  # carol's reply is also a comment
        assert await notif_svc.unread_count(s, bob.id) == 1  # reply to bob's comment


async def test_mark_all_read_and_settings_update(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        target, _ = await follows_svc.follow(s, follower=alice, login="bob")
        await notif_svc.create_follow_notification(s, followee=target, actor_id=alice.id)
    async with maker() as s:
        assert await notif_svc.unread_count(s, bob.id) == 1
        await notif_svc.mark_all_read(s, bob.id)
    async with maker() as s:
        assert await notif_svc.unread_count(s, bob.id) == 0
    async with maker() as s:
        bob_u = await s.get(User, bob.id)
        res = await notif_svc.update_settings(
            s, user=bob_u, data=NotificationSettingsUpdate(notify_follows=False, notify_posts=PostNotify.OFF)
        )
        assert res.notify_follows is False and res.notify_posts == PostNotify.OFF


async def test_retention_excludes_and_purges_old(engine, users):
    alice, bob = users["alice"], users["bob"]
    notif_svc._last_purge_monotonic = -1e9  # force the throttled purge to run
    maker = get_sessionmaker()
    old = datetime.now(timezone.utc) - timedelta(days=40)
    async with maker() as s:
        s.add(
            Notification(
                recipient_id=bob.id, actor_id=alice.id, type=NotificationType.FOLLOW, created_at=old
            )
        )
        s.add(Notification(recipient_id=bob.id, actor_id=alice.id, type=NotificationType.FOLLOW))
        await s.commit()
    async with maker() as s:
        page = await notif_svc.list_notifications(s, user_id=bob.id, cursor=None, limit=20)
        assert len(page.items) == 1  # the 40-day-old one is excluded
        assert await notif_svc.unread_count(s, bob.id) == 1
    async with maker() as s:
        total = await s.scalar(
            select(func.count(Notification.id)).where(Notification.recipient_id == bob.id)
        )
        assert total == 1  # and physically purged


async def test_list_filter_by_kind(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        for t in (
            NotificationType.POST,
            NotificationType.COMMENT,
            NotificationType.REPLY,
            NotificationType.FOLLOW,
        ):
            s.add(Notification(recipient_id=bob.id, actor_id=alice.id, type=t))
        await s.commit()
    async with maker() as s:
        posts = await notif_svc.list_notifications(
            s, user_id=bob.id, cursor=None, limit=20, kinds={NotificationType.POST}
        )
        assert {i.type for i in posts.items} == {"post"}
        comments = await notif_svc.list_notifications(
            s,
            user_id=bob.id,
            cursor=None,
            limit=20,
            kinds={NotificationType.COMMENT, NotificationType.REPLY},
        )
        assert {i.type for i in comments.items} == {"comment", "reply"}
        all_kinds = await notif_svc.list_notifications(s, user_id=bob.id, cursor=None, limit=20)
        assert len(all_kinds.items) == 4
