"""Linked-GitHub adapter: OAuth token storage (encrypted) + contributing a
file to the repo's assets/ as a fork-based Pull Request on the student's behalf.

The student's token is Fernet-encrypted at rest (``app/crypto.py``) and never
leaves the backend. Writes are confined by the caller to ``assets/<section>/``.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from .config import Settings
from .crypto import decrypt, encrypt
from .models.user import User

_GITHUB_API = "https://api.github.com"
_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
_UA = "42-studenti"


class GithubAuthRequired(Exception):
    """The student's GitHub token is missing / invalid / lacks permission."""


class GithubApiError(Exception):
    """GitHub rejected an operation (non-auth) or is unreachable."""


# --- token storage ----------------------------------------------------------


def apply_github_token(user: User, *, token: str, username: str) -> None:
    user.github_token_enc = encrypt(token)
    user.github_username = username


def clear_github(user: User) -> None:
    user.github_token_enc = None
    user.github_username = None


def github_token_of(user: User) -> str | None:
    return decrypt(user.github_token_enc) if user.github_token_enc else None


# --- OAuth link flow ---------------------------------------------------------


async def exchange_oauth_code(settings: Settings, code: str) -> str:
    data = {
        "client_id": settings.github_oauth_client_id,
        "client_secret": settings.github_oauth_secret,
        "code": code,
        "redirect_uri": settings.github_oauth_callback_url,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": _UA}) as client:
            resp = await client.post(_OAUTH_TOKEN_URL, data=data, headers={"Accept": "application/json"})
    except httpx.HTTPError as exc:
        raise GithubApiError("GitHub unreachable") from exc
    if resp.status_code != 200:
        raise GithubApiError("GitHub token exchange failed")
    token = resp.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise GithubAuthRequired("GitHub did not return a token")
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "User-Agent": _UA,
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def fetch_github_login(token: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_headers(token)) as client:
            resp = await client.get(f"{_GITHUB_API}/user")
    except httpx.HTTPError as exc:
        raise GithubApiError("GitHub unreachable") from exc
    if resp.status_code in (401, 403):
        raise GithubAuthRequired("GitHub token rejected")
    if resp.status_code != 200:
        raise GithubApiError("Couldn't read GitHub profile")
    login = resp.json().get("login")
    if not isinstance(login, str) or not login:
        raise GithubApiError("GitHub profile has no login")
    return login


# --- contribution flow (fork -> branch -> commit -> PR) ----------------------


async def contribute_via_pr(
    *,
    settings: Settings,
    token: str,
    login: str,
    section: str,
    rel_path: str,
    content_b64: str,
    message: str,
    title: str,
    body: str,
) -> str:
    """Create a fork-based PR adding/updating ``assets/<section>/<rel_path>``.

    Returns the pull request's HTML URL. Uses only the student's token.
    """
    upstream = settings.github_repo
    reponame = upstream.split("/", 1)[1]
    base = settings.github_branch
    full_path = f"assets/{section}/{rel_path}"

    def _auth(resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise GithubAuthRequired("GitHub denied the operation (check access/scope)")

    async with httpx.AsyncClient(
        base_url=_GITHUB_API, timeout=20.0, headers=_headers(token)
    ) as client:
        # 1. Ensure the student has a fork (idempotent).
        fork_resp = await client.post(f"/repos/{upstream}/forks")
        _auth(fork_resp)
        if fork_resp.status_code not in (200, 202):
            raise GithubApiError("Couldn't create your fork")
        fork_full = fork_resp.json().get("full_name") or f"{login}/{reponame}"

        # 2. Wait for the fork to be ready and read the base branch SHA.
        base_sha: str | None = None
        for _ in range(6):
            ref = await client.get(f"/repos/{fork_full}/git/ref/heads/{base}")
            if ref.status_code == 200:
                base_sha = ref.json().get("object", {}).get("sha")
                break
            if ref.status_code not in (404, 409):
                _auth(ref)
                raise GithubApiError("Couldn't read your fork")
            await asyncio.sleep(1.0)
        if not base_sha:
            raise GithubApiError("Your fork isn't ready yet — try again in a moment")

        # 3. Create a working branch on the fork.
        new_branch = f"contrib/{section}-{int(time.time())}"
        mk = await client.post(
            f"/repos/{fork_full}/git/refs",
            json={"ref": f"refs/heads/{new_branch}", "sha": base_sha},
        )
        _auth(mk)
        if mk.status_code not in (200, 201):
            raise GithubApiError("Couldn't create a branch on your fork")

        # 4. If the file already exists on that branch, we need its blob sha.
        existing = await client.get(
            f"/repos/{fork_full}/contents/{full_path}", params={"ref": new_branch}
        )
        sha = existing.json().get("sha") if existing.status_code == 200 else None

        # 5. Commit the file on the fork branch.
        payload: dict[str, object] = {
            "message": message,
            "content": content_b64,
            "branch": new_branch,
        }
        if sha:
            payload["sha"] = sha
        put = await client.put(f"/repos/{fork_full}/contents/{full_path}", json=payload)
        _auth(put)
        if put.status_code not in (200, 201):
            raise GithubApiError("Couldn't commit the file to your fork")

        # 6. Open the PR against the upstream repo.
        pr = await client.post(
            f"/repos/{upstream}/pulls",
            json={"title": title, "head": f"{login}:{new_branch}", "base": base, "body": body},
        )
        _auth(pr)
        if pr.status_code not in (200, 201):
            raise GithubApiError("Couldn't open the pull request")
        url = pr.json().get("html_url")
        if not isinstance(url, str):
            raise GithubApiError("GitHub didn't return a PR link")
        return url
