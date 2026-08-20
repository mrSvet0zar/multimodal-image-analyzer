"""Shared async Redis client (created lazily; None when REDIS_URL is unset)."""

from typing import Any

from app.config import settings

_client: Any = None
_initialized = False


def get_redis() -> Any:
    """Return a shared async Redis client, or None if Redis isn't configured."""
    global _client, _initialized
    if not _initialized:
        _initialized = True
        if settings.redis_url:
            import redis.asyncio as aioredis

            _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client
