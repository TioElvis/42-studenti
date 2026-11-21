"""The ``Comment`` model: a reply within a post thread."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .post import Post
    from .user import User


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # A reply points at the comment it answers (same post). SET NULL on delete so
    # removing a parent comment keeps the replies (they just lose the @ref).
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="SET NULL"), index=True, nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    post: Mapped["Post"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")
