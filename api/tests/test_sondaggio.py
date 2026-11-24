"""Sondaggio posts: capacity rules, RSVP toggle, full -> 409, attendees."""

from __future__ import annotations


async def _make(client, **overrides):
    # participate=False so these RSVP/capacity tests start with an empty poll
    # (the author auto-join default is covered in test_polls.py).
    payload = {
        "content": "Se vedemo?",
        "category": "evento_casuale",
        "post_type": "sondaggio",
        "participate": False,
    }
    payload.update(overrides)
    return await client.post("/posts", json=payload)


async def test_create_sondaggio_unlimited(client):
    resp = await _make(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["post_type"] == "sondaggio"
    assert body["max_participants"] is None
    assert body["rsvp_count"] == 0
    assert body["rsvp_full"] is False


async def test_cerco_team_requires_1_to_3(client):
    # Missing capacity for cerco_team sondaggio -> 422.
    bad = await _make(client, category="cerco_team")
    assert bad.status_code == 422
    # Out of range -> 422.
    too_big = await _make(client, category="cerco_team", max_participants=4)
    assert too_big.status_code == 422
    # Valid.
    ok = await _make(client, category="cerco_team", max_participants=2)
    assert ok.status_code == 201
    assert ok.json()["max_participants"] == 2


async def test_rsvp_toggle_and_count(client):
    post = (await _make(client)).json()
    pid = post["id"]

    r1 = await client.post(f"/posts/{pid}/rsvp")
    assert r1.status_code == 200
    assert r1.json() == {"joined": True, "rsvp_count": 1, "rsvp_full": False}

    r2 = await client.post(f"/posts/{pid}/rsvp")
    assert r2.json() == {"joined": False, "rsvp_count": 0, "rsvp_full": False}


async def test_capacity_enforced_409(client, users):
    # A cerco_team sondaggio with capacity 1.
    post = (await _make(client, category="cerco_team", max_participants=1)).json()
    pid = post["id"]

    # Alice joins -> full.
    r1 = await client.post(f"/posts/{pid}/rsvp")
    assert r1.json()["rsvp_full"] is True

    # Bob tries to join a full sondaggio -> 409.
    client.auth_ctx.current = users["bob"]
    r2 = await client.post(f"/posts/{pid}/rsvp")
    assert r2.status_code == 409


async def test_rsvp_on_plain_post_rejected(client):
    plain = await client.post("/posts", json={"content": "ciao", "category": "studio"})
    pid = plain.json()["id"]
    resp = await client.post(f"/posts/{pid}/rsvp")
    assert resp.status_code == 409


async def test_attendees_list(client, users):
    post = (await _make(client)).json()
    pid = post["id"]
    await client.post(f"/posts/{pid}/rsvp")  # alice joins
    client.auth_ctx.current = users["bob"]
    await client.post(f"/posts/{pid}/rsvp")  # bob joins

    resp = await client.get(f"/posts/{pid}/attendees")
    assert resp.status_code == 200
    logins = {a["login"] for a in resp.json()}
    assert logins == {"alice", "bob"}


async def test_cursor_pagination(client):
    created_ids = []
    for i in range(5):
        r = await client.post("/posts", json={"content": f"post {i}", "category": "studio"})
        created_ids.append(r.json()["id"])

    first = (await client.get("/posts", params={"limit": 2})).json()
    assert len(first["items"]) == 2
    assert first["next_cursor"] is not None
    # Newest first: the two highest ids.
    assert [p["id"] for p in first["items"]] == sorted(created_ids, reverse=True)[:2]

    second = (
        await client.get("/posts", params={"limit": 2, "cursor": first["next_cursor"]})
    ).json()
    assert [p["id"] for p in second["items"]] == sorted(created_ids, reverse=True)[2:4]
    # No overlap between pages.
    assert set(p["id"] for p in first["items"]).isdisjoint(p["id"] for p in second["items"])


async def test_edit_raise_capacity(client):
    post = (await _make(client, max_participants=2)).json()
    r = await client.patch(f"/posts/{post['id']}", json={"max_participants": 5})
    assert r.status_code == 200
    assert r.json()["max_participants"] == 5


async def test_edit_cannot_lower_below_current(client, users):
    # evento_casuale sondaggio, cap 5; alice (author) + bob both join -> 2 in.
    post = (await _make(client, max_participants=5)).json()
    pid = post["id"]
    await client.post(f"/posts/{pid}/rsvp")  # alice
    client.auth_ctx.current = users["bob"]
    await client.post(f"/posts/{pid}/rsvp")  # bob
    client.auth_ctx.current = users["alice"]  # author edits
    r = await client.patch(f"/posts/{pid}", json={"max_participants": 1})
    assert r.status_code == 409


async def test_edit_cerco_team_range_enforced(client):
    post = (await _make(client, category="cerco_team", max_participants=2)).json()
    pid = post["id"]
    assert (await client.patch(f"/posts/{pid}", json={"max_participants": 4})).status_code == 409
    ok = await client.patch(f"/posts/{pid}", json={"max_participants": 3})
    assert ok.status_code == 200 and ok.json()["max_participants"] == 3


async def test_edit_set_unlimited(client):
    post = (await _make(client, max_participants=5)).json()
    r = await client.patch(f"/posts/{post['id']}", json={"max_participants": None})
    assert r.status_code == 200 and r.json()["max_participants"] is None


async def test_edit_capacity_on_plain_post_rejected(client):
    plain = (await client.post("/posts", json={"content": "x", "category": "studio"})).json()
    r = await client.patch(f"/posts/{plain['id']}", json={"max_participants": 5})
    assert r.status_code == 409
