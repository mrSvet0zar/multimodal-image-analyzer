"""Cost guard tests — in-memory and Redis (via fakeredis)."""

import fakeredis.aioredis
import pytest
from fastapi import HTTPException

from app.cost_guard import InMemoryCostGuard, RedisCostGuard


async def test_disabled_when_limit_zero():
    guard = InMemoryCostGuard(0.0)
    await guard.add(100.0)
    await guard.check()  # disabled -> never raises


async def test_inmemory_blocks_when_over_limit():
    guard = InMemoryCostGuard(1.0)
    await guard.check()  # 0 spent, ok
    await guard.add(0.6)
    await guard.check()  # 0.6 < 1.0, ok
    await guard.add(0.6)  # total 1.2
    with pytest.raises(HTTPException) as exc:
        await guard.check()
    assert exc.value.status_code == 429


async def test_redis_cost_guard():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    guard = RedisCostGuard(redis, 1.0)
    await guard.add(0.7)
    await guard.check()  # 0.7 < 1.0, ok
    await guard.add(0.5)  # total 1.2
    with pytest.raises(HTTPException):
        await guard.check()
