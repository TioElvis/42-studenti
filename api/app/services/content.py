"""File-based content for Materiale / Archivio.

Content lives ONLY on GitHub under ``assets/material/**`` and
``assets/archive/**``. The server never mirrors it to disk: listings use the Git
Trees API (metadata only: path, size, sha) and file bytes are proxied through
memory on demand (the repo is private, so browsers can't hit raw URLs). Paths
are confined to the section root — no traversal.
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import quote
from dataclasses import dataclass

import httpx

from ..config import Settings
from ..schemas.content import ContentEntry, ContentFile, ContentList
from .exceptions import ContentUnavailableError, NotFoundError

# Section name -> subfolder under assets/. Allow-list; nothing else is reachable.
SECTIONS: dict[str, str] = {"material": "material", "archive": "archive"}

# Extensions returned as inline text (via ``read_file``).
_TEXT_EXT = {".md", ".markdown", ".txt", ".csv", ".json", ".yml", ".yaml", ".log"}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

_MIME: dict[str, str] = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".yml": "text/yaml",
    ".yaml": "text/yaml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".zip": "application/zip",
}

_MAX_TEXT_BYTES = 512 * 1024  # 512 KiB cap on an inline text document
_MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MiB cap on a streamed file


def _mime_for(suffix: str) -> str:
    return _MIME.get(suffix, "application/octet-stream")


def _kind_for(suffix: str) -> str:
    if suffix in _TEXT_EXT:
        return "text"
    if suffix in _IMAGE_EXT:
        return "image"
    if suffix == ".pdf":
        return "pdf"
    return "other"


# ---------------------------------------------------------------------------
# GitHub-backed source: read content live from the repo's assets/ so a push
# updates the site without a redeploy. A GitHub outage raises
# ContentUnavailableError (502); a genuine 404 raises NotFoundError.
# ---------------------------------------------------------------------------

_KEEP = ".gitkeep"  # placeholder committed to create an empty folder
_GITHUB_API = "https://api.github.com"
_GITHUB_RAW = "https://raw.githubusercontent.com"
_GH_UA = "42-studenti"  # GitHub requires a User-Agent; generic app name, no PII.


@dataclass
class FilePayload:
    """A file to stream: in-memory bytes fetched from GitHub (never on disk)."""

    name: str
    media_type: str
    data: bytes


class _GitHubUnavailable(Exception):
    """GitHub couldn't be reached / returned an unexpected status → fall back."""


# Per-section tree-listing cache (TTL). File bytes come from raw.* (uncached
# here; the browser caches them via Cache-Control).
_gh_tree_cache: dict[str, tuple[float, ContentList]] = {}
_gh_lock = asyncio.Lock()


def invalidate_github_cache(section: str | None = None) -> None:
    """Drop the cached listing (used after a commit so it shows at once)."""
    if section is None:
        _gh_tree_cache.clear()
    else:
        _gh_tree_cache.pop(section, None)


def _github_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "github_repo", ""))


def _suffix_of(name: str) -> str:
    return f".{name.rsplit('.', 1)[-1].lower()}" if "." in name else ""


def _validate_segments(rel: str) -> str:
    """Strict relative-path check: no empty/``..``/dot segments, no backslash,
    no leading or trailing slash."""
    if not rel or rel != rel.strip() or "\\" in rel or "\x00" in rel:
        raise NotFoundError("File not found")
    if rel.startswith("/") or rel.endswith("/"):
        raise NotFoundError("File not found")
    segments = rel.split("/")
    for seg in segments:
        if seg in ("", ".", "..") or seg.startswith("."):
            raise NotFoundError("File not found")
    return rel


def _safe_rel(rel: str) -> str:
    """Confine a GitHub-bound file path to the section (no traversal)."""
    return _validate_segments(rel)


def confine_rel(rel: str) -> str:
    """Public: validate a relative file path stays under the section."""
    return _safe_rel(rel)


def confine_folder(folder: str) -> str:
    """Public: validate a (possibly nested) folder path, e.g. ``exam02/ex03``."""
    return _validate_segments(folder)


def keep_path(folder: str) -> str:
    """The placeholder file that materializes an empty folder on GitHub."""
    return f"{confine_folder(folder)}/{_KEEP}"


def section_allowed(section: str) -> bool:
    return section in SECTIONS


