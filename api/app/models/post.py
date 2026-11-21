"""The ``Post`` model: a message on La Bacheca."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import PostCategory, PostType

if TYPE_CHECKING:
    from .comment import Comment
    from .like import PostLike
    from .rsvp import PostRSVP
    from .user import User


class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    __table_args__ = (Index("ix_posts_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(140), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[PostCategory] = mapped_column(
        SAEnum(PostCategory, name="post_category", native_enum=False, length=32),
        nullable=False,
        index=True,
    )
    post_type: Mapped[PostType] = mapped_column(
        SAEnum(PostType, name="post_type", native_enum=False, length=16),
        nullable=False,
        default=PostType.POST,
        server_default=PostType.POST.value,
    )
    # Max attendees for a sondaggio: NULL = unlimited, only meaningful when
    # post_type == SONDAGGIO.
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)

    author: Mapped["User"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="Comment.created_at",
    )
    likes: Mapped[list["PostLike"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    rsvps: Mapped[list["PostRSVP"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
