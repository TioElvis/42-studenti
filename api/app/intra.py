"""Adapter over the vendored ``intra42`` client for the public events feed.

The rest of the app depends on :class:`EventsProvider`, not on ``intra42``
directly (DIP). Results are cached in-process for ``events_cache_ttl`` seconds
so repeated page loads don't burn through the 42 API hourly quota.

TODO (Step 2.1): when students can propose community events from the frontend,
add a write path here (or a separate local-events store) so proposed events are
merged with the official 42 Intra feed. Keep official vs. community events
clearly distinguished in the response.
"""

from __future__ import annotations

import asyncio
import time

from intra42 import AsyncClient, Event
from intra42.exceptions import FortyTwoAPIError

from .config import Settings
from .schemas.event import EventOut


class EventsUnavailableError(Exception):
    """Raised when upstream 42 events cannot be fetched."""


class EventsProvider:
    """Fetches and caches upcoming campus events from the 42 Intra API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: tuple[float, list[EventOut]] | None = None
        self._lock = asyncio.Lock()

    def _credentials_present(self) -> bool:
        return bool(self._settings.forty_two_uid and self._settings.forty_two_secret)

    async def get_upcoming(self) -> list[EventOut]:
        """Return cached events, refreshing past the TTL (single-flight)."""
        now = time.monotonic()
        if self._cache and now - self._cache[0] < self._settings.events_cache_ttl:
            return self._cache[1]

        async with self._lock:
            # Double-check: another coroutine may have refreshed while we waited.
            now = time.monotonic()
            if self._cache and now - self._cache[0] < self._settings.events_cache_ttl:
                return self._cache[1]
            events = await self._fetch()
            self._cache = (time.monotonic(), events)
            return events

    async def _fetch(self) -> list[EventOut]:
        if not self._credentials_present():
            raise EventsUnavailableError("42 API credentials are not configured")
        campus_id = self._settings.forty_two_campus_id
        try:
            async with AsyncClient(
                self._settings.forty_two_uid, self._settings.forty_two_secret
            ) as client:
                raw: list[Event] = await client.events.for_campus(campus_id).sort("begin_at").all()
        except FortyTwoAPIError as exc:
            raise EventsUnavailableError("42 API request failed") from exc

        now_ts = time.time()
        upcoming = [
            _to_out(e)
            for e in raw
            if e.end_at is None or e.end_at.timestamp() >= now_ts
        ]
        upcoming.sort(key=lambda e: (e.begin_at is None, e.begin_at))
        return upcoming


    async def registrations(
        self, user_intra_id: int, event_ids: list[int]
    ) -> dict[int, int] | None:
        """Return {event_id: events_user_id} for the user's real 42 sign-ups
        among ``event_ids``, or None on failure.

        This is 42's source of truth, used to reconcile our local mirror so a
        cancellation made directly on the Intra is reflected here.
        """
        if not event_ids or not self._credentials_present():
            return {} if not event_ids else None
        params = {
            "filter[user_id]": str(user_intra_id),
            "filter[event_id]": ",".join(str(e) for e in event_ids),
            "page[size]": "100",
        }
        try:
            async with AsyncClient(
                self._settings.forty_two_uid, self._settings.forty_two_secret
            ) as client:
                resp = await client.request("GET", "/events_users", params=params)
                rows = resp.json()
        except FortyTwoAPIError:
            return None
        out: dict[int, int] = {}
        if isinstance(rows, list):
            for r in rows:
                eid, euid = r.get("event_id"), r.get("id")
                if isinstance(eid, int) and isinstance(euid, int):
                    out[eid] = euid
        return out

    async def subscriber_count(self, event_id: int) -> int | None:
        """Fresh ``nbr_subscribers`` for one event from 42, or None on failure.

        Reads a single event (public data, app token), bypassing the list
        cache so the number reflects a just-made (un)registration.
        """
        if not self._credentials_present():
            return None
        try:
            async with AsyncClient(
                self._settings.forty_two_uid, self._settings.forty_two_secret
            ) as client:
                event = await client.events.get(event_id)
        except FortyTwoAPIError:
            return None
        return int(event.nbr_subscribers or 0)


def _to_out(event: Event) -> EventOut:
    return EventOut(
        id=event.id,
        name=event.name,
        description=event.description,
        location=event.location,
        kind=event.kind,
        begin_at=event.begin_at,
        end_at=event.end_at,
        max_people=event.max_people,
        nbr_subscribers=event.nbr_subscribers,
    )
