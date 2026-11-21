from __future__ import annotations

from ...models.event import Event
from ..query import AsyncQuerySet
from .base import AsyncResource


class AsyncEventsResource(AsyncResource[Event]):
    path = "/events"
    model = Event

    def for_campus(self, campus_id: int) -> AsyncQuerySet[Event]:
        """Query events scoped to a single campus: ``GET /campus/{id}/events``.

        A thin convenience over ``/campus/{id}/events`` so callers don't have to
        fetch the ``Campus`` first just to reach its events. Chainable like any
        other queryset (``.filter()`` / ``.sort()`` / ``.range()``).
        """
        return self._queryset(f"/campus/{campus_id}/events")
