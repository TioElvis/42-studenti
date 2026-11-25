"""DTOs for linking GitHub and contributing files to assets/."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GithubStatus(BaseModel):
    configured: bool  # can anyone contribute on this deployment?
    server_mode: bool = False  # backend commits with its own token (no linking)
    linked: bool
    username: str | None = None
    can_archive: bool = False  # may this student contribute to the archive section?


class ContributeIn(BaseModel):
    section: Literal["material", "archive"]
    # Nested relative path, e.g. "exam02/ex03/notes.md". With ``create_folder`` it
    # is the folder to create instead (e.g. "exam02/ex03") and ``content`` is ignored.
    path: str = Field(min_length=1, max_length=512)
    content: str = Field(default="", max_length=8_000_000)
    encoding: Literal["utf-8", "base64"] = "utf-8"
    message: str | None = Field(default=None, max_length=200)
    create_folder: bool = False


class ContributeOut(BaseModel):
    url: str
    action: Literal["created", "updated"]
