"""In-process WebSocket fan-out for live Bacheca updates.

A single :class:`ConnectionManager` keeps the set of open sockets and broadcasts
JSON events to all of them. Routers publish events after a successful mutation
(presentation concern), so the service layer stays transport-agnostic.

This is a single-process broadcaster. For multi-worker / horizontal scaling,
swap it for a shared pub/sub (e.g. Redis) behind the same `broadcast` call.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("app.realtime")


class ConnectionManager:
    def __init__(self) -> None:
        self._active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._active.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._active.discard(websocket)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send one event to every connected client; prune dead sockets."""
        payload = json.dumps({"type": event_type, "data": data}, default=str)
        async with self._lock:
            targets = list(self._active)
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001 - any send failure means the socket is gone
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._active.discard(ws)


# Process-wide singleton used by the routers.
manager = ConnectionManager()
