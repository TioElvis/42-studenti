"""Realtime layer: connection-manager fan-out and WebSocket auth gate."""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app
from app.realtime import ConnectionManager


class _StubSocket:
    """Minimal stand-in for a Starlette WebSocket that records sent frames."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


async def test_manager_broadcasts_to_all_connected():
    manager = ConnectionManager()
    a, b = _StubSocket(), _StubSocket()
    await manager.connect(a)
    await manager.connect(b)

    await manager.broadcast("post.created", {"id": 7})

    for sock in (a, b):
        assert sock.accepted
        assert len(sock.sent) == 1
        msg = json.loads(sock.sent[0])
        assert msg == {"type": "post.created", "data": {"id": 7}}


async def test_manager_prunes_dead_sockets():
    manager = ConnectionManager()

    class _Broken(_StubSocket):
        async def send_text(self, text: str) -> None:
            raise RuntimeError("socket closed")

    good, bad = _StubSocket(), _Broken()
    await manager.connect(good)
    await manager.connect(bad)

    await manager.broadcast("post.deleted", {"id": 1})  # must not raise
    # The broken socket is dropped; a second broadcast only reaches the good one.
    await manager.broadcast("post.deleted", {"id": 2})
    assert len(good.sent) == 2


def test_ws_rejects_unauthenticated():
    # No cookie on the handshake -> server closes with a policy violation.
    client = TestClient(create_app())
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws"):
            pass
