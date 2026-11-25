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


# --- deletion (special users only; enforced by the router) -------------------


def _author_of(login: str, name: str | None) -> dict[str, str]:
    return {"name": name or login, "email": f"{login}@users.noreply.github.com"}


async def _delete_file(
    client: httpx.AsyncClient,
    *,
    upstream: str,
    base: str,
    section: str,
    rel_path: str,
    message: str | None,
    author: dict[str, str] | None,
) -> str:
    """Delete one file via the Contents API (needs its blob sha). Returns the
    commit URL. Raises ``FileNotFoundError`` if it doesn't exist."""
    full_path = f"assets/{section}/{rel_path}"
    existing = await client.get(f"/repos/{upstream}/contents/{full_path}", params={"ref": base})
    if existing.status_code in (401, 403):
        raise GithubAuthRequired("No write access to the repo")
    body = existing.json() if existing.status_code == 200 else None
    if not isinstance(body, dict) or not body.get("sha"):
        raise FileNotFoundError(rel_path)
    payload: dict[str, object] = {
        "message": message or f"Delete {section}/{rel_path}",
        "sha": body["sha"],
        "branch": base,
    }
    if author:
        payload["author"] = author
        payload["committer"] = author
    resp = await client.request("DELETE", f"/repos/{upstream}/contents/{full_path}", json=payload)
    if resp.status_code in (401, 403):
        raise GithubAuthRequired("Serve accesso in scrittura al repository")
    if resp.status_code != 200:
        raise GithubApiError("Couldn't delete the file")
    commit = (resp.json().get("commit") or {}) if resp.content else {}
    return commit.get("html_url") or f"https://github.com/{upstream}/commits/{base}"


async def _delete_folder(
    client: httpx.AsyncClient,
    *,
    upstream: str,
    base: str,
    section: str,
    rel_path: str,
    message: str | None,
    author: dict[str, str] | None,
) -> str:
    """Delete a whole folder in ONE commit through the Git Data API: build a
    tree that nulls every blob under the prefix. Metadata only — no file bytes
    are downloaded. Raises ``FileNotFoundError`` if the folder is empty/absent."""
    prefix = f"assets/{section}/{rel_path}/"

    def _auth(resp: httpx.Response) -> None:
        if resp.status_code in (401, 403):
            raise GithubAuthRequired("No write access to the repo")

    ref = await client.get(f"/repos/{upstream}/git/ref/heads/{base}")
    _auth(ref)
    if ref.status_code != 200:
        raise GithubApiError("Couldn't read the base branch")
    head_sha = ref.json().get("object", {}).get("sha")

    commit = await client.get(f"/repos/{upstream}/git/commits/{head_sha}")
    _auth(commit)
    if commit.status_code != 200:
        raise GithubApiError("Couldn't read the base commit")
    base_tree = commit.json().get("tree", {}).get("sha")

    tree = await client.get(f"/repos/{upstream}/git/trees/{base_tree}", params={"recursive": "1"})
    _auth(tree)
    if tree.status_code != 200:
        raise GithubApiError("Couldn't read the repository tree")
    data = tree.json()
    if data.get("truncated"):
        raise GithubApiError("Repository too large to delete a folder safely")
    entries = [
        {"path": it["path"], "mode": "100644", "type": "blob", "sha": None}
        for it in data.get("tree") or []
        if it.get("type") == "blob" and str(it.get("path", "")).startswith(prefix)
    ]
    if not entries:
        raise FileNotFoundError(rel_path)

    new_tree = await client.post(
        f"/repos/{upstream}/git/trees", json={"base_tree": base_tree, "tree": entries}
    )
    _auth(new_tree)
    if new_tree.status_code not in (200, 201):
        raise GithubApiError("Couldn't build the new tree")

    payload: dict[str, object] = {
        "message": message or f"Delete folder {section}/{rel_path}",
        "tree": new_tree.json().get("sha"),
        "parents": [head_sha],
    }
    if author:
        payload["author"] = author
        payload["committer"] = author
    new_commit = await client.post(f"/repos/{upstream}/git/commits", json=payload)
    _auth(new_commit)
    if new_commit.status_code not in (200, 201):
        raise GithubApiError("Couldn't create the commit")
    new_sha = new_commit.json().get("sha")

    upd = await client.patch(f"/repos/{upstream}/git/refs/heads/{base}", json={"sha": new_sha})
    _auth(upd)
    if upd.status_code != 200:
        raise GithubApiError("Couldn't update the branch")
    return new_commit.json().get("html_url") or f"https://github.com/{upstream}/commit/{new_sha}"


async def delete_path(
    *,
    settings: Settings,
    token: str | None,
    section: str,
    rel_path: str,
    folder: bool,
    message: str | None = None,
    author_login: str | None = None,
    author_name: str | None = None,
) -> str:
    """Delete a file or folder with the server token (when ``token`` is None and
    server mode is on) or the student's own token. Returns the commit URL."""
    server = token is None
    bearer = settings.github_write_token if server else token
    author = _author_of(author_login, author_name) if server and author_login else None
    fn = _delete_folder if folder else _delete_file
    async with httpx.AsyncClient(
        base_url=_GITHUB_API, timeout=30.0, headers=_headers(bearer or "")
    ) as client:
        return await fn(
            client,
            upstream=settings.github_repo,
            base=settings.github_branch,
            section=section,
            rel_path=rel_path,
            message=message,
            author=author,
        )
