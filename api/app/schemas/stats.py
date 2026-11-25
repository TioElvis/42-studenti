"""DTOs for the Studenti leaderboards ("Classifiche")."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class StatRow(BaseModel):
    """One leaderboard entry. ``value`` is a count, points, or seconds."""

    login: str
    display_name: str | None = None
    avatar_url: str | None = None
    value: int


class StatsOut(BaseModel):
    followers: list[StatRow] = []  # live, from our DB
    daje: list[StatRow] = []  # live, from our DB (likes received, own likes excluded)
    wallet: list[StatRow] = []  # from 42, refreshed in the background
    cluster: list[StatRow] = []  # seconds logged in at the cluster, last 30 days (42)
    intra_ready: bool = False  # False until the first 42 snapshot has been built
    intra_updated_at: datetime | None = None
    cluster_days: int = 30
