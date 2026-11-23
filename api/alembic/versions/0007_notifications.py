"""notifications table + user notification preferences

Revision ID: 0007_notifications
Revises: 0006_follows
Create Date: 2026-11-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_notifications"
down_revision: str | None = "0006_follows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOTIF_TYPE = sa.Enum(
    "post", "comment", "reply", "follow", name="notification_type", native_enum=False, length=16
)
_POST_NOTIFY = sa.Enum("off", "followed", "all", name="post_notify", native_enum=False, length=16)


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("type", _NOTIF_TYPE, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notifications_recipient_id", "notifications", ["recipient_id"])

    op.add_column(
        "users",
        sa.Column("notify_posts", _POST_NOTIFY, nullable=False, server_default="followed"),
    )
    op.add_column(
        "users",
        sa.Column("notify_comments", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column("notify_follows", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("users", "notify_follows")
    op.drop_column("users", "notify_comments")
    op.drop_column("users", "notify_posts")
    op.drop_table("notifications")
