"""Poll options and votes for an "options" sondaggio (WhatsApp-style poll)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .post import Post
    from .user import User


class PollOption(Base, TimestampMixin):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    text: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    post: Mapped["Post"] = relationship(back_populates="poll_options")
    votes: Mapped[list["PollVote"]] = relationship(
        back_populates="option", cascade="all, delete-orphan"
    )


class PollVote(Base, TimestampMixin):
    __tablename__ = "poll_votes"
    # One vote per (option, user); single- vs multiple-choice is enforced in the
    # service across a post's options.
    __table_args__ = (UniqueConstraint("option_id", "user_id", name="uq_poll_vote"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    option_id: Mapped[int] = mapped_column(
        ForeignKey("poll_options.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    option: Mapped["PollOption"] = relationship(back_populates="votes")
    user: Mapped["User"] = relationship()
