"""DTOs for linking GitHub and contributing files to assets/."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GithubStatus(BaseModel):
    configured: bool  # is the GitHub OAuth app set up on this deployment?
    linked: bool
    username: str | None = None


class ContributeIn(BaseModel):
    section: Literal["material", "archive"]
    path: str = Field(min_length=1, max_length=512)
    content: str = Field(min_length=1)
    encoding: Literal["utf-8", "base64"] = "utf-8"
    message: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)


class ContributeOut(BaseModel):
    pr_url: str
