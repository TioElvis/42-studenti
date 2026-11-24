"""The ``Notification`` model: an event directed at one recipient."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import NotificationType

if TYPE_CHECKING:
    from .user import User


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    # Keyset list is: recipient_id = ? AND created_at >= cutoff, ordered by id.
    __table_args__ = (
        Index("ix_notifications_recipient_created", "recipient_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    actor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(
            NotificationType,
            name="notification_type",
            native_enum=False,
            length=16,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    # The post the notification points at (post/comment/reply); null for follows.
    post_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    actor: Mapped["User"] = relationship(foreign_keys=[actor_id])