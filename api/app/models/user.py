"""The ``User`` model: a flat, role-free 42 student.

There are no admin/BDE roles anywhere. Every authenticated user is a student;
authorization is strictly ownership-based (enforced in the service layer).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .comment import Comment
    from .like import PostLike
    from .post import Post


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The user's id on the 42 Intra (stable, unique). Not our PK.
    intra_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    campus: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Login activity metadata: ``login_count`` bumps on every 42 OAuth callback
    # (42 exposes no login counter, so we keep our own); ``last_login_at`` is the
    # most recent callback time.
    login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 42 user tokens (encrypted at rest) to act on 42 on the student's behalf.
    intra_access_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    intra_refresh_token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    intra_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    posts: Mapped[list["Post"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    likes: Mapped[list["PostLike"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
