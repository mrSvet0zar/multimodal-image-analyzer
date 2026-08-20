"""Global daily spend guard — protects the Claude API budget on a public app.

Tracks cumulative USD spend per UTC day and rejects new analyses once the
configured limit is reached. In-memory for a single instance, Redis when shared.
A limit of 0 disables the guard entirely.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class CostGuard(ABC):
    def __init__(self, limit_usd: float):
        self.limit_usd = limit_usd

    async def check(self) -> None:
        """Raise HTTP 429 if today's spend already reached the limit."""
        if self.limit_usd <= 0:
            return
        spent = await self._spent_today()
        if spent >= self.limit_usd:
            raise HTTPException(
                status_code=429,
                detail="Daily budget reached. Please try again tomorrow.",
            )

    async def add(self, cost_usd: float) -> None:
        if self.limit_usd <= 0 or cost_usd <= 0:
            return
        await self._add_today(cost_usd)

    @abstractmethod
    async def _spent_today(self) -> float: ...

    @abstractmethod
    async def _add_today(self, cost_usd: float) -> None: ...


class InMemoryCostGuard(CostGuard):
    def __init__(self, limit_usd: float):
        super().__init__(limit_usd)
        self._spent: dict[str, float] = {}

    async def _spent_today(self) -> float:
        return self._spent.get(_today(), 0.0)

    async def _add_today(self, cost_usd: float) -> None:
        day = _today()
        self._spent[day] = self._spent.get(day, 0.0) + cost_usd


class RedisCostGuard(CostGuard):
    def __init__(self, redis: Any, limit_usd: float):
        super().__init__(limit_usd)
        self.redis = redis

    async def _spent_today(self) -> float:
        value = await self.redis.get(f"cost:{_today()}")
        return float(value) if value else 0.0

    async def _add_today(self, cost_usd: float) -> None:
        key = f"cost:{_today()}"
        await self.redis.incrbyfloat(key, cost_usd)
        await self.redis.expire(key, 2 * 24 * 3600)  # keep ~2 days
