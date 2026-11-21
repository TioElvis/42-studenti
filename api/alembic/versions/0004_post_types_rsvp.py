"""post types (post/sondaggio) + max_participants + post_rsvps

Revision ID: 0004_post_types_rsvp
Revises: 0003_intra_tokens
Create Date: 2026-11-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_post_types_rsvp"
down_revision: str | None = "0003_intra_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_POST_TYPE = sa.Enum("post", "sondaggio", name="post_type", native_enum=False, length=16)


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("post_type", _POST_TYPE, nullable=False, server_default="post"),
    )
    op.add_column("posts", sa.Column("max_participants", sa.Integer(), nullable=True))

    op.create_table(
        "post_rsvps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_post_rsvp"),
    )
    op.create_index("ix_post_rsvps_user_id", "post_rsvps", ["user_id"])
    op.create_index("ix_post_rsvps_post_id", "post_rsvps", ["post_id"])


def downgrade() -> None:
    op.drop_table("post_rsvps")
    op.drop_column("posts", "max_participants")
    op.drop_column("posts", "post_type")
