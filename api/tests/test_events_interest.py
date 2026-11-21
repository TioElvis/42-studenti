"""Event RSVP: real 42 events_users sign-up/cancel, mirrored locally."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import respx
from httpx import Response

from app import crypto
from app.config import get_settings
from app.database import get_sessionmaker
from app.intra_user import IntraAuthRequired
from app.models.event_interest import EventInterest
from app.services import events as svc

EVENTS_USERS_URL = "https://api.intra.42.fr/v2/events_users"


async def _give_token(user_id: int):
    """Store a valid (non-expired) fake 42 token on the user."""
    maker = get_sessionmaker()
    async with maker() as s:
        from app.models.user import User

        u = await s.get(User, user_id)
        assert u is not None
        u.intra_access_token_enc = crypto.encrypt("fake-42-access-token")
        u.intra_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await s.commit()


async def test_subscribe_then_unsubscribe(engine, users):
    settings = get_settings()
    alice_id = users["alice"].id
    await _give_token(alice_id)
    maker = get_sessionmaker()

    with respx.mock(assert_all_called=False) as mock:
        post = mock.post(EVENTS_USERS_URL).mock(
            return_value=Response(201, json={"id": 999, "event_id": 42})
        )
        delete = mock.delete(f"{EVENTS_USERS_URL}/999").mock(return_value=Response(204))

        async with maker() as s:
            alice = await _reload(s, alice_id)
            interested = await svc.toggle_interest(
                s, settings=settings, user=alice, event_id=42
            )
        assert interested is True
        assert post.called
        # The 42 registration id is stored locally for later cancellation.
        async with maker() as s:
            row = (await _interest(s, alice_id, 42))
            assert row is not None and row.intra_events_user_id == 999

        async with maker() as s:
            alice = await _reload(s, alice_id)
            interested = await svc.toggle_interest(
                s, settings=settings, user=alice, event_id=42
            )
        assert interested is False
        assert delete.called


async def test_subscribe_without_token_raises(engine, users):
    settings = get_settings()
    bob_id = users["bob"].id  # bob has no stored 42 token
    maker = get_sessionmaker()
    async with maker() as s:
        bob = await _reload(s, bob_id)
        try:
            await svc.toggle_interest(s, settings=settings, user=bob, event_id=7)
            raised = False
        except IntraAuthRequired:
            raised = True
    assert raised is True


async def test_counts_and_interested_ids(engine, users):
    # Direct DB rows (no 42 call) to check the read helpers still work.
    maker = get_sessionmaker()
    async with maker() as s:
        s.add(EventInterest(user_id=users["alice"].id, event_id=5, intra_events_user_id=1))
        s.add(EventInterest(user_id=users["bob"].id, event_id=5, intra_events_user_id=2))
        await s.commit()
    async with maker() as s:
        assert await svc.counts_for(s, [5, 9]) == {5: 2}
        assert await svc.interested_ids(s, user_id=users["bob"].id, event_ids=[5, 9]) == {5}


async def _reload(session, user_id):
    from app.models.user import User

    return await session.get(User, user_id)


async def _interest(session, user_id, event_id):
    from sqlalchemy import select

    return (
        await session.execute(
            select(EventInterest).where(
                EventInterest.user_id == user_id, EventInterest.event_id == event_id
            )
        )
    ).scalar_one_or_none()


async def test_reconcile_adds_and_removes(engine, users):
    """Local mirror self-heals against 42's real registrations."""
    from app.models.event_interest import EventInterest

    alice = users["alice"].id
    maker = get_sessionmaker()
    # Pre-existing local row for event 100 that 42 no longer has (cancelled there).
    async with maker() as s:
        s.add(EventInterest(user_id=alice, event_id=100, intra_events_user_id=55))
        await s.commit()

    # 42 says: not registered to 100, but registered to 200 (events_user id 77).
    async with maker() as s:
        await svc.reconcile_registrations(
            s, user_id=alice, feed_event_ids=[100, 200], intra_regs={200: 77}
        )

    async with maker() as s:
        assert await svc.interested_ids(s, user_id=alice, event_ids=[100, 200]) == {200}
        row = await _interest(s, alice, 200)
        assert row is not None and row.intra_events_user_id == 77
        assert await _interest(s, alice, 100) is None
