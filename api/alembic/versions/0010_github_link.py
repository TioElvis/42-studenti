"""link a student's GitHub account (username + encrypted token)

Revision ID: 0010_github_link
Revises: 0009_polls
Create Date: 2026-11-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_github_link"
down_revision: str | None = "0009_polls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("github_username", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("github_token_enc", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "github_token_enc")
    op.drop_column("users", "github_username")
