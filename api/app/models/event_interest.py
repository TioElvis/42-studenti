"""The ``EventInterest`` model: a student's RSVP ("Mi interessa") to an event.

We can't subscribe users to official 42 events (our OAuth scope is ``public``),
so interest is tracked locally. ``event_id`` is the 42 Intra event id; there is
no FK because events live on the Intra, not in our database. The composite
unique constraint makes an RSVP idempotent (one per student per event).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class EventInterest(Base, TimestampMixin):
    __tablename__ = "event_interests"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_event_interest"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    # The id of the registration on 42 (events_user.id), so we can cancel it.
    intra_events_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    user: Mapped["User"] = relationship()
