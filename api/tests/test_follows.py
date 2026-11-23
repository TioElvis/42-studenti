"""Follow system: follow/unfollow, idempotency, self-follow, stats."""

from __future__ import annotations

import pytest

from app.database import get_sessionmaker
from app.services import follows as follows_svc
from app.services.exceptions import ConflictError


async def test_follow_unfollow_and_stats(engine, users):
    alice, bob = users["alice"], users["bob"]
    maker = get_sessionmaker()
    async with maker() as s:
        target, created = await follows_svc.follow(s, follower=alice, login="bob")
        assert created is True and target.login == "bob"
    async with maker() as s:
        _, created_again = await follows_svc.follow(s, follower=alice, login="bob")
        assert created_again is False  # idempotent
    async with maker() as s:
        followers, _, is_following = await follows_svc.stats(
            s, user_id=bob.id, viewer_id=alice.id
        )
        assert followers == 1 and is_following is True
        _, following_a, _ = await follows_svc.stats(s, user_id=alice.id, viewer_id=bob.id)
        assert following_a == 1
    async with maker() as s:
        await follows_svc.unfollow(s, follower=alice, login="bob")
    async with maker() as s:
        followers, _, is_following = await follows_svc.stats(
            s, user_id=bob.id, viewer_id=alice.id
        )
        assert followers == 0 and is_following is False


async def test_cannot_follow_self(engine, users):
    async with get_sessionmaker()() as s:
        with pytest.raises(ConflictError):
            await follows_svc.follow(s, follower=users["alice"], login="alice")
