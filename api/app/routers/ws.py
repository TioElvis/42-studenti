"""WebSocket endpoint for live Bacheca updates (`GET /ws`).

Authenticated with the same httpOnly session cookie as the REST API, and the
handshake's Origin is checked against the allow-list to prevent cross-site
WebSocket hijacking (CSWSH). The server pushes events; inbound frames are
ignored (we only read to detect disconnects).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..realtime import manager
from ..security import TokenError, decode_access_token

logger = logging.getLogger("app.ws")

router = APIRouter()

# WebSocket close code for policy violations (RFC 6455).
_POLICY_VIOLATION = 1008


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    settings = get_settings()

    # CSWSH protection: reject browser origins outside the allow-list.
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in settings.cors_origins:
        await websocket.close(code=_POLICY_VIOLATION)
        return

    # Auth via the session cookie (deny by default).
    token = websocket.cookies.get(settings.cookie_name)
    if not token:
        await websocket.close(code=_POLICY_VIOLATION)
        return
    try:
        decode_access_token(settings, token)
    except TokenError:
        await websocket.close(code=_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            # We don't act on client messages; this await returns on disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - ensure cleanup on any transport error
        logger.debug("WebSocket closed with error", exc_info=True)
    finally:
        await manager.disconnect(websocket)
