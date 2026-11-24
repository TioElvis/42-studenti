"""sondaggio poll modes: poll_options + poll_votes + posts.poll_mode/poll_multi

Revision ID: 0009_polls
Revises: 0008_notif_retention_idx
Create Date: 2026-11-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_polls"
down_revision: str | None = "0008_notif_retention_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_POLL_MODE = sa.Enum(
    "attendance", "options", name="poll_mode", native_enum=False, length=16
)


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("poll_mode", _POLL_MODE, nullable=False, server_default="attendance"),
    )
    op.add_column(
        "posts",
        sa.Column("poll_multi", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "poll_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_poll_options_post_id", "poll_options", ["post_id"])

    op.create_table(
        "poll_votes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["poll_options.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("option_id", "user_id", name="uq_poll_vote"),
    )
    op.create_index("ix_poll_votes_option_id", "poll_votes", ["option_id"])
    op.create_index("ix_poll_votes_user_id", "poll_votes", ["user_id"])


def downgrade() -> None:
    op.drop_table("poll_votes")
    op.drop_table("poll_options")
    op.drop_column("posts", "poll_multi")
    op.drop_column("posts", "poll_mode")
