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

from pathlib import Path

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
