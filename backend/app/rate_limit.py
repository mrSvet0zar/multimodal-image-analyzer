"""Lightweight in-memory, per-client rate limiting.

A fixed-window counter keyed by client IP. Good enough for a single-instance
demo; for multi-instance production, back it with Redis instead.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        """Record a hit for `key`; raise HTTP 429 if over the limit."""
        now = time.time()
        window_start = now - self.window_seconds
        recent = [t for t in self._hits[key] if t > window_start]

        if len(recent) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - recent[0])) + 1
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        recent.append(now)
        self._hits[key] = recent


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"
