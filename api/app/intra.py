"""Adapter over the vendored ``intra42`` client for the public events feed.

The rest of the app depends on :class:`EventsProvider`, not on ``intra42``
directly (DIP). Results are cached in-process for ``events_cache_ttl`` seconds
so repeated page loads don't burn through the 42 API hourly quota.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from intra42 import AsyncClient, Event
from intra42.exceptions import FortyTwoAPIError
from intra42.exceptions import NotFoundError as IntraNotFound

from .config import Settings
from .schemas.event import EventAttendee, EventOut


class EventsUnavailableError(Exception):
    """Raised when upstream 42 events cannot be fetched."""


class IntraUserNotFound(Exception):
    """The requested 42 login does not exist on the Intra."""


@dataclass(frozen=True)
class ProjectInfo:
    """One of a student's 42 projects."""

    name: str
    status: str  # in_progress | waiting_for_correction | searching_a_group | finished | ...
    mark: int | None
    validated: bool | None


@dataclass(frozen=True)
class IntraUserInfo:
    """A student's public 42 profile (identity + figures), read live from 42."""

    login: str
    display_name: str | None
    avatar_url: str | None
    campus: str | None  # primary campus name
    campus_ids: frozenset[int]  # all campuses the user belongs to (for the gate)
    level: float | None
    grade: str | None
    correction_point: int | None
    wallet: int | None
    location: str | None
    pool: str | None
    joined: datetime | None  # 42 account creation
    projects: tuple[ProjectInfo, ...] = ()
    achievements: tuple[str, ...] = ()


def _extra(user: object) -> dict:
    return getattr(user, "model_extra", None) or {}


# Sort sentinel for events with no begin_at (tz-aware, so it compares safely
# with 42's tz-aware datetimes).
_FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)

# Cap the per-login profile cache so it can't grow without bound.
_PROFILE_CACHE_MAX = 512

# Attendee lists: 100 per page, at most 5 pages (500 names) per event.
_ATTENDEES_PAGE = 100
_ATTENDEES_MAX_PAGES = 5
_ATTENDEE_CACHE_MAX = 64

_COMMON_CORE_CURSUS_ID = 21
_COMMON_CORE_SLUG = "42cursus"

# Internal vs external classification for official events (mirrors 42's own
# notion): a 42 ``kind`` of ``extern``/``partnership`` is External; so is an
# event whose ``location`` is a real off-campus address (street/venue) — unless
# the location mentions the campus, which keeps it Internal.
_EXTERNAL_KINDS = {"extern", "partnership"}
_CAMPUS_LOC_HINTS = ("42", "cluster", "campus")
_EXTERNAL_LOC_HINTS = ("via ", "viale", "piazza", "largo ", "corso ", "strada ", "(rm)", "(roma)")


def _event_is_internal(kind: str | None, location: str | None) -> bool:
    if (kind or "").lower() in _EXTERNAL_KINDS:
        return False
    loc = (location or "").lower()
    # Location override: a clear off-campus address makes it external, but a
    # location that names the campus (e.g. "42 Roma", "Cluster 1") stays internal.
    if loc and not any(h in loc for h in _CAMPUS_LOC_HINTS):
        if any(h in loc for h in _EXTERNAL_LOC_HINTS):
            return False
    return True


def _main_cursus(user: object) -> dict | None:
    """The student's **common-core** (42cursus) cursus_user, or None.

    Strictly the common core — never the Piscine or any other cursus, so a
    Piscine-only student has no level/grade/black-hole here.
    """
    for cu in _extra(user).get("cursus_users") or []:
        if not isinstance(cu, dict):
            continue
        cursus = cu.get("cursus")
        slug = cursus.get("slug") if isinstance(cursus, dict) else None
        if cu.get("cursus_id") == _COMMON_CORE_CURSUS_ID or slug == _COMMON_CORE_SLUG:
            return cu
    return None


def _parse_cursus(user: object) -> tuple[float | None, str | None]:
    """(level, grade) from the common-core cursus."""
    cu = _main_cursus(user)
    if cu is None:
        return None, None
    raw_level = cu.get("level")
    level = round(float(raw_level), 2) if isinstance(raw_level, (int, float)) else None
    grade = cu.get("grade") if isinstance(cu.get("grade"), str) else None
    return level, grade


