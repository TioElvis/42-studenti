"""GitHub linking + direct-commit contribution (GitHub API mocked)."""

from __future__ import annotations

import json
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


_CONTENTS = "https://api.github.com/repos/TioElvis/42-studenti/contents/"


def _put_ok(path="assets/material/x.md"):
    return R(
        201,
        json={"content": {"html_url": f"https://github.com/TioElvis/42-studenti/blob/main/{path}"}},
    )


async def test_direct_push_creates_new_file():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=_CONTENTS).mock(return_value=R(404, json={}))
        put = m.put(url__startswith=_CONTENTS).mock(return_value=_put_ok())
        url, action = await github_user.contribute_direct_push(
            settings=s, token="ghp_x", section="material", rel_path="x.md", content_b64="aGk="
        )
    assert action == "created" and "blob/main/assets/material/x.md" in url
    body = json.loads(put.calls.last.request.content)
    assert "sha" not in body and body["message"] == "Add material/x.md" and body["branch"] == "main"


async def test_direct_push_overwrites_existing_with_sha():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=_CONTENTS).mock(return_value=R(200, json={"sha": "oldsha"}))
        put = m.put(url__startswith=_CONTENTS).mock(return_value=R(200, json={}))
        url, action = await github_user.contribute_direct_push(
            settings=s, token="ghp_x", section="material", rel_path="x.md", content_b64="aGk="
        )
    assert action == "updated"
    body = json.loads(put.calls.last.request.content)
    assert body["sha"] == "oldsha" and body["message"] == "Update material/x.md"
    assert url.endswith("blob/main/assets/material/x.md")  # fallback URL


async def test_direct_push_nested_path_and_custom_message():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=_CONTENTS).mock(return_value=R(404, json={}))
        put = m.put(url__startswith=_CONTENTS).mock(return_value=_put_ok())
        await github_user.contribute_direct_push(
            settings=s,
            token="t",
            section="archive",
            rel_path="exam02/ex03/notes.md",
            content_b64="aGk=",
            message="custom",
        )
    assert str(put.calls.last.request.url).endswith("/contents/assets/archive/exam02/ex03/notes.md")
    assert json.loads(put.calls.last.request.content)["message"] == "custom"


async def test_direct_push_requires_write_access():
    s = _settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=_CONTENTS).mock(return_value=R(404, json={}))
        m.put(url__startswith=_CONTENTS).mock(return_value=R(403, json={}))
        with pytest.raises(GithubAuthRequired):
            await github_user.contribute_direct_push(
                settings=s, token="noperm", section="material", rel_path="x.md", content_b64="aGk="
            )


def _server_settings():
    return SimpleNamespace(
        github_repo="TioElvis/42-studenti",
        github_branch="main",
        github_write_token="ghs_servertoken",
    )


async def test_contribute_server_commits_directly_and_attributes_author():
    s = _server_settings()
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=_CONTENTS).mock(return_value=R(404, json={}))
        put = m.put(url__startswith=_CONTENTS).mock(return_value=_put_ok())
        pulls = m.post(url__regex=r".*/(pulls|git/refs)$").mock(return_value=R(500))
        url, action = await github_user.contribute_server(
            settings=s,
            section="material",
            rel_path="x.md",
            content_b64="aGk=",
            author_name="Alice",
            author_login="alice",
        )
    assert action == "created" and "blob/main/assets/material/x.md" in url
    assert not pulls.called  # no PR / branch creation anymore
    req = put.calls.last.request
    assert req.headers["authorization"] == "Bearer ghs_servertoken"
    body = json.loads(req.content)
    assert body["branch"] == "main" and body["author"]["email"] == "alice@users.noreply.github.com"


def test_pr_flow_removed():
    assert not hasattr(github_user, "contribute_via_pr")
    from app.schemas.github import ContributeIn

    assert "mode" not in ContributeIn.model_fields and "title" not in ContributeIn.model_fields


def test_special_users_list():
    from app.config import Settings

    s = Settings(GITHUB_SPECIAL_USERS="alice, Bob")
    assert s.is_special_user("alice") is True
    assert s.is_special_user("BOB") is True
    assert s.is_special_user("carol") is False
    assert Settings(GITHUB_SPECIAL_USERS="").is_special_user("alice") is False
    assert not hasattr(s, "github_archive_allow")  # old variable is gone


