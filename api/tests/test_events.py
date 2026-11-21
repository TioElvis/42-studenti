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
