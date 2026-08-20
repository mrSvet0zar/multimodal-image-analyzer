"""Per-client rate limiting — in-memory (single instance) or Redis (shared)."""

import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, Request


class Limiter(ABC):
    @abstractmethod
    async def check(self, key: str) -> None:
        """Record a hit for `key`; raise HTTP 429 if over the limit."""


class InMemoryLimiter(Limiter):
    """Fixed-window counter kept in process memory (single instance only)."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def check(self, key: str) -> None:
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


class RedisLimiter(Limiter):
    """Fixed-window counter in Redis — shared across all instances."""

    def __init__(self, redis: Any, max_requests: int, window_seconds: int):
        self.redis = redis
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def check(self, key: str) -> None:
        rkey = f"ratelimit:{key}"
        count = await self.redis.incr(rkey)
        if count == 1:
            await self.redis.expire(rkey, self.window_seconds)
        if count > self.max_requests:
            ttl = await self.redis.ttl(rkey)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(max(int(ttl), 1))},
            )


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"