async def test_status_and_contribute_unconfigured(client):
    st = (await client.get("/github/status")).json()
    assert st["configured"] is False and st["linked"] is False and st["username"] is None

    resp = await client.post(
        "/github/contribute", json={"section": "material", "path": "x.md", "content": "hi"}
    )
    assert resp.status_code == 503  # no OAuth app / repo configured in tests


# --- POST /github/contribute (server-token mode) ------------------------------


def _server_app_settings(client):
    from app.config import Settings, get_settings

    s = Settings(GITHUB_REPO="TioElvis/42-studenti", GITHUB_WRITE_TOKEN="ghs_tok")
    client._transport.app.dependency_overrides[get_settings] = lambda: s


async def test_contribute_endpoint_created_then_updated(client):
    from app.services import content as content_service

    _server_app_settings(client)
    content_service._gh_tree_cache["material"] = (1e12, object())  # sentinel
    body = {"section": "material", "path": "exam02/ex03/notes.md", "content": "ciao"}
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=_CONTENTS).mock(return_value=R(404, json={}))
        m.put(url__startswith=_CONTENTS).mock(return_value=_put_ok())
        r = await client.post("/github/contribute", json=body)
        assert r.status_code == 200 and r.json()["action"] == "created"
        assert "pr_url" not in r.json() and r.json()["url"].startswith("https://github.com/")
        assert "material" not in content_service._gh_tree_cache  # cache invalidated

        m.get(url__startswith=_CONTENTS).mock(return_value=R(200, json={"sha": "s1"}))
        put = m.put(url__startswith=_CONTENTS).mock(return_value=R(200, json={}))
        r = await client.post("/github/contribute", json=body)
        assert r.json()["action"] == "updated"
        assert json.loads(put.calls.last.request.content)["sha"] == "s1"


@pytest.mark.parametrize(
    "path", ["../x.md", "a\\b.md", "/a.md", "a/", "a//b.md", "a/../b.md", ".hidden"]
)
async def test_contribute_endpoint_rejects_bad_paths(client, path):
    _server_app_settings(client)
    r = await client.post(
        "/github/contribute", json={"section": "material", "path": path, "content": "x"}
    )
    assert r.status_code == 400


async def test_contribute_endpoint_creates_folder_with_gitkeep(client):
    _server_app_settings(client)
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=_CONTENTS).mock(return_value=R(404, json={}))
        put = m.put(url__startswith=_CONTENTS).mock(return_value=_put_ok())
        r = await client.post(
            "/github/contribute",
            json={"section": "material", "path": "exam02/ex03", "create_folder": True},
        )
    assert r.status_code == 200 and r.json()["action"] == "created"
    req = put.calls.last.request
    assert str(req.url).endswith("/contents/assets/material/exam02/ex03/.gitkeep")
    assert json.loads(req.content)["content"] == ""


# --- POST /github/delete -------------------------------------------------------

_API = "https://api.github.com/repos/TioElvis/42-studenti"


def _special_app_settings(client, users="alice"):
    from app.config import Settings, get_settings

    s = Settings(
        GITHUB_REPO="TioElvis/42-studenti", GITHUB_WRITE_TOKEN="ghs_tok", GITHUB_SPECIAL_USERS=users
    )
    client._transport.app.dependency_overrides[get_settings] = lambda: s


async def test_status_exposes_can_delete(client):
    _special_app_settings(client, users="alice")
    assert (await client.get("/github/status")).json()["can_delete"] is True
    _special_app_settings(client, users="bob")
    assert (await client.get("/github/status")).json()["can_delete"] is False


async def test_delete_forbidden_for_non_special_user(client):
    _special_app_settings(client, users="bob")
    with respx.mock(assert_all_called=False) as m:
        any_call = m.route().mock(return_value=R(500))
        r = await client.post("/github/delete", json={"section": "material", "path": "a.md"})
    assert r.status_code == 403 and not any_call.called  # GitHub never touched


