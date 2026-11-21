"""initial schema: users, posts, comments, post_likes

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORY = sa.Enum(
    "studio",
    "cerco_team",
    "evento_casuale",
    "vita_romana",
    "mercatino",
    "off_topic",
    name="post_category",
    native_enum=False,
    length=32,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("intra_id", sa.BigInteger(), nullable=False),
        sa.Column("login", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("campus", sa.String(length=128), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("intra_id", name="uq_users_intra_id"),
        sa.UniqueConstraint("login", name="uq_users_login"),
    )
    op.create_index("ix_users_intra_id", "users", ["intra_id"])
    op.create_index("ix_users_login", "users", ["login"])

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", _CATEGORY, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_posts_author_id", "posts", ["author_id"])
    op.create_index("ix_posts_category", "posts", ["category"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_comments_post_id", "comments", ["post_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    op.create_table(
        "post_likes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_post_like"),
    )
    op.create_index("ix_post_likes_user_id", "post_likes", ["user_id"])
    op.create_index("ix_post_likes_post_id", "post_likes", ["post_id"])


def downgrade() -> None:
    op.drop_table("post_likes")
    op.drop_table("comments")
    op.drop_table("posts")
    op.drop_index("ix_users_login", table_name="users")
    op.drop_index("ix_users_intra_id", table_name="users")
    op.drop_table("users")
