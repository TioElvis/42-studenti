"""comment replies (parent_id) + user login stats (login_count, last_login_at)

Revision ID: 0005_replies_and_login_stats
Revises: 0004_post_types_rsvp
Create Date: 2026-11-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_replies_and_login_stats"
down_revision: str | None = "0004_post_types_rsvp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Comment replies: a self-FK; SET NULL keeps replies when a parent is deleted.
    op.add_column("comments", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])
    op.create_foreign_key(
        "fk_comments_parent_id",
        "comments",
        "comments",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Playful login stats (42 has no login counter, so we keep our own).
    op.add_column(
        "users",
        sa.Column("login_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "login_count")
    op.drop_constraint("fk_comments_parent_id", "comments", type_="foreignkey")
    op.drop_index("ix_comments_parent_id", table_name="comments")
    op.drop_column("comments", "parent_id")
