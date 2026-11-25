"""Background-refreshed 42 snapshot for the Studenti leaderboards.

Wallet points and cluster log time exist only on the 42 API and cost one or two
calls per student, so they are NOT fetched per page view. A single snapshot is
rebuilt in the background when it is older than ``stats_refresh_seconds``
(throttled by the client's rate limiter plus a small concurrency cap). Readers
always get the last good snapshot immediately; a failed refresh keeps it.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from intra42 import AsyncClient
from intra42.exceptions import FortyTwoAPIError

from .config import Settings

logger = logging.getLogger("app.stats")

CLUSTER_DAYS = 30
_CONCURRENCY = 3
_DURATION = re.compile(r"^(\d+):(\d{1,2}):(\d{1,2})(?:\.\d+)?$")


def parse_duration(value: object) -> int:
    """``"03:25:41.123456"`` → seconds. Anything malformed counts as 0."""
    if not isinstance(value, str):
        return 0
    m = _DURATION.match(value.strip())
    if not m:
        return 0
    h, mi, s = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s


@dataclass(frozen=True)
class StatsSnapshot:
    wallet: dict[str, int] = field(default_factory=dict)
    cluster: dict[str, int] = field(default_factory=dict)  # seconds, last 30 days
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IntraStats:
    """Holds the latest snapshot and refreshes it in the background."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._snapshot: StatsSnapshot | None = None
        self._fetched_at = 0.0  # monotonic time of the last successful build
        self._task: asyncio.Task[None] | None = None

    def _credentials_present(self) -> bool:
        return bool(self._settings.forty_two_uid and self._settings.forty_two_secret)

    def get(self, logins: list[str]) -> StatsSnapshot | None:
        """Return the current snapshot (maybe ``None`` on the very first call)
        and start a background refresh when it is missing or stale."""
        stale = (
            self._snapshot is None
            or time.monotonic() - self._fetched_at >= self._settings.stats_refresh_seconds
        )
        running = self._task is not None and not self._task.done()
        if stale and not running and logins and self._credentials_present():
            self._task = asyncio.create_task(self._refresh(list(logins)))
        return self._snapshot

    async def refresh_now(self, logins: list[str]) -> None:
        """Rebuild synchronously (used by tests and by an explicit warm-up)."""
        await self._refresh(logins)

    async def _refresh(self, logins: list[str]) -> None:
        end = datetime.now(timezone.utc)
        begin = end - timedelta(days=CLUSTER_DAYS)
        params = {"begin_at": begin.date().isoformat(), "end_at": end.date().isoformat()}
        wallet: dict[str, int] = {}
        cluster: dict[str, int] = {}
        sem = asyncio.Semaphore(_CONCURRENCY)
        ok = 0

        try:
            async with AsyncClient(
                self._settings.forty_two_uid, self._settings.forty_two_secret
            ) as client:

                async def one(login: str) -> None:
                    nonlocal ok
                    async with sem:
                        try:
                            u = await client.users.get(login)
                            if u.wallet is not None:
                                wallet[login] = int(u.wallet)
                            resp = await client.request(
                                "GET", f"/users/{login}/locations_stats", params=params
                            )
                            data = resp.json()
                            if isinstance(data, dict):
                                cluster[login] = sum(parse_duration(v) for v in data.values())
                            ok += 1
                        except FortyTwoAPIError:
                            return  # skip this student; keep going

                await asyncio.gather(*(one(lg) for lg in logins))
        except Exception:  # noqa: BLE001 - a background job must never crash the app
            logger.warning("stats refresh failed", exc_info=True)
            return

        if ok == 0:  # nothing worked (42 down): keep the previous snapshot
            logger.warning("stats refresh produced no data; keeping the old snapshot")
            return
        self._snapshot = StatsSnapshot(wallet=wallet, cluster=cluster)
        self._fetched_at = time.monotonic()
