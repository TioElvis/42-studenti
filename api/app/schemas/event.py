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
    # Local "Mi interessa" RSVP state (our DB, per viewer + total).
    interested: bool = False
    interest_count: int = 0


class InterestState(BaseModel):
    interested: bool
    interest_count: int
