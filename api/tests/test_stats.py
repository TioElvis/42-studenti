"""Studenti leaderboards: live DB rankings + the 42 snapshot (mocked)."""

from __future__ import annotations

import asyncio

import respx
from httpx import Response

import app.deps as deps
from app.database import get_sessionmaker
from app.intra_stats import IntraStats, parse_duration
from app.models.user import User

TOKEN_URL = "https://api.intra.42.fr/oauth/token"
V2 = "https://api.intra.42.fr/v2"


def test_parse_duration():
    assert parse_duration("03:25:41.123456") == 3 * 3600 + 25 * 60 + 41
    assert parse_duration("00:00:00.000000") == 0
    assert parse_duration("12:00:00") == 43200
    for bad in (None, 5, "", "abc", "1:2"):
        assert parse_duration(bad) == 0


async def _as(client, user):
    client.auth_ctx.current = user


async def test_followers_and_daje_rankings(client, users):
    alice, bob = users["alice"], users["bob"]
    # bob follows alice; alice follows nobody.
    await _as(client, bob)
    assert (await client.post(f"/users/{alice.login}/follow")).status_code in (200, 201, 204)
    # alice posts; bob likes it (counts), alice likes her own (must not count).
    await _as(client, alice)
    pid = (await client.post("/posts", json={"content": "ciao", "category": "studio"})).json()["id"]
    await client.post(f"/posts/{pid}/like")  # own like: ignored
    await _as(client, bob)
    await client.post(f"/posts/{pid}/like")

    body = (await client.get("/students/stats")).json()
    assert [(r["login"], r["value"]) for r in body["followers"]] == [("alice", 1)]
    assert [(r["login"], r["value"]) for r in body["daje"]] == [("alice", 1)]
    assert body["intra_ready"] is False and body["wallet"] == [] and body["cluster"] == []
    assert body["cluster_days"] == 30


def _intra_mocks(mock, *, wallets, stats):
    mock.post(TOKEN_URL).mock(
        return_value=Response(200, json={"access_token": "t", "expires_in": 7200})
    )
    for login, w in wallets.items():
        mock.get(f"{V2}/users/{login}").mock(
            return_value=Response(200, json={"id": 1, "login": login, "wallet": w})
        )
        mock.route(method="GET", url__startswith=f"{V2}/users/{login}/locations_stats").mock(
            return_value=Response(200, json=stats[login])
        )


async def test_snapshot_builds_and_ranks(client, users):
    deps._intra_stats = None
    with respx.mock(assert_all_called=False) as mock:
        _intra_mocks(
            mock,
            wallets={"alice": 120, "bob": 500},
            stats={
                "alice": {"2026-11-20": "10:00:00.000000", "2026-11-21": "02:30:00.000000"},
                "bob": {"2026-11-20": "01:00:00.000000"},
            },
        )
        stats = IntraStats(deps.get_settings())
        await stats.refresh_now(["alice", "bob"])
        deps._intra_stats = stats  # the endpoint now reads this snapshot
        body = (await client.get("/students/stats")).json()
    assert body["intra_ready"] is True and body["intra_updated_at"]
    assert [(r["login"], r["value"]) for r in body["wallet"]] == [("bob", 500), ("alice", 120)]
    assert [(r["login"], r["value"]) for r in body["cluster"]] == [
        ("alice", 12 * 3600 + 30 * 60),
        ("bob", 3600),
    ]
    deps._intra_stats = None


async def test_failed_refresh_keeps_previous_snapshot():
    deps._intra_stats = None
    stats = IntraStats(deps.get_settings())
    with respx.mock(assert_all_called=False) as mock:
        _intra_mocks(mock, wallets={"alice": 10}, stats={"alice": {}})
        await stats.refresh_now(["alice"])
    first = stats._snapshot
    assert first is not None and first.wallet == {"alice": 10}
    with respx.mock(assert_all_called=False) as mock:
        mock.post(TOKEN_URL).mock(
            return_value=Response(200, json={"access_token": "t", "expires_in": 7200})
        )
        mock.get(url__startswith=f"{V2}/users/").mock(return_value=Response(500, json={}))
        await stats.refresh_now(["alice"])
    assert stats._snapshot is first  # 42 down → old snapshot kept


async def test_get_triggers_background_refresh_once(monkeypatch):
    stats = IntraStats(deps.get_settings())
    monkeypatch.setattr(stats, "_credentials_present", lambda: True)
    calls: list[list[str]] = []

    async def fake_refresh(logins):
        calls.append(logins)
        await asyncio.sleep(0.05)

    monkeypatch.setattr(stats, "_refresh", fake_refresh)
    assert stats.get(["a"]) is None  # first call: no snapshot yet, refresh started
    assert stats.get(["a"]) is None  # still running: no second task
    await asyncio.sleep(0.1)
    assert calls == [["a"]]


async def test_ranking_ignores_unknown_and_zero(engine, users):
    from app.services import students as svc

    async with get_sessionmaker()() as s:
        alice = await s.get(User, users["alice"].id)
    rows = svc.rank_from_snapshot({"alice": 5, "ghost": 99, "bob": 0}, {"alice": alice})
    assert [(r.login, r.value) for r in rows] == [("alice", 5)]
