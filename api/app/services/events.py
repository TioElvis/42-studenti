"""Event-interest service: local "Mi interessa" RSVPs and their counts."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import intra_user
from ..config import Settings
from ..models.event_interest import EventInterest
from ..models.user import User


async def toggle_interest(
    session: AsyncSession, *, settings: Settings, user: User, event_id: int
) -> bool:
    """Register/unregister the student to the 42 event, mirrored locally.

    Calls 42 first (``events_users`` POST/DELETE); only on success is the local
    row changed, so our DB never claims a registration 42 didn't accept.
    Returns whether the student is now registered. Raises ``IntraAuthRequired``
    / ``IntraApiError`` from ``intra_user`` on failure (mapped by the router).
    The displayed count comes from 42's ``nbr_subscribers`` (see the router).
    """
    existing = (
        await session.execute(
            select(EventInterest).where(
                EventInterest.user_id == user.id, EventInterest.event_id == event_id
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        if existing.intra_events_user_id is not None:
            await intra_user.unsubscribe_from_event(
                session, settings, user, existing.intra_events_user_id
            )
        await session.delete(existing)
        await session.commit()
        return False

    events_user_id = await intra_user.subscribe_to_event(session, settings, user, event_id)
    session.add(
        EventInterest(user_id=user.id, event_id=event_id, intra_events_user_id=events_user_id)
    )
    await session.commit()
    return True


async def local_count(session: AsyncSession, event_id: int) -> int:
    """Local RSVP count (fallback when 42's nbr_subscribers can't be fetched)."""
    count = await session.scalar(
        select(func.count(EventInterest.id)).where(EventInterest.event_id == event_id)
    )
    return int(count or 0)


async def reconcile_registrations(
    session: AsyncSession,
    *,
    user_id: int,
    feed_event_ids: list[int],
    intra_regs: dict[int, int],
) -> None:
    """Make the local mirror match 42's real registrations for the feed events.

    Adds rows for sign-ups made on 42, removes rows cancelled on 42, and
    refreshes the stored 42 ``events_user`` id. Only touches events currently
    in the feed, so local rows for past/other events are left alone.
    """
    if not feed_event_ids:
        return
    rows = (
        await session.execute(
            select(EventInterest).where(
                EventInterest.user_id == user_id,
                EventInterest.event_id.in_(feed_event_ids),
            )
        )
    ).scalars().all()
    local = {r.event_id: r for r in rows}
    changed = False
    for eid in feed_event_ids:
        intra_id = intra_regs.get(eid)
        row = local.get(eid)
        if intra_id is not None and row is None:
            session.add(
                EventInterest(user_id=user_id, event_id=eid, intra_events_user_id=intra_id)
            )
            changed = True
        elif intra_id is None and row is not None:
            await session.delete(row)
            changed = True
        elif intra_id is not None and row is not None and row.intra_events_user_id != intra_id:
            row.intra_events_user_id = intra_id
            changed = True
    if changed:
        await session.commit()


async def counts_for(session: AsyncSession, event_ids: Iterable[int]) -> dict[int, int]:
    ids = list(event_ids)
    if not ids:
        return {}
    rows = await session.execute(
        select(EventInterest.event_id, func.count(EventInterest.id))
        .where(EventInterest.event_id.in_(ids))
        .group_by(EventInterest.event_id)
    )
    return {int(eid): int(c) for eid, c in rows.all()}


async def interested_ids(
    session: AsyncSession, *, user_id: int, event_ids: Iterable[int]
) -> set[int]:
    ids = list(event_ids)
    if not ids:
        return set()
    rows = await session.execute(
        select(EventInterest.event_id).where(
            EventInterest.user_id == user_id, EventInterest.event_id.in_(ids)
        )
    )
    return {int(r) for r in rows.scalars().all()}
