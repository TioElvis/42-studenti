"""Post and comment DTOs with strict input validation (allow-list by schema)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.enums import PostCategory, PostType
from .comment import CommentOut
from .user import UserPublic

TITLE_MAX = 140
CONTENT_MAX = 4000
CERCO_TEAM_MAX = 3
PARTICIPANTS_MAX = 500


def _strip_optional(v: str | None) -> str | None:
    """Trim; turn an empty/whitespace string into None (used for the title)."""
    if v is None:
        return None
    return v.strip() or None


def _strip_required(v: str | None) -> str | None:
    """Trim; reject an empty/whitespace body (used for post/comment content)."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        raise ValueError("Content cannot be empty")
    return v


class PostCreate(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    content: str = Field(min_length=1, max_length=CONTENT_MAX)
    category: PostCategory
    post_type: PostType = PostType.POST
    # Only used for a sondaggio. None = unlimited (where allowed).
    max_participants: int | None = Field(default=None, ge=1, le=PARTICIPANTS_MAX)

    @field_validator("title")
    @classmethod
    def _v_title(cls, v: str | None) -> str | None:
        return _strip_optional(v)

    @field_validator("content")
    @classmethod
    def _v_content(cls, v: str | None) -> str | None:
        return _strip_required(v)

    @model_validator(mode="after")
    def _v_participants(self) -> "PostCreate":
        if self.post_type is PostType.POST:
            # Capacity is meaningless on a plain post.
            object.__setattr__(self, "max_participants", None)
            return self
        # Sondaggio rules.
        if self.category is PostCategory.CERCO_TEAM:
            if self.max_participants is None or not (1 <= self.max_participants <= CERCO_TEAM_MAX):
                raise ValueError(
                    f"Un sondaggio 'Cerco team' vuole da 1 a {CERCO_TEAM_MAX} partecipanti."
                )
        # Other categories: None (unlimited) or a custom value within bounds — both ok.
        return self


class PostUpdate(BaseModel):
    """Partial update; only provided fields change.

    ``max_participants`` is only honored for a sondaggio. Sending it as ``null``
    means "unlimited" (where the category allows it); omitting it leaves the
    capacity unchanged. The post type itself cannot be changed after creation.
    """

    title: str | None = Field(default=None, max_length=TITLE_MAX)
    content: str | None = Field(default=None, min_length=1, max_length=CONTENT_MAX)
    category: PostCategory | None = None
    max_participants: int | None = Field(default=None, ge=1, le=PARTICIPANTS_MAX)

    @field_validator("title")
    @classmethod
    def _v_title(cls, v: str | None) -> str | None:
        return _strip_optional(v)

    @field_validator("content")
    @classmethod
    def _v_content(cls, v: str | None) -> str | None:
        return _strip_required(v)


class PostAuthor(UserPublic):
    pass


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    content: str
    category: PostCategory
    post_type: PostType
    max_participants: int | None = None
    created_at: datetime
    updated_at: datetime
    author: PostAuthor
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False
    is_mine: bool = False
    rsvp_count: int = 0
    rsvp_full: bool = False
    joined_by_me: bool = False


class PostDetail(PostOut):
    comments: list[CommentOut] = Field(default_factory=list)


class PostPage(BaseModel):
    """A page of posts for cursor-based infinite scroll."""

    items: list[PostOut]
    next_cursor: int | None = None


class LikeState(BaseModel):
    liked: bool
    like_count: int


class RsvpState(BaseModel):
    joined: bool
    rsvp_count: int
    rsvp_full: bool
