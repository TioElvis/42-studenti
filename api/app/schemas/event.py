"""Event DTO for the Eventi feed (projected from the 42 Intra Event model)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventOut(BaseModel):
    id: int
    name: str | None = None
    description: str | None = None
    location: str | None = None
    kind: str | None = None
    begin_at: datetime | None = None
    end_at: datetime | None = None
    max_people: int | None = None
    nbr_subscribers: int | None = None
    # True when the event is scoped to the 42 Roma campus only; False for a
    # multi-campus / shared event (online, partner, cross-campus).
    internal: bool = True
    # Local "Mi interessa" RSVP state (our DB, per viewer + total).
    interested: bool = False
    interest_count: int = 0


class InterestState(BaseModel):
    interested: bool
    interest_count: int


class EventAttendee(BaseModel):
    """A student registered to an event on 42 (read live from the 42 API)."""

    login: str
    display_name: str | None = None
    avatar_url: str | None = None
