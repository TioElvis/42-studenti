"""A tiny in-process fixed-window rate limiter for sensitive endpoints.

Good enough for a single-process dev/small deployment. For horizontal scaling,
swap this adapter for a shared store (e.g. Redis) behind the same dependency.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request, status
from fastapi.exceptions import HTTPException


class FixedWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: float) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _client_key(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        self.check_key(self._client_key(request))

    def check_key(self, key: str) -> None:
        now = time.monotonic()
        window_start = now - self._window
        hits = [t for t in self._hits[key] if t >= window_start]
        if len(hits) >= self._max:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Aò, rallenta! Troppi tentativi, riprova tra un attimo.",
            )
        hits.append(now)
        self._hits[key] = hits


def auth_rate_limiter(request: Request) -> None:
    """Dependency: throttle auth endpoints to 20 requests / minute / IP."""
    _AUTH_LIMITER.check(request)


def message_rate_limiter(request: Request) -> None:
    """Dependency for user-generated messaging (e.g. a future "contact staff"
    endpoint): a stricter 5 requests / minute / IP to curb spam/abuse.

    NB: 42's API has no email-sending capability, so actually delivering a
    staff message needs a separate email provider (SMTP/SendGrid/SES); wire
    this limiter onto that endpoint when it's built.
    """
    _MESSAGE_LIMITER.check(request)


_AUTH_LIMITER = FixedWindowRateLimiter(max_requests=20, window_seconds=60.0)
_MESSAGE_LIMITER = FixedWindowRateLimiter(max_requests=5, window_seconds=60.0)
# Uploads to Materiale/Archivio: 20 commits / 10 minutes / user.
upload_limiter = FixedWindowRateLimiter(max_requests=20, window_seconds=600.0)
