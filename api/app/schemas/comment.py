"""Comment DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .user import UserPublic

COMMENT_MAX = 2000


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=COMMENT_MAX)
    # Set to answer another comment on the same post (adds an @ref to its author).
    parent_id: int | None = Field(default=None, ge=1)

    @field_validator("content")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Comment cannot be empty")
        return v


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime
    author: UserPublic
    is_mine: bool = False
    # Reply threading: the answered comment's id, and the login to @ref in the UI
    # (None once the parent has been deleted — SET NULL).
    parent_id: int | None = None
    reply_to: str | None = None
