"""Rate limiter tests — in-memory and Redis (via fakeredis)."""

import fakeredis.aioredis
import pytest
from fastapi import HTTPException

from app.rate_limit import InMemoryLimiter, RedisLimiter


async def test_inmemory_allows_up_to_limit():
    limiter = InMemoryLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        await limiter.check("1.2.3.4")  # should not raise


async def test_inmemory_blocks_over_limit():
    limiter = InMemoryLimiter(max_requests=2, window_seconds=60)
    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")
    with pytest.raises(HTTPException) as exc:
        await limiter.check("1.2.3.4")
    assert exc.value.status_code == 429


async def test_inmemory_per_key():
    limiter = InMemoryLimiter(max_requests=1, window_seconds=60)
    await limiter.check("client-a")
    await limiter.check("client-b")  # different key, still allowed
    with pytest.raises(HTTPException):
        await limiter.check("client-a")


async def test_redis_limiter_blocks_over_limit():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    limiter = RedisLimiter(redis, max_requests=2, window_seconds=60)
    await limiter.check("k")
    await limiter.check("k")
    with pytest.raises(HTTPException) as exc:
        await limiter.check("k")
    assert exc.value.status_code == 429
    await limiter.check("other-key")  # different key, allowed
