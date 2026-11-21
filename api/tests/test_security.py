"""JWT round-trip and auth-gate unit tests."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.security import TokenError, create_access_token, decode_access_token


def test_jwt_roundtrip():
    settings = get_settings()
    token = create_access_token(settings, user_id=42, login="jdoe")
    assert decode_access_token(settings, token) == 42


def test_jwt_rejects_tampered_token():
    settings = get_settings()
    token = create_access_token(settings, user_id=42, login="jdoe")
    with pytest.raises(TokenError):
        decode_access_token(settings, token + "tamper")


def test_jwt_rejects_wrong_secret():
    settings = get_settings()
    token = create_access_token(settings, user_id=1, login="x")
    # Decoding with a different secret must fail (signature check).
    from app.config import Settings

    other = Settings(JWT_SECRET="a-totally-different-secret-value-here-123456")
    with pytest.raises(TokenError):
        decode_access_token(other, token)


async def test_protected_endpoint_requires_auth(engine):
    # A fresh app with NO auth override -> /me must 401 without a cookie.
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/me")
    assert resp.status_code == 401