def _parse_projects(user: object, limit: int = 8) -> tuple[ProjectInfo, ...]:
    """Common-core projects only: current first, then recently finished."""
    core = _main_cursus(user)
    if core is None:
        return ()
    cursus = core.get("cursus")
    core_id = (
        core.get("cursus_id")
        or (cursus.get("id") if isinstance(cursus, dict) else None)
        or _COMMON_CORE_CURSUS_ID
    )
    items = [
        p
        for p in (_extra(user).get("projects_users") or [])
        if isinstance(p, dict) and core_id in (p.get("cursus_ids") or [])
    ]
    ongoing_states = {"in_progress", "waiting_for_correction", "searching_a_group"}
    current = [p for p in items if p.get("status") in ongoing_states]
    finished = sorted(
        (p for p in items if p.get("status") == "finished"),
        key=lambda p: p.get("marked_at") or "",
        reverse=True,
    )
    out: list[ProjectInfo] = []
    for p in (current + finished)[:limit]:
        proj = p.get("project")
        name = (proj.get("name") or proj.get("slug")) if isinstance(proj, dict) else None
        if not name:
            continue
        mark = p.get("final_mark")
        validated = p.get("validated?")
        out.append(
            ProjectInfo(
                name=str(name),
                status=str(p.get("status") or ""),
                mark=int(mark) if isinstance(mark, (int, float)) else None,
                validated=validated if isinstance(validated, bool) else None,
            )
        )
    return tuple(out)


def _parse_achievements(user: object, limit: int = 24) -> tuple[str, ...]:
    """Distinct achievement names (42 'milestones')."""
    seen: set[str] = set()
    names: list[str] = []
    for a in _extra(user).get("achievements") or []:
        name = a.get("name") if isinstance(a, dict) else None
        if isinstance(name, str) and name not in seen:
            seen.add(name)
            names.append(name)
    return tuple(names[:limit])


def _pool_label(user: object) -> str | None:
    month = getattr(user, "pool_month", None)
    year = getattr(user, "pool_year", None)
    if month and year:
        return f"{str(month).capitalize()} {year}"
    return None


def _extract_campus(user: object) -> tuple[str | None, frozenset[int]]:
    """Primary campus name + the set of campus ids (``campus``/``campus_users``
    are extra fields on the 42 user payload)."""
    extra = getattr(user, "model_extra", None) or {}
    campuses = extra.get("campus") or []
    campus_users = extra.get("campus_users") or []
    ids: set[int] = {c["id"] for c in campuses if isinstance(c, dict) and isinstance(c.get("id"), int)}
    primary_id: int | None = None
    for cu in campus_users:
        if isinstance(cu, dict) and cu.get("is_primary") and isinstance(cu.get("campus_id"), int):
            primary_id = cu["campus_id"]
            ids.add(primary_id)
            break
    name: str | None = None
    if primary_id is not None:
        name = next(
            (c.get("name") for c in campuses if isinstance(c, dict) and c.get("id") == primary_id),
            None,
        )
    if name is None and campuses and isinstance(campuses[0], dict):
        name = campuses[0].get("name")
    return name, frozenset(ids)


