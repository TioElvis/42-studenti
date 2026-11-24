"""GitHub linking + fork-based PR contribution (GitHub API mocked)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import respx
from httpx import Response as R

from app import github_user
from app.github_user import GithubAuthRequired
from app.models.user import User


def _settings():
    return SimpleNamespace(
        github_repo="TioElvis/42-studenti",
        github_branch="main",
        github_oauth_client_id="cid",
        github_oauth_secret="sec",
        github_oauth_callback_url="http://localhost:9000/github/link/callback",
    )


def test_token_store_roundtrip():
    u = User(intra_id=9, login="x")
    github_user.apply_github_token(u, token="ghp_abc", username="octocat")
    assert u.github_username == "octocat"
    assert u.github_token_enc and u.github_token_enc != "ghp_abc"  # encrypted at rest
    assert github_user.github_token_of(u) == "ghp_abc"
    github_user.clear_github(u)
    assert u.github_username is None and u.github_token_enc is None
    assert github_user.github_token_of(u) is None


async def test_oauth_exchange_and_login():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.post("https://github.com/login/oauth/access_token").mock(
            return_value=R(200, json={"access_token": "ghp_x"})
        )
        m.get("https://api.github.com/user").mock(return_value=R(200, json={"login": "octocat"}))
        token = await github_user.exchange_oauth_code(s, "code123")
        assert token == "ghp_x"
        assert await github_user.fetch_github_login(token) == "octocat"


async def test_contribute_via_fork_pr():
    """Non-collaborator: no push access -> fork + PR."""
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get("https://api.github.com/repos/TioElvis/42-studenti").mock(
            return_value=R(200, json={"permissions": {"push": False}})
        )
        m.post("https://api.github.com/repos/TioElvis/42-studenti/forks").mock(
            return_value=R(202, json={"full_name": "octocat/42-studenti"})
        )
        m.get("https://api.github.com/repos/octocat/42-studenti/git/ref/heads/main").mock(
            return_value=R(200, json={"object": {"sha": "base123"}})
        )
        m.post("https://api.github.com/repos/octocat/42-studenti/git/refs").mock(
            return_value=R(201, json={})
        )
        m.get(
            url__startswith="https://api.github.com/repos/octocat/42-studenti/contents/"
        ).mock(return_value=R(404, json={}))
        m.put(
            url__startswith="https://api.github.com/repos/octocat/42-studenti/contents/"
        ).mock(return_value=R(201, json={}))
        m.post("https://api.github.com/repos/TioElvis/42-studenti/pulls").mock(
            return_value=R(201, json={"html_url": "https://github.com/TioElvis/42-studenti/pull/7"})
        )
        url = await github_user.contribute_via_pr(
            settings=s,
            token="ghp_x",
            login="octocat",
            section="material",
            rel_path="exam03/notes.md",
            content_b64="aGk=",
            message="m",
            title="t",
            body="b",
        )
    assert url.endswith("/pull/7")


async def test_contribute_direct_push_when_owner():
    """Owner / collaborator: push access -> branch on upstream, no fork."""
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get("https://api.github.com/repos/TioElvis/42-studenti").mock(
            return_value=R(200, json={"permissions": {"push": True}})
        )
        m.get("https://api.github.com/repos/TioElvis/42-studenti/git/ref/heads/main").mock(
            return_value=R(200, json={"object": {"sha": "base999"}})
        )
        m.post("https://api.github.com/repos/TioElvis/42-studenti/git/refs").mock(
            return_value=R(201, json={})
        )
        m.get(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(404, json={}))
        m.put(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(201, json={}))
        pulls = m.post("https://api.github.com/repos/TioElvis/42-studenti/pulls").mock(
            return_value=R(201, json={"html_url": "https://github.com/TioElvis/42-studenti/pull/9"})
        )
        url = await github_user.contribute_via_pr(
            settings=s,
            token="ghp_owner",
            login="TioElvis",
            section="archive",
            rel_path="recap.md",
            content_b64="aGk=",
            message="m",
            title="t",
            body="b",
        )
    assert url.endswith("/pull/9")
    # No fork was attempted; PR head is same-repo owner:branch.
    assert pulls.calls.last.request.content  # a PR was opened


async def test_contribute_auth_required_on_403():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get("https://api.github.com/repos/TioElvis/42-studenti").mock(
            return_value=R(403, json={})
        )
        with pytest.raises(GithubAuthRequired):
            await github_user.contribute_via_pr(
                settings=s,
                token="bad",
                login="octocat",
                section="material",
                rel_path="x.md",
                content_b64="aGk=",
                message="m",
                title="t",
                body="b",
            )


async def test_direct_push_commits_to_base():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(404, json={}))
        m.put(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(
            return_value=R(
                201,
                json={
                    "content": {
                        "html_url": "https://github.com/TioElvis/42-studenti/blob/main/assets/material/x.md"
                    }
                },
            )
        )
        url = await github_user.contribute_direct_push(
            settings=s,
            token="ghp_x",
            section="material",
            rel_path="x.md",
            content_b64="aGk=",
            message="m",
        )
    assert "blob/main/assets/material/x.md" in url


async def test_direct_push_requires_write_access():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(404, json={}))
        m.put(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(403, json={}))
        with pytest.raises(GithubAuthRequired):
            await github_user.contribute_direct_push(
                settings=s,
                token="noperm",
                section="material",
                rel_path="x.md",
                content_b64="aGk=",
                message="m",
            )


def _server_settings():
    return SimpleNamespace(
        github_repo="TioElvis/42-studenti",
        github_branch="main",
        github_write_token="ghs_servertoken",
    )


async def test_contribute_server_push():
    s = _server_settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(404, json={}))
        m.put(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(
            return_value=R(
                201,
                json={
                    "content": {
                        "html_url": "https://github.com/TioElvis/42-studenti/blob/main/assets/material/x.md"
                    }
                },
            )
        )
        url = await github_user.contribute_server(
            settings=s,
            mode="push",
            section="material",
            rel_path="x.md",
            content_b64="aGk=",
            message="m",
            title="t",
            body="b",
            author_name="Alice",
            author_login="alice",
        )
    assert "blob/main/assets/material/x.md" in url


async def test_contribute_server_pr():
    s = _server_settings()
    with respx.mock(assert_all_called=False) as m:
        m.get("https://api.github.com/repos/TioElvis/42-studenti/git/ref/heads/main").mock(
            return_value=R(200, json={"object": {"sha": "s1"}})
        )
        m.post("https://api.github.com/repos/TioElvis/42-studenti/git/refs").mock(
            return_value=R(201, json={})
        )
        m.get(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(404, json={}))
        m.put(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/contents/"
        ).mock(return_value=R(201, json={}))
        m.post("https://api.github.com/repos/TioElvis/42-studenti/pulls").mock(
            return_value=R(201, json={"html_url": "https://github.com/TioElvis/42-studenti/pull/12"})
        )
        url = await github_user.contribute_server(
            settings=s,
            mode="pr",
            section="archive",
            rel_path="recap.md",
            content_b64="aGk=",
            message="m",
            title="t",
            body="b",
            author_name="Alice",
            author_login="alice",
        )
    assert url.endswith("/pull/12")


def test_archive_allow_list():
    from app.config import Settings

    s = Settings(GITHUB_ARCHIVE_ALLOW="alice, Bob")
    assert s.can_contribute_archive("alice") is True
    assert s.can_contribute_archive("BOB") is True
    assert s.can_contribute_archive("carol") is False
    assert Settings(GITHUB_ARCHIVE_ALLOW="").can_contribute_archive("alice") is False


async def test_status_and_contribute_unconfigured(client):
    st = (await client.get("/github/status")).json()
    assert st["configured"] is False and st["linked"] is False and st["username"] is None

    resp = await client.post(
        "/github/contribute", json={"section": "material", "path": "x.md", "content": "hi"}
    )
    assert resp.status_code == 503  # no OAuth app / repo configured in tests
