"""Student profile DTOs (own profile and other 42 Roma students)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ActivityStats(BaseModel):
    """What the student has done inside this app."""

    posts: int
    comments: int
    daje_received: int  # likes received across their own posts
    rsvps: int
    logins: int


class ProjectInfo(BaseModel):
    name: str
    status: str
    mark: int | None = None
    validated: bool | None = None


class Intra42Info(BaseModel):
    """Public figures read live from 42."""

    level: float | None = None
    grade: str | None = None
    correction_point: int | None = None
    wallet: int | None = None
    location: str | None = None  # current cluster seat, if logged in
    pool: str | None = None  # e.g. "Settembre 2024"
    joined: datetime | None = None  # 42 account creation
    projects: list[ProjectInfo] = []
    achievements: list[str] = []


class ProfileOut(BaseModel):
    # Identity + figures come live from 42; activity is computed from our DB.
    login: str
    display_name: str | None
    avatar_url: str | None
    campus: str | None
    is_me: bool
    activity: ActivityStats
    intra: Intra42Info
