"""DTOs for the file-based Materiale / Archivio content."""

from __future__ import annotations

from pydantic import BaseModel


class ContentEntry(BaseModel):
    path: str  # posix path relative to the section root, e.g. "exam02/help.md"
    name: str  # file name, e.g. "help.md"
    folder: str  # parent folder relative to the section root ("" at the root)
    size: int  # bytes
    text: bool  # whether the file is a readable text document


class ContentList(BaseModel):
    section: str  # "material" | "archive"
    entries: list[ContentEntry]


class ContentFile(BaseModel):
    path: str
    name: str
    content: str
