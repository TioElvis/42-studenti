"""store 42 user tokens + the 42 events_user id for real event sign-up

Revision ID: 0003_intra_tokens
Revises: 0002_event_interests
Create Date: 2026-11-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_intra_tokens"
down_revision: str | None = "0002_event_interests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("intra_access_token_enc", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("intra_refresh_token_enc", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("intra_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_interests",
        sa.Column("intra_events_user_id", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_interests", "intra_events_user_id")
    op.drop_column("users", "intra_token_expires_at")
    op.drop_column("users", "intra_refresh_token_enc")
    op.drop_column("users", "intra_access_token_enc")
