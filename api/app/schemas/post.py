"""Post and comment DTOs with strict input validation (allow-list by schema)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..models.enums import PollMode, PostCategory, PostType
from .comment import CommentOut
from .user import UserPublic

TITLE_MAX = 140
CONTENT_MAX = 4000
CERCO_TEAM_MAX = 3
PARTICIPANTS_MAX = 500
POLL_OPTIONS_MIN = 2
POLL_OPTIONS_MAX = 10
POLL_OPTION_MAX_LEN = 120


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
    # Sondaggio poll settings.
    poll_mode: PollMode = PollMode.ATTENDANCE
    poll_multi: bool = False  # single- vs multiple-choice (options mode only)
    options: list[str] = Field(default_factory=list)  # options mode only
    # Auto-register the author on an attendance sondaggio ("Partecipo anch'io").
    participate: bool = True

    @field_validator("title")
    @classmethod
    def _v_title(cls, v: str | None) -> str | None:
        return _strip_optional(v)

    @field_validator("content")
    @classmethod
    def _v_content(cls, v: str | None) -> str | None:
        return _strip_required(v)

    @model_validator(mode="after")
    def _v_sondaggio(self) -> "PostCreate":
        if self.post_type is PostType.POST:
            # Poll/capacity are meaningless on a plain post.
            object.__setattr__(self, "max_participants", None)
            object.__setattr__(self, "poll_mode", PollMode.ATTENDANCE)
            object.__setattr__(self, "poll_multi", False)
            object.__setattr__(self, "options", [])
            return self

        if self.poll_mode is PollMode.OPTIONS:
            # An options poll has no attendance capacity.
            object.__setattr__(self, "max_participants", None)
            cleaned: list[str] = []
            seen: set[str] = set()
            for raw in self.options:
                s = raw.strip()[:POLL_OPTION_MAX_LEN].strip()
                if not s or s.casefold() in seen:
                    continue
                seen.add(s.casefold())
                cleaned.append(s)
            if len(cleaned) < POLL_OPTIONS_MIN:
                raise ValueError(
                    f"Un sondaggio a opzioni vuole almeno {POLL_OPTIONS_MIN} opzioni distinte."
                )
            object.__setattr__(self, "options", cleaned[:POLL_OPTIONS_MAX])
            return self

        # Attendance mode: no options; capacity rules as before.
        object.__setattr__(self, "options", [])
        object.__setattr__(self, "poll_multi", False)
        if self.category is PostCategory.CERCO_TEAM:
            if self.max_participants is None or not (1 <= self.max_participants <= CERCO_TEAM_MAX):
                raise ValueError(
                    f"Un sondaggio 'Cerco team' vuole da 1 a {CERCO_TEAM_MAX} partecipanti."
                )
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


class PollOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    vote_count: int = 0
    voted_by_me: bool = False


class PollState(BaseModel):
    """Response of a vote toggle: the post's options with fresh counts."""

    post_id: int
    options: list[PollOptionOut]


class PollVoteIn(BaseModel):
    option_id: int = Field(ge=1)


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    content: str
    category: PostCategory
    post_type: PostType
    max_participants: int | None = None
    poll_mode: PollMode = PollMode.ATTENDANCE
    poll_multi: bool = False
    poll_options: list[PollOptionOut] = Field(default_factory=list)
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
