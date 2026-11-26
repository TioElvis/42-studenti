"""The ``PushSubscription`` model: one browser that receives Web Push messages."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class PushSubscription(Base, TimestampMixin):
    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The push service URL for this browser; unique, so a browser has one owner.
    endpoint: Mapped[str] = mapped_column(String(1024), nullable=False)
    # The browser's public key and auth secret, used to encrypt each message.
    p256dh: Mapped[str] = mapped_column(String(128), nullable=False)
    auth: Mapped[str] = mapped_column(String(64), nullable=False)
    # Language of the notification text ("it" or "en"), chosen in the browser.
    lang: Mapped[str] = mapped_column(String(2), nullable=False, default="it")
