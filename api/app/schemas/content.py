"""DTOs for the file-based Materiale / Archivio content."""

from __future__ import annotations

from pydantic import BaseModel


class ContentEntry(BaseModel):
    path: str  # posix path relative to the section root, e.g. "exam02/help.md"
    name: str  # file name, e.g. "help.md"
    folder: str  # parent folder relative to the section root ("" at the root)
    size: int  # bytes
    kind: str  # "text" | "image" | "pdf" | "other" — how the UI should render it
    mime: str  # media type, e.g. "application/pdf"
    sha: str = ""  # git blob sha (metadata only)
    github_url: str = ""  # https://github.com/<repo>/blob/<branch>/assets/...
    raw_url: str = ""  # raw.githubusercontent.com URL (public repos only)


class ContentList(BaseModel):
    section: str  # "material" | "archive"
    entries: list[ContentEntry]
    folders: list[str] = []  # every folder path (incl. empty ones), sorted


class ContentFile(BaseModel):
    path: str
    name: str
    content: str
