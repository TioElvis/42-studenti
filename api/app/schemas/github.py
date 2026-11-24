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
    path: str = Field(min_length=1, max_length=512)
    content: str = Field(min_length=1)
    encoding: Literal["utf-8", "base64"] = "utf-8"
    # "pr" = fork/branch + Pull Request; "push" = commit straight to the branch
    # (needs GitHub write access to the repo).
    mode: Literal["pr", "push"] = "pr"
    message: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)


class ContributeOut(BaseModel):
    pr_url: str