class EventsProvider:
    """Fetches and caches upcoming campus events from the 42 Intra API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: tuple[float, list[EventOut]] | None = None
        self._lock = asyncio.Lock()
        # Per-login 42 profile cache (profiles change slowly).
        self._profile_cache: dict[str, tuple[float, IntraUserInfo]] = {}
        self._profile_lock = asyncio.Lock()
        # Per-event attendee cache (registrations change slowly; one 42 call each).
        self._attendee_cache: dict[int, tuple[float, list[EventAttendee]]] = {}

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
        # Only events that haven't started yet: once the start time has passed
        # the event is hidden (this also drops long-running pinned/news posts).
        # Undated events fall back to the end date.
        upcoming = [
            _to_out(e)
            for e in raw
            if (
                e.begin_at.timestamp() >= now_ts
                if e.begin_at is not None
                else (e.end_at is None or e.end_at.timestamp() >= now_ts)
            )
        ]
        # Undated events sort last; the sentinel avoids comparing None to None
        # (a TypeError) when two or more events have no begin_at.
        upcoming.sort(key=lambda e: (e.begin_at is None, e.begin_at or _FAR_FUTURE))
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

    async def attendees(self, event_id: int) -> list[EventAttendee]:
        """Everyone registered to ``event_id`` on 42 (names straight from 42).

        Cached for ``events_cache_ttl`` seconds. Raises
        :class:`EventsUnavailableError` if 42 is unreachable / unconfigured.
        """
        now = time.monotonic()
        hit = self._attendee_cache.get(event_id)
        if hit and now - hit[0] < self._settings.events_cache_ttl:
            return hit[1]
        if not self._credentials_present():
            raise EventsUnavailableError("42 credentials not configured")
        people: list[EventAttendee] = []
        try:
            async with AsyncClient(
                self._settings.forty_two_uid, self._settings.forty_two_secret
            ) as client:
                for page in range(1, _ATTENDEES_MAX_PAGES + 1):
                    resp = await client.request(
                        "GET",
                        f"/events/{event_id}/users",
                        params={"page[size]": str(_ATTENDEES_PAGE), "page[number]": str(page)},
                    )
                    rows = resp.json()
                    if not isinstance(rows, list):
                        break
                    for u in rows:
                        login = u.get("login") if isinstance(u, dict) else None
                        if not isinstance(login, str) or not login:
                            continue
                        image = u.get("image") or {}
                        people.append(
                            EventAttendee(
                                login=login,
                                display_name=u.get("displayname") or u.get("usual_full_name"),
                                avatar_url=image.get("link") if isinstance(image, dict) else None,
                            )
                        )
                    if len(rows) < _ATTENDEES_PAGE:
                        break
        except FortyTwoAPIError as exc:
            raise EventsUnavailableError("Couldn't fetch attendees from 42") from exc
        people.sort(key=lambda a: (a.display_name or a.login).lower())
        if len(self._attendee_cache) >= _ATTENDEE_CACHE_MAX:
            self._attendee_cache.pop(next(iter(self._attendee_cache)))
        self._attendee_cache[event_id] = (now, people)
        return people

    def invalidate_attendees(self, event_id: int) -> None:
        """Drop the cached list (used after a (un)registration made here)."""
        self._attendee_cache.pop(event_id, None)

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

    async def user_profile(self, login: str) -> IntraUserInfo:
        """A student's live 42 profile, cached per login.

        Raises :class:`IntraUserNotFound` if 42 has no such login, and
        :class:`EventsUnavailableError` if 42 is unreachable or no credentials
        are set.
        """
        if not self._credentials_present():
            raise EventsUnavailableError("42 API credentials are not configured")
        cached = self._profile_cache.get(login)
        if cached and time.monotonic() - cached[0] < self._settings.events_cache_ttl:
            return cached[1]
        async with self._profile_lock:
            cached = self._profile_cache.get(login)
            if cached and time.monotonic() - cached[0] < self._settings.events_cache_ttl:
                return cached[1]
            info = await self._fetch_user_info(login)
            # Evict the oldest entry if the cache is full (bounded memory).
            if len(self._profile_cache) >= _PROFILE_CACHE_MAX and login not in self._profile_cache:
                oldest = min(self._profile_cache, key=lambda k: self._profile_cache[k][0])
                self._profile_cache.pop(oldest, None)
            self._profile_cache[login] = (time.monotonic(), info)
            return info

    async def _fetch_user_info(self, login: str) -> IntraUserInfo:
        try:
            async with AsyncClient(
                self._settings.forty_two_uid, self._settings.forty_two_secret
            ) as client:
                u = await client.users.get(login)
        except IntraNotFound as exc:
            raise IntraUserNotFound(login) from exc
        except FortyTwoAPIError as exc:
            raise EventsUnavailableError("42 profile fetch failed") from exc
        campus_name, campus_ids = _extract_campus(u)
        image = getattr(u, "image", None)
        level, grade = _parse_cursus(u)
        return IntraUserInfo(
            login=u.login or login,
            display_name=u.displayname or getattr(u, "usual_full_name", None),
            avatar_url=getattr(image, "link", None),
            campus=campus_name,
            campus_ids=campus_ids,
            level=level,
            grade=grade,
            correction_point=int(u.correction_point) if u.correction_point is not None else None,
            wallet=int(u.wallet) if u.wallet is not None else None,
            location=u.location,
            pool=_pool_label(u),
            joined=getattr(u, "created_at", None),
            projects=_parse_projects(u),
            achievements=_parse_achievements(u),
        )


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
        internal=_event_is_internal(event.kind, event.location),
    )