async def test_delete_file_uses_sha_and_invalidates_cache(client):
    from app.services import content as content_service

    _special_app_settings(client)
    content_service._gh_tree_cache["archive"] = (1e12, object())
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=f"{_API}/contents/").mock(return_value=R(200, json={"sha": "abc"}))
        d = m.delete(url__startswith=f"{_API}/contents/").mock(
            return_value=R(200, json={"commit": {"html_url": "https://github.com/x/commit/1"}})
        )
        r = await client.post(
            "/github/delete", json={"section": "archive", "path": "exam02/ex03/notes.md"}
        )
    assert r.status_code == 200 and r.json() == {
        "url": "https://github.com/x/commit/1",
        "action": "deleted",
    }
    req = d.calls.last.request
    assert str(req.url).endswith("/contents/assets/archive/exam02/ex03/notes.md")
    body = json.loads(req.content)
    assert body["sha"] == "abc" and body["branch"] == "main"
    assert body["message"] == "Delete archive/exam02/ex03/notes.md"
    assert "archive" not in content_service._gh_tree_cache


async def test_delete_missing_file_404_and_bad_path_400(client):
    _special_app_settings(client)
    with respx.mock(assert_all_called=False) as m:
        m.get(url__startswith=f"{_API}/contents/").mock(return_value=R(404, json={}))
        r = await client.post("/github/delete", json={"section": "material", "path": "nope.md"})
        assert r.status_code == 404
    for bad in ["../x.md", "a\\b", "/a", "a/", "a//b"]:
        r = await client.post("/github/delete", json={"section": "material", "path": bad})
        assert r.status_code == 400


async def test_delete_folder_is_one_commit_via_tree(client):
    _special_app_settings(client)
    tree = {
        "tree": [
            {"path": "assets/material/exam02/a.md", "type": "blob"},
            {"path": "assets/material/exam02/ex03/.gitkeep", "type": "blob"},
            {"path": "assets/material/exam02x/keep.md", "type": "blob"},  # sibling prefix
            {"path": "assets/material/other.md", "type": "blob"},
        ]
    }
    with respx.mock(assert_all_called=False) as m:
        m.get(f"{_API}/git/ref/heads/main").mock(return_value=R(200, json={"object": {"sha": "h1"}}))
        m.get(f"{_API}/git/commits/h1").mock(return_value=R(200, json={"tree": {"sha": "t1"}}))
        m.get(url__startswith=f"{_API}/git/trees/t1").mock(return_value=R(200, json=tree))
        nt = m.post(f"{_API}/git/trees").mock(return_value=R(201, json={"sha": "t2"}))
        nc = m.post(f"{_API}/git/commits").mock(
            return_value=R(201, json={"sha": "c2", "html_url": "https://github.com/x/commit/c2"})
        )
        ref = m.patch(f"{_API}/git/refs/heads/main").mock(return_value=R(200, json={}))
        r = await client.post(
            "/github/delete", json={"section": "material", "path": "exam02", "folder": True}
        )
    assert r.status_code == 200 and r.json()["url"].endswith("/commit/c2")
    entries = json.loads(nt.calls.last.request.content)["tree"]
    assert {e["path"] for e in entries} == {
        "assets/material/exam02/a.md",
        "assets/material/exam02/ex03/.gitkeep",
    }  # exam02x/ and other.md untouched
    assert all(e["sha"] is None for e in entries)
    assert json.loads(nc.calls.last.request.content)["parents"] == ["h1"]
    assert json.loads(ref.calls.last.request.content) == {"sha": "c2"}


async def test_delete_empty_folder_404(client):
    _special_app_settings(client)
    with respx.mock(assert_all_called=False) as m:
        m.get(f"{_API}/git/ref/heads/main").mock(return_value=R(200, json={"object": {"sha": "h1"}}))
        m.get(f"{_API}/git/commits/h1").mock(return_value=R(200, json={"tree": {"sha": "t1"}}))
        m.get(url__startswith=f"{_API}/git/trees/t1").mock(return_value=R(200, json={"tree": []}))
        r = await client.post(
            "/github/delete", json={"section": "material", "path": "ghost", "folder": True}
        )
    assert r.status_code == 404
