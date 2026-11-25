"""User DTOs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    """A user as shown to other students (no email)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    display_name: str | None = None
    avatar_url: str | None = None
    campus: str | None = None


class UserMe(UserPublic):
    """The authenticated user's own profile (includes email)."""

    email: str | None = None
    intra_id: int


class StudentPage(BaseModel):
    """One page of the Studenti directory."""

    items: list[UserPublic]
    total: int
    page: int  # 1-based, clamped to the last page
    pages: int  # at least 1
