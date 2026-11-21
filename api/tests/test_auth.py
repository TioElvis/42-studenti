"""42 OAuth login flow (token + /me mocked with respx)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import create_app

ME_PAYLOAD = {
    "id": 2001,
    "login": "rspqr",
    "email": "rspqr@student.42roma.it",
    "displayname": "Romolo SPQR",
    "image": {"link": "https://cdn.intra.42.fr/users/rspqr.jpg"},
    "campus": [{"id": 61, "name": "Rome"}, {"id": 1, "name": "Paris"}],
    "campus_users": [{"campus_id": 61, "is_primary": True}],
}


async def test_full_login_flow_sets_cookie_and_creates_user(engine):
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # 1) Start the flow: grab the CSRF state (from the redirect) + state cookie.
        start = await c.get("/auth/42", follow_redirects=False)
        assert start.status_code == 302
        state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
        assert c.cookies.get("oauth_state") == state

        # 2) Mock 42's token + /me endpoints.
        with respx.mock(assert_all_called=True) as mock:
            mock.post("https://api.intra.42.fr/oauth/token").mock(
                return_value=Response(200, json={"access_token": "intra-token-xyz"})
            )
            mock.get("https://api.intra.42.fr/v2/me").mock(
                return_value=Response(200, json=ME_PAYLOAD)
            )
            cb = await c.get(
                "/auth/42/callback",
                params={"code": "auth-code-123", "state": state},
                follow_redirects=False,
            )
        assert cb.status_code == 302
        assert cb.headers["location"] == "http://localhost:3000"
        assert c.cookies.get("access_token")

        # 3) The session cookie now authenticates /me with the real dependency.
        me = await c.get("/me")
        assert me.status_code == 200
        body = me.json()
        assert body["login"] == "rspqr"
        assert body["campus"] == "Rome"
        assert body["avatar_url"].endswith("rspqr.jpg")


async def test_callback_rejects_bad_state(engine):
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        await c.get("/auth/42", follow_redirects=False)  # sets a state cookie
        cb = await c.get(
            "/auth/42/callback",
            params={"code": "x", "state": "forged-state"},
            follow_redirects=False,
        )
        assert cb.status_code == 302
        assert "auth_error=state" in cb.headers["location"]
        assert not c.cookies.get("access_token")
