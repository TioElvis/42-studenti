# GENERATED FILE — DO NOT EDIT BY HAND.
#
# Generated from the corresponding module under intra42._async by
# scripts/unasync_generate.py (via the `unasync` library). Edit the
# async source and re-run that script instead.

from __future__ import annotations

from ...models.event import Event
from ..query import QuerySet
from .base import Resource


class EventsResource(Resource[Event]):
    path = "/events"
    model = Event

    def for_campus(self, campus_id: int) -> QuerySet[Event]:
        """Query events scoped to a single campus: ``GET /campus/{id}/events``.

        A thin convenience over ``/campus/{id}/events`` so callers don't have to
        fetch the ``Campus`` first just to reach its events. Chainable like any
        other queryset (``.filter()`` / ``.sort()`` / ``.range()``).
        """
        return self._queryset(f"/campus/{campus_id}/events")
