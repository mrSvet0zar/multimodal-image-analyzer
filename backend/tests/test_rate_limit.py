import pytest
from fastapi import HTTPException

from app.rate_limit import RateLimiter


def test_allows_up_to_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("1.2.3.4")  # should not raise


def test_blocks_over_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.check("1.2.3.4")
    limiter.check("1.2.3.4")
    with pytest.raises(HTTPException) as exc:
        limiter.check("1.2.3.4")
    assert exc.value.status_code == 429


def test_limits_are_per_key():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check("client-a")
    limiter.check("client-b")  # different key, still allowed
    with pytest.raises(HTTPException):
        limiter.check("client-a")
