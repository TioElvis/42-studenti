"""Sondaggi: options polls (single/multi vote) + attendance auto-join."""

from __future__ import annotations


async def _create_options_poll(client, *, multi: bool, options=("A", "B", "C")):
    resp = await client.post(
        "/posts",
        json={
            "content": "Quando ci vediamo?",
            "category": "off_topic",
            "post_type": "sondaggio",
            "poll_mode": "options",
            "poll_multi": multi,
            "options": list(options),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _opts(detail):
    return {o["text"]: o for o in detail["poll_options"]}


async def test_create_options_poll_exposes_options(client):
    detail = await _create_options_poll(client, multi=False)
    assert detail["poll_mode"] == "options"
    assert [o["text"] for o in detail["poll_options"]] == ["A", "B", "C"]
    assert all(o["vote_count"] == 0 and o["voted_by_me"] is False for o in detail["poll_options"])


async def test_single_choice_vote_toggles_and_switches(client):
    detail = await _create_options_poll(client, multi=False)
    pid = detail["id"]
    a, b = _opts(detail)["A"]["id"], _opts(detail)["B"]["id"]

    # Vote A.
    state = (await client.post(f"/posts/{pid}/poll/vote", json={"option_id": a})).json()
    by_id = {o["id"]: o for o in state["options"]}
    assert by_id[a]["vote_count"] == 1 and by_id[a]["voted_by_me"] is True

    # Switch to B — A is dropped (single choice).
    state = (await client.post(f"/posts/{pid}/poll/vote", json={"option_id": b})).json()
    by_id = {o["id"]: o for o in state["options"]}
    assert by_id[a]["vote_count"] == 0 and by_id[a]["voted_by_me"] is False
    assert by_id[b]["vote_count"] == 1 and by_id[b]["voted_by_me"] is True

    # Click B again — toggles off.
    state = (await client.post(f"/posts/{pid}/poll/vote", json={"option_id": b})).json()
    by_id = {o["id"]: o for o in state["options"]}
    assert by_id[b]["vote_count"] == 0 and by_id[b]["voted_by_me"] is False


async def test_multi_choice_allows_several(client):
    detail = await _create_options_poll(client, multi=True)
    pid = detail["id"]
    a, b = _opts(detail)["A"]["id"], _opts(detail)["B"]["id"]
    await client.post(f"/posts/{pid}/poll/vote", json={"option_id": a})
    state = (await client.post(f"/posts/{pid}/poll/vote", json={"option_id": b})).json()
    by_id = {o["id"]: o for o in state["options"]}
    assert by_id[a]["voted_by_me"] is True and by_id[b]["voted_by_me"] is True


async def test_options_poll_needs_two_options(client):
    resp = await client.post(
        "/posts",
        json={
            "content": "x",
            "category": "off_topic",
            "post_type": "sondaggio",
            "poll_mode": "options",
            "options": ["Solo una"],
        },
    )
    assert resp.status_code == 422


async def test_attendance_auto_join(client):
    joined = await client.post(
        "/posts",
        json={
            "content": "Vieni?",
            "category": "off_topic",
            "post_type": "sondaggio",
            "participate": True,
        },
    )
    assert joined.status_code == 201
    body = joined.json()
    assert body["rsvp_count"] == 1 and body["joined_by_me"] is True

    not_joined = await client.post(
        "/posts",
        json={
            "content": "Vieni?",
            "category": "off_topic",
            "post_type": "sondaggio",
            "participate": False,
        },
    )
    assert not_joined.json()["rsvp_count"] == 0


async def test_vote_on_non_options_post_conflicts(client):
    # A plain post isn't a poll.
    post = (
        await client.post("/posts", json={"content": "ciao", "category": "off_topic"})
    ).json()
    resp = await client.post(f"/posts/{post['id']}/poll/vote", json={"option_id": 1})
    assert resp.status_code == 409
