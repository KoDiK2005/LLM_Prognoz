from redis.asyncio import Redis

from app.core.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


class RateLimitExceeded(Exception):
    pass


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Fixed-window counter: the first request in a window sets the TTL,
    every request after it just increments. Raises once `limit` is passed.
    """
    redis = get_redis()
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)
    if current > limit:
        raise RateLimitExceeded()
