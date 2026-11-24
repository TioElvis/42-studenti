"""File-based content for Materiale / Archivio.

Content lives in the repo under ``assets/material/**`` and ``assets/archive/**``
(committed via GitHub, e.g. ``assets/material/exam02/help.md``) and is served
read-only. Paths are canonicalized and confined to the section root — no path
traversal, no following symlinks out of the tree.

Any file type is listed. Text files are returned inline (JSON); binary files
(PDF, images, Office docs, …) are streamed by the router and classified by
``kind`` so the UI can render images/PDFs and offer a download for the rest.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from ..config import Settings
from ..schemas.content import ContentEntry, ContentFile, ContentList
from .exceptions import NotFoundError

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


def _section_root(settings: Settings, section: str) -> Path:
    if section not in SECTIONS:
        raise NotFoundError("Unknown content section")
    return (Path(settings.assets_dir) / SECTIONS[section]).resolve()


def _resolve_within(root: Path, rel: str) -> Path:
    """Resolve ``rel`` under ``root``, rejecting anything that escapes it."""
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise NotFoundError("File not found") from exc
    if not target.is_file() or target.name.startswith("."):
        raise NotFoundError("File not found")
    return target


def list_entries(settings: Settings, section: str) -> ContentList:
    root = _section_root(settings, section)
    entries: list[ContentEntry] = []
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.name.startswith("."):
                continue
            rel = p.relative_to(root)
            folder = rel.parent.as_posix()
            suffix = p.suffix.lower()
            entries.append(
                ContentEntry(
                    path=rel.as_posix(),
                    name=p.name,
                    folder="" if folder == "." else folder,
                    size=p.stat().st_size,
                    kind=_kind_for(suffix),
                    mime=_mime_for(suffix),
                )
            )
    return ContentList(section=section, entries=entries)


def read_file(settings: Settings, section: str, rel: str) -> ContentFile:
    """Return a text document's content (for inline rendering)."""
    root = _section_root(settings, section)
    target = _resolve_within(root, rel)
    if target.suffix.lower() not in _TEXT_EXT:
        raise NotFoundError("This file type can't be shown as text")
    if target.stat().st_size > _MAX_TEXT_BYTES:
        raise NotFoundError("File too large to display")
    content = target.read_text(encoding="utf-8", errors="replace")
    return ContentFile(path=target.relative_to(root).as_posix(), name=target.name, content=content)


def resolve_file(settings: Settings, section: str, rel: str) -> tuple[Path, str]:
    """Resolve a file for streaming (any type); returns (path, media_type)."""
    root = _section_root(settings, section)
    target = _resolve_within(root, rel)
    if target.stat().st_size > _MAX_FILE_BYTES:
        raise NotFoundError("File too large")
    return target, _mime_for(target.suffix.lower())


# ---------------------------------------------------------------------------
# GitHub-backed source (optional): read content live from a repo's assets/ so
# a push/merge updates the site without a redeploy. Falls back to the local
# source on any availability error; a genuine 404 propagates as NotFoundError.
# ---------------------------------------------------------------------------

_GITHUB_API = "https://api.github.com"
_GITHUB_RAW = "https://raw.githubusercontent.com"
_GH_UA = "42-studenti"  # GitHub requires a User-Agent; generic app name, no PII.


@dataclass
class FilePayload:
    """A file to stream: either a local path or in-memory bytes (GitHub)."""

    name: str
    media_type: str
    path: Path | None = None
    data: bytes | None = None


class _GitHubUnavailable(Exception):
    """GitHub couldn't be reached / returned an unexpected status → fall back."""


# Per-section tree-listing cache (TTL). File bytes come from raw.* (uncached
# here; the browser caches them via Cache-Control).
_gh_tree_cache: dict[str, tuple[float, ContentList]] = {}
_gh_lock = asyncio.Lock()


def invalidate_github_cache(section: str | None = None) -> None:
    """Drop the cached listing (used after a direct push in Step 11)."""
    if section is None:
        _gh_tree_cache.clear()
    else:
        _gh_tree_cache.pop(section, None)


def _github_enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "github_repo", ""))


def _suffix_of(name: str) -> str:
    return f".{name.rsplit('.', 1)[-1].lower()}" if "." in name else ""


def _safe_rel(rel: str) -> str:
    """Confine a GitHub-bound relative path to the section (no traversal)."""
    cleaned = rel.strip().lstrip("/")
    segments = cleaned.split("/")
    if not cleaned or any(seg in ("", "..") or seg.startswith(".") for seg in segments):
        raise NotFoundError("File not found")
    return cleaned


def confine_rel(rel: str) -> str:
    """Public: validate a relative path stays under the section (no traversal)."""
    return _safe_rel(rel)


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
        for item in resp.json().get("tree") or []:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if not path.startswith(prefix):
                continue
            rel = path[len(prefix):]
            segments = rel.split("/")
            if not rel or any(seg.startswith(".") for seg in segments):
                continue
            name = segments[-1]
            folder = "/".join(segments[:-1])
            suffix = _suffix_of(name)
            entries.append(
                ContentEntry(
                    path=rel,
                    name=name,
                    folder=folder,
                    size=int(item.get("size") or 0),
                    kind=_kind_for(suffix),
                    mime=_mime_for(suffix),
                )
            )
        entries.sort(key=lambda e: e.path)
        result = ContentList(section=section, entries=entries)
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


# --- Public async orchestrators (GitHub when configured, else local) --------


async def get_listing(settings: Settings, section: str) -> ContentList:
    if section not in SECTIONS:
        raise NotFoundError("Unknown content section")
    if _github_enabled(settings):
        try:
            return await _gh_listing(settings, section)
        except _GitHubUnavailable:
            pass  # fall back to the local tree
    return list_entries(settings, section)


async def get_text(settings: Settings, section: str, rel: str) -> ContentFile:
    if section not in SECTIONS:
        raise NotFoundError("Unknown content section")
    if _github_enabled(settings):
        try:
            return await _gh_text(settings, section, rel)
        except _GitHubUnavailable:
            pass
    return read_file(settings, section, rel)


async def get_file(settings: Settings, section: str, rel: str) -> FilePayload:
    if section not in SECTIONS:
        raise NotFoundError("Unknown content section")
    if _github_enabled(settings):
        try:
            return await _gh_file(settings, section, rel)
        except _GitHubUnavailable:
            pass
    path, mime = resolve_file(settings, section, rel)
    return FilePayload(name=path.name, media_type=mime, path=path)
