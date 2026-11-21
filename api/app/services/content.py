"""File-based content for Materiale / Archivio.

Content lives in the repo under ``assets/material/**`` and ``assets/archive/**``
(committed via GitHub, e.g. ``assets/material/exam02/help.md``) and is served
read-only. Paths are canonicalized and confined to the section root — no path
traversal, no following symlinks out of the tree.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Settings
from ..schemas.content import ContentEntry, ContentFile, ContentList
from .exceptions import NotFoundError

# Section name -> subfolder under assets/. Allow-list; nothing else is reachable.
SECTIONS: dict[str, str] = {"material": "material", "archive": "archive"}

# Extensions we return as inline text (others are listed but not readable here).
_TEXT_EXT = {".md", ".markdown", ".txt", ".csv", ".json", ".yml", ".yaml"}
_MAX_BYTES = 512 * 1024  # 512 KiB cap on a single document


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
            entries.append(
                ContentEntry(
                    path=rel.as_posix(),
                    name=p.name,
                    folder="" if folder == "." else folder,
                    size=p.stat().st_size,
                    text=p.suffix.lower() in _TEXT_EXT,
                )
            )
    return ContentList(section=section, entries=entries)


def read_file(settings: Settings, section: str, rel: str) -> ContentFile:
    root = _section_root(settings, section)
    target = _resolve_within(root, rel)
    if not target.is_file() or target.name.startswith("."):
        raise NotFoundError("File not found")
    if target.suffix.lower() not in _TEXT_EXT:
        raise NotFoundError("This file type can't be shown here")
    if target.stat().st_size > _MAX_BYTES:
        raise NotFoundError("File too large to display")
    content = target.read_text(encoding="utf-8", errors="replace")
    return ContentFile(path=target.relative_to(root).as_posix(), name=target.name, content=content)
