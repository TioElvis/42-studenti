"""The ``PostRSVP`` model: a student who clicked "Ci sto!" on a sondaggio.

Separate from likes on purpose — liking a post and attending it are distinct
actions. The composite unique constraint makes attendance idempotent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .post import Post
    from .user import User


class PostRSVP(Base, TimestampMixin):
    __tablename__ = "post_rsvps"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_post_rsvp"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True, nullable=False
    )

    user: Mapped["User"] = relationship()
    post: Mapped["Post"] = relationship(back_populates="rsvps")
