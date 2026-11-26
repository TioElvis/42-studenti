"""Web Push: subscriptions (validation, ownership) and delivery."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pywebpush import WebPushException
from sqlalchemy import select

from app.config import get_settings
from app.database import get_sessionmaker
from app.deps import get_current_user
from app.models import PushSubscription, User
from app.services import push as push_service

ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"


def _body(endpoint: str = ENDPOINT, lang: str = "it") -> dict:
    return {"endpoint": endpoint, "keys": {"p256dh": "B" * 87, "auth": "a" * 22}, "lang": lang}


async def _subscriptions() -> list[PushSubscription]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(PushSubscription).order_by(PushSubscription.id)))


@pytest.fixture
def push_on(monkeypatch):
    """Configure VAPID and capture sends instead of calling a push service."""
    settings = get_settings()
    monkeypatch.setattr(settings, "vapid_public_key", "public")
    monkeypatch.setattr(settings, "vapid_private_key", "private")
    monkeypatch.setattr(settings, "vapid_subject", "mailto:test@example.org")
    sent: list[tuple[str, dict]] = []

    def _fake(_settings, subscription, payload):
        sent.append((subscription["endpoint"], json.loads(payload)))

    monkeypatch.setattr(push_service, "_send", _fake)
    return sent


async def test_key_is_null_when_not_configured(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "vapid_private_key", "")
    r = await client.get("/notifications/push/key")
    assert r.json() == {"public_key": None}


async def test_key_when_configured(client, push_on):
    r = await client.get("/notifications/push/key")
    assert r.json() == {"public_key": "public"}


async def test_key_is_null_with_invalid_subject(client, push_on, monkeypatch):
    monkeypatch.setattr(get_settings(), "vapid_subject", "http://localhost:3000")
    r = await client.get("/notifications/push/key")
    assert r.json() == {"public_key": None}


async def test_subscribe_requires_auth(client):
    client._transport.app.dependency_overrides.pop(get_current_user)
    r = await client.post("/notifications/push/subscribe", json=_body())
    assert r.status_code == 401


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/x",
        "https://localhost/x",
        "https://169.254.169.254/latest",
        "https://evil.example/x",
        "https://fcm.googleapis.com.evil.example/x",
        "https://user@fcm.googleapis.com/x",
        "https://evil.example@a.push.apple.com/x",
        "https://fcm.googleapis.com:8443/x",
        "https://evil.example\\@a.push.apple.com/x",
    ],
)
async def test_rejects_untrusted_endpoints(client, endpoint):
    r = await client.post("/notifications/push/subscribe", json=_body(endpoint))
    assert r.status_code == 422
    assert await _subscriptions() == []


@pytest.mark.parametrize(
    "endpoint",
    [
        ENDPOINT,
        "https://updates.push.services.mozilla.com/wpush/v2/x",
        "https://wns2-par02p.notify.windows.com/w/?token=x",
        "https://web.push.apple.com/x",
    ],
)
async def test_accepts_browser_push_services(client, endpoint):
    r = await client.post("/notifications/push/subscribe", json=_body(endpoint))
    assert r.status_code == 204


async def test_resubscribe_updates_and_moves_owner(client, users):
    await client.post("/notifications/push/subscribe", json=_body())
    client.auth_ctx.current = users["bob"]
    await client.post("/notifications/push/subscribe", json=_body(lang="en"))
    subs = await _subscriptions()
    assert [(s.user_id, s.lang) for s in subs] == [(users["bob"].id, "en")]


async def test_oldest_subscriptions_are_dropped(client):
    for i in range(push_service.MAX_SUBSCRIPTIONS_PER_USER + 2):
        await client.post("/notifications/push/subscribe", json=_body(f"{ENDPOINT}-{i}"))
    subs = await _subscriptions()
    assert len(subs) == push_service.MAX_SUBSCRIPTIONS_PER_USER
    assert subs[0].endpoint == f"{ENDPOINT}-2"


async def test_unsubscribe_only_own(client, users):
    await client.post("/notifications/push/subscribe", json=_body())
    client.auth_ctx.current = users["bob"]
    await client.post("/notifications/push/unsubscribe", json={"endpoint": ENDPOINT})
    assert len(await _subscriptions()) == 1
    client.auth_ctx.current = users["alice"]
    await client.post("/notifications/push/unsubscribe", json={"endpoint": ENDPOINT})
    assert await _subscriptions() == []


async def test_follow_pushes_to_followee_only(client, users, push_on):
    client.auth_ctx.current = users["bob"]
    await client.post("/notifications/push/subscribe", json=_body(lang="en"))
    client.auth_ctx.current = users["alice"]
    await client.post("/notifications/push/subscribe", json=_body(f"{ENDPOINT}-alice"))

    assert (await client.post("/users/bob/follow")).status_code == 204

    assert len(push_on) == 1
    endpoint, payload = push_on[0]
    assert endpoint == ENDPOINT
    assert payload["body"] == "@alice started following you"
    assert payload["url"] == "/u/alice"


async def test_disabled_setting_means_no_push(client, users, push_on):
    client.auth_ctx.current = users["bob"]
    await client.post("/notifications/push/subscribe", json=_body())
    async with get_sessionmaker()() as session:
        (await session.get(User, users["bob"].id)).notify_follows = False
        await session.commit()
    client.auth_ctx.current = users["alice"]
    await client.post("/users/bob/follow")
    assert push_on == []


@pytest.mark.parametrize(("status_code", "remaining"), [(410, 0), (404, 0), (500, 1)])
async def test_gone_subscriptions_are_deleted(
    client, users, push_on, monkeypatch, status_code, remaining
):
    def _fail(*_args):
        raise WebPushException("nope", response=SimpleNamespace(status_code=status_code))

    monkeypatch.setattr(push_service, "_send", _fail)
    client.auth_ctx.current = users["bob"]
    await client.post("/notifications/push/subscribe", json=_body())
    client.auth_ctx.current = users["alice"]
    assert (await client.post("/users/bob/follow")).status_code == 204
    assert len(await _subscriptions()) == remaining
