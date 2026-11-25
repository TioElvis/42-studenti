"""Eventi feed via the local 42api wrapper (upstream mocked with respx)."""

from __future__ import annotations

import respx
from httpx import Response

import app.deps as deps

EVENTS_PAYLOAD = [
    {
        "id": 1,
        "name": "Hackathon Romano",
        "description": "48h di codice",
        "location": "Cluster 1",
        "kind": "hackathon",
        "begin_at": "2999-01-01T10:00:00.000Z",
        "end_at": "2999-01-02T10:00:00.000Z",
        "max_people": 100,
        "nbr_subscribers": 10,
    },
    {
        "id": 2,
        "name": "Vecchio evento",
        "description": "passato",
        "location": "Aula",
        "kind": "meetup",
        "begin_at": "2000-01-01T10:00:00.000Z",
        "end_at": "2000-01-01T12:00:00.000Z",
    },
]


async def test_events_feed_returns_only_upcoming(client):
    # Reset the provider singleton so this test's cache is fresh.
    deps._events_provider = None

    with respx.mock(assert_all_called=False) as mock:
        mock.post("https://api.intra.42.fr/oauth/token").mock(
            return_value=Response(200, json={"access_token": "app-token", "expires_in": 7200})
        )
        mock.route(
            method="GET", url__startswith="https://api.intra.42.fr/v2/campus/61/events"
        ).mock(return_value=Response(200, json=EVENTS_PAYLOAD))
        # Reconciliation reads the user's real 42 registrations (none here).
        mock.route(
            method="GET", url__startswith="https://api.intra.42.fr/v2/events_users"
        ).mock(return_value=Response(200, json=[]))

        resp = await client.get("/events")

    assert resp.status_code == 200
    data = resp.json()
    # Only the future event survives the upcoming filter.
    assert [e["id"] for e in data] == [1]
    assert data[0]["name"] == "Hackathon Romano"
    assert data[0]["interested"] is False

    deps._events_provider = None  # don't leak the cache into other tests


_SCOPE_PAYLOAD = [
    # Campus activity (internal kind, on-campus location) -> Interno.
    {
        "id": 10,
        "name": "Meetup al cluster",
        "kind": "meet_up",
        "location": "Cluster 1",
        "begin_at": "2999-01-01T10:00:00.000Z",
        "end_at": "2999-01-01T12:00:00.000Z",
    },
    # External kind -> Esterno (even though single-campus, like XmasDev).
    {
        "id": 11,
        "name": "Conferenza XmasDev",
        "kind": "extern",
        "location": "Seraphicum",
        "begin_at": "2999-01-02T10:00:00.000Z",
        "end_at": "2999-01-02T12:00:00.000Z",
    },
    # Internal-ish kind but off-campus address -> Esterno via location override.
    {
        "id": 12,
        "name": "Conferenza fuori sede",
        "kind": "conference",
        "location": "Via del Serafico 1 (RM)",
        "begin_at": "2999-01-03T10:00:00.000Z",
        "end_at": "2999-01-03T12:00:00.000Z",
    },
    # Conference whose location names the campus -> stays Interno.
    {
        "id": 13,
        "name": "Conferenza in campus",
        "kind": "conference",
        "location": "42 Roma, Aula Magna",
        "begin_at": "2999-01-04T10:00:00.000Z",
        "end_at": "2999-01-04T12:00:00.000Z",
    },
]


async def test_events_internal_external_flag(client):
    deps._events_provider = None
    with respx.mock(assert_all_called=False) as mock:
        mock.post("https://api.intra.42.fr/oauth/token").mock(
            return_value=Response(200, json={"access_token": "app-token", "expires_in": 7200})
        )
        mock.route(
            method="GET", url__startswith="https://api.intra.42.fr/v2/campus/61/events"
        ).mock(return_value=Response(200, json=_SCOPE_PAYLOAD))
        mock.route(
            method="GET", url__startswith="https://api.intra.42.fr/v2/events_users"
        ).mock(return_value=Response(200, json=[]))
        resp = await client.get("/events")

    assert resp.status_code == 200
    internal_by_id = {e["id"]: e["internal"] for e in resp.json()}
    # 10 campus meetup, 13 conference in campus -> Interno; 11 extern, 12 off-campus -> Esterno.
    assert internal_by_id == {10: True, 11: False, 12: False, 13: True}

    deps._events_provider = None


# --- GET /events/{id}/attendees: names come straight from the 42 API ----------

_TOKEN_URL = "https://api.intra.42.fr/oauth/token"
_CAMPUS_EVENTS = "https://api.intra.42.fr/v2/campus/61/events"


def _mock_feed(mock):
    mock.post(_TOKEN_URL).mock(
        return_value=Response(200, json={"access_token": "app-token", "expires_in": 7200})
    )
    mock.route(method="GET", url__startswith=_CAMPUS_EVENTS).mock(
        return_value=Response(200, json=EVENTS_PAYLOAD)
    )


async def test_attendees_listed_from_42(client):
    deps._events_provider = None
    with respx.mock(assert_all_called=False) as mock:
        _mock_feed(mock)
        users = mock.route(
            method="GET", url__startswith="https://api.intra.42.fr/v2/events/1/users"
        ).mock(
            return_value=Response(
                200,
                json=[
                    {"login": "zed", "usual_full_name": "Zed Z", "image": {"link": "https://x/z.jpg"}},
                    {"login": "amy", "displayname": "Amy Adams", "image": None},
                    {"id": 5},  # no login: skipped
                ],
            )
        )
        resp = await client.get("/events/1/attendees")
        again = await client.get("/events/1/attendees")  # served from the cache
    assert resp.status_code == 200
    assert resp.json() == [
        {"login": "amy", "display_name": "Amy Adams", "avatar_url": None},
        {"login": "zed", "display_name": "Zed Z", "avatar_url": "https://x/z.jpg"},
    ]
    assert again.json() == resp.json() and users.call_count == 1
    deps._events_provider = None


async def test_attendees_unknown_event_404(client):
    deps._events_provider = None
    with respx.mock(assert_all_called=False) as mock:
        _mock_feed(mock)
        resp = await client.get("/events/999/attendees")
    assert resp.status_code == 404
    deps._events_provider = None


async def test_attendees_42_failure_503(client):
    deps._events_provider = None
    with respx.mock(assert_all_called=False) as mock:
        _mock_feed(mock)
        mock.route(
            method="GET", url__startswith="https://api.intra.42.fr/v2/events/1/users"
        ).mock(return_value=Response(403, json={}))
        resp = await client.get("/events/1/attendees")
    assert resp.status_code == 503
    deps._events_provider = None