def _gh_headers(settings: Settings, *, api: bool) -> dict[str, str]:
    headers = {"User-Agent": _GH_UA}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    # A server token lets us read a PRIVATE repo (public repos work without it).
    token = getattr(settings, "github_write_token", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _gh_listing(settings: Settings, section: str) -> ContentList:
    ttl = getattr(settings, "github_cache_ttl", 300)
    cached = _gh_tree_cache.get(section)
    if cached and time.monotonic() - cached[0] < ttl:
        return cached[1]
    async with _gh_lock:
        cached = _gh_tree_cache.get(section)
        if cached and time.monotonic() - cached[0] < ttl:
            return cached[1]
        repo = settings.github_repo
        branch = getattr(settings, "github_branch", "main")
        url = f"{_GITHUB_API}/repos/{repo}/git/trees/{branch}?recursive=1"
        try:
            async with httpx.AsyncClient(
                timeout=10.0, headers=_gh_headers(settings, api=True)
            ) as client:
                resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise _GitHubUnavailable() from exc
        if resp.status_code != 200:
            raise _GitHubUnavailable()
        prefix = f"assets/{SECTIONS[section]}/"
        entries: list[ContentEntry] = []
        folders: set[str] = set()
        blob_base = f"https://github.com/{repo}/blob/{branch}/{prefix}"
        raw_base = f"{_GITHUB_RAW}/{repo}/{branch}/{prefix}"
        for item in resp.json().get("tree") or []:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if not path.startswith(prefix):
                continue
            rel = path[len(prefix):]
            segments = rel.split("/")
            if not rel or any(seg in ("", "..") for seg in segments):
                continue
            name = segments[-1]
            parent = segments[:-1]
            if any(seg.startswith(".") for seg in parent):
                continue
            # Every ancestor is a visible folder (even if it only holds .gitkeep).
            for i in range(1, len(parent) + 1):
                folders.add("/".join(parent[:i]))
            if name.startswith("."):  # .gitkeep & friends: folder marker only
                continue
            suffix = _suffix_of(name)
            entries.append(
                ContentEntry(
                    path=rel,
                    name=name,
                    folder="/".join(parent),
                    size=int(item.get("size") or 0),
                    kind=_kind_for(suffix),
                    mime=_mime_for(suffix),
                    sha=str(item.get("sha") or ""),
                    github_url=blob_base + quote(rel),
                    raw_url=raw_base + quote(rel),
                )
            )
        entries.sort(key=lambda e: e.path)
        result = ContentList(section=section, entries=entries, folders=sorted(folders))
        _gh_tree_cache[section] = (time.monotonic(), result)
        return result


async def _gh_fetch_raw(settings: Settings, section: str, rel: str) -> bytes:
    repo = settings.github_repo
    branch = getattr(settings, "github_branch", "main")
    full = f"assets/{SECTIONS[section]}/{rel}"
    token = getattr(settings, "github_write_token", "")
    # Private repo → the Contents API with the token (raw.* needs no auth only
    # for public repos). The "raw" media type returns the file bytes directly.
    if token:
        url = f"{_GITHUB_API}/repos/{repo}/contents/{full}"
        headers = {
            "User-Agent": _GH_UA,
            "Accept": "application/vnd.github.raw",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {token}",
        }
        params = {"ref": branch}
    else:
        url = f"{_GITHUB_RAW}/{repo}/{branch}/{full}"
        headers = {"User-Agent": _GH_UA}
        params = {}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        raise _GitHubUnavailable() from exc
    if resp.status_code == 404:
        raise NotFoundError("File not found")
    if resp.status_code != 200:
        raise _GitHubUnavailable()
    return resp.content


async def _gh_text(settings: Settings, section: str, rel: str) -> ContentFile:
    safe = _safe_rel(rel)
    if _suffix_of(safe.rsplit("/", 1)[-1]) not in _TEXT_EXT:
        raise NotFoundError("This file type can't be shown as text")
    data = await _gh_fetch_raw(settings, section, safe)
    if len(data) > _MAX_TEXT_BYTES:
        raise NotFoundError("File too large to display")
    return ContentFile(
        path=safe, name=safe.rsplit("/", 1)[-1], content=data.decode("utf-8", errors="replace")
    )


async def _gh_file(settings: Settings, section: str, rel: str) -> FilePayload:
    safe = _safe_rel(rel)
    data = await _gh_fetch_raw(settings, section, safe)
    if len(data) > _MAX_FILE_BYTES:
        raise NotFoundError("File too large")
    name = safe.rsplit("/", 1)[-1]
    return FilePayload(name=name, media_type=_mime_for(_suffix_of(name)), data=data)


# --- Public async orchestrators ---------------------------------------------


def _require_github(settings: Settings, section: str) -> None:
    if section not in SECTIONS:
        raise NotFoundError("Unknown content section")
    if not _github_enabled(settings):
        raise ContentUnavailableError("Contenuti non configurati.")


async def get_listing(settings: Settings, section: str) -> ContentList:
    _require_github(settings, section)
    try:
        return await _gh_listing(settings, section)
    except _GitHubUnavailable as exc:
        raise ContentUnavailableError("GitHub non raggiungibile.") from exc


async def get_text(settings: Settings, section: str, rel: str) -> ContentFile:
    _require_github(settings, section)
    try:
        return await _gh_text(settings, section, rel)
    except _GitHubUnavailable as exc:
        raise ContentUnavailableError("GitHub non raggiungibile.") from exc


async def get_file(settings: Settings, section: str, rel: str) -> FilePayload:
    _require_github(settings, section)
    try:
        return await _gh_file(settings, section, rel)
    except _GitHubUnavailable as exc:
        raise ContentUnavailableError("GitHub non raggiungibile.") from exc
