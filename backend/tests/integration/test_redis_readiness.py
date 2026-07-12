import os

import pytest
from redis.asyncio import Redis

from klee_web.health import RedisReadiness

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_UNREACHABLE_URL = "redis://localhost:6390/0"


def _redis_ready() -> bool:
    import redis

    try:
        client = redis.Redis.from_url(_REDIS_URL, socket_connect_timeout=1)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _redis_ready(),
    reason=f"redis not reachable at {_REDIS_URL}",
)


async def test_ready_against_live_redis() -> None:
    client = Redis.from_url(_REDIS_URL)
    try:
        assert await RedisReadiness(client).is_ready() is True
    finally:
        await client.aclose()


async def test_not_ready_against_unreachable_redis() -> None:
    client = Redis.from_url(_UNREACHABLE_URL, socket_connect_timeout=1)
    try:
        assert await RedisReadiness(client).is_ready() is False
    finally:
        await client.aclose()
