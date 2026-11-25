"""Linked-GitHub adapter: OAuth token storage (encrypted) + contributing a
file straight to the repo's assets/ (direct commit, no PRs) on the student's behalf.

The student's token is Fernet-encrypted at rest (``app/crypto.py``) and never
leaves the backend. Writes are confined by the caller to ``assets/<section>/``.
"""

from __future__ import annotations

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


async def _commit_file(
    client: httpx.AsyncClient,
    *,
    upstream: str,
    base: str,
    section: str,
    rel_path: str,
    content_b64: str,
    message: str | None,
    author: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Commit ``assets/<section>/<rel_path>`` straight to ``base``.

    GETs the file first: if it exists its blob sha goes in the PUT so GitHub
    overwrites it (no 422). Returns ``(url, action)`` with action
    ``"created"`` or ``"updated"``. ``message=None`` → "Add/Update <path>".
    """
    full_path = f"assets/{section}/{rel_path}"
    existing = await client.get(f"/repos/{upstream}/contents/{full_path}", params={"ref": base})
    if existing.status_code in (401, 403):
        raise GithubAuthRequired("No write access to the repo")
    sha = None
    if existing.status_code == 200:
        body = existing.json()
        sha = body.get("sha") if isinstance(body, dict) else None
    action = "updated" if sha else "created"

    payload: dict[str, object] = {
        "message": message or f"{'Update' if sha else 'Add'} {section}/{rel_path}",
        "content": content_b64,
        "branch": base,
    }
    if sha:
        payload["sha"] = sha
    if author:
        payload["author"] = author
        payload["committer"] = author
    put = await client.put(f"/repos/{upstream}/contents/{full_path}", json=payload)
    if put.status_code in (401, 403):
        raise GithubAuthRequired("Serve accesso in scrittura al repository")
    if put.status_code not in (200, 201):
        raise GithubApiError("Couldn't commit the file")
    data = put.json()
    url = (data.get("content") or {}).get("html_url") or (
        (data.get("commit") or {}).get("html_url")
    )
    return url or f"https://github.com/{upstream}/blob/{base}/{full_path}", action


async def contribute_direct_push(
    *,
    settings: Settings,
    token: str,
    section: str,
    rel_path: str,
    content_b64: str,
    message: str | None = None,
) -> tuple[str, str]:
    """Commit with the student's own token (needs repo write access)."""
    async with httpx.AsyncClient(
        base_url=_GITHUB_API, timeout=20.0, headers=_headers(token)
    ) as client:
        return await _commit_file(
            client,
            upstream=settings.github_repo,
            base=settings.github_branch,
            section=section,
            rel_path=rel_path,
            content_b64=content_b64,
            message=message,
        )


async def contribute_server(
    *,
    settings: Settings,
    section: str,
    rel_path: str,
    content_b64: str,
    message: str | None = None,
    author_name: str,
    author_login: str,
) -> tuple[str, str]:
    """Commit with the backend's own write token (private repo), attributed to
    the student via the author/committer fields."""
    author = {
        "name": author_name or author_login,
        "email": f"{author_login}@users.noreply.github.com",
    }
    async with httpx.AsyncClient(
        base_url=_GITHUB_API, timeout=20.0, headers=_headers(settings.github_write_token)
    ) as client:
        return await _commit_file(
            client,
            upstream=settings.github_repo,
            base=settings.github_branch,
            section=section,
            rel_path=rel_path,
            content_b64=content_b64,
            message=message,
            author=author,
        )
