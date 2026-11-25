"""Eventi: upcoming official 42 Roma events (cached, fetched via local 42api)
plus local "Mi interessa" RSVPs.

Official 42 events can't be joined via our ``public`` OAuth scope, so interest
is tracked in our own DB (see services/events.py). Interest is per student and
counted across the campus; counts update live over the WebSocket.

TODO (Step 2.1): add POST /events to let authenticated students PROPOSE custom
community events (stored locally, clearly separated from official 42 events).
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from fastapi.exceptions import HTTPException

from ..deps import CurrentUser, EventsProviderDep, SessionDep, SettingsDep
from ..intra import EventsUnavailableError
from ..intra_user import IntraApiError, IntraAuthRequired
from ..realtime import manager
from ..schemas.event import EventAttendee, EventOut, InterestState
from ..services import events as events_service

router = APIRouter(prefix="/events", tags=["events"])


async def _upcoming_or_503(provider: EventsProviderDep) -> list[EventOut]:
    try:
        return await provider.get_upcoming()
    except EventsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Aò, 'nte impanicà! Gli eventi non so' disponibili proprio mo'.",
        ) from exc


@router.get("", response_model=list[EventOut])
async def list_events(
    provider: EventsProviderDep,
    session: SessionDep,
    user: CurrentUser,
    settings: SettingsDep,
    response: Response,
) -> list[EventOut]:
    """Upcoming campus events, annotated with this student's RSVP state."""
    # Per-viewer data (RSVP flags) → short private cache for perf, never shared.
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
    base = await _upcoming_or_503(provider)
    ids = [e.id for e in base]
    # Reconcile our local mirror with 42's real sign-ups (so a cancellation made
    # on the Intra is reflected here and we don't show a stale "iscritto").
    regs = await provider.registrations(user.intra_id, ids)
    if regs is not None:
        await events_service.reconcile_registrations(
            session, user_id=user.id, feed_event_ids=ids, intra_regs=regs
        )
    mine = await events_service.interested_ids(session, user_id=user.id, event_ids=ids)
    # Count shown is 42's own nbr_subscribers; "interested" is this viewer's RSVP.
    # Copy per request so the shared provider cache never holds per-user data.
    return [
        e.model_copy(
            update={"interested": e.id in mine, "interest_count": e.nbr_subscribers or 0}
        )
        for e in base
    ]


@router.get("/{event_id}/attendees", response_model=list[EventAttendee])
async def list_attendees(
    event_id: int,
    provider: EventsProviderDep,
    settings: SettingsDep,
    user: CurrentUser,
    response: Response,
) -> list[EventAttendee]:
    """Who is registered to an upcoming event, with names read live from 42."""
    base = await _upcoming_or_503(provider)
    if not any(e.id == event_id for e in base):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento non trovato.")
    try:
        people = await provider.attendees(event_id)
    except EventsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nun riesco a legge chi è iscritto da 42, riprova tra poco.",
        ) from exc
    response.headers["Cache-Control"] = f"private, max-age={settings.http_cache_seconds}"
    return people


@router.post("/{event_id}/interest", response_model=InterestState)
async def toggle_interest(
    event_id: int,
    provider: EventsProviderDep,
    session: SessionDep,
    settings: SettingsDep,
    user: CurrentUser,
) -> InterestState:
    """Register / unregister to an upcoming campus event on 42, mirrored locally."""
    # Allow-list: only accept RSVPs for events that are actually in the feed.
    base = await _upcoming_or_503(provider)
    if not any(e.id == event_id for e in base):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento non trovato.",
        )
    try:
        interested = await events_service.toggle_interest(
            session, settings=settings, user=user, event_id=event_id
        )
    except IntraAuthRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ri-accedi con 42 pe' iscriverti all'evento (serve il permesso 'profile').",
        ) from exc
    except IntraApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "42 non ha accettato l'operazione.",
        ) from exc

    provider.invalidate_attendees(event_id)  # the list just changed
    # Count = 42's fresh nbr_subscribers; fall back to our local mirror if 42 is down.
    count = await provider.subscriber_count(event_id)
    if count is None:
        count = await events_service.local_count(session, event_id)
    await manager.broadcast("event.interest", {"event_id": event_id, "interest_count": count})
    return InterestState(interested=interested, interest_count=count)
