import os

import pytest
from redis.asyncio import Redis

from klee_web.jobs.cache import RedisResultCache
from klee_web.models import JobResult, SymbolicInput, TestCase

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_CACHE_TTL_SECONDS = 24 * 60 * 60


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


@pytest.fixture
async def cache():
    client = Redis.from_url(_REDIS_URL)
    await client.flushdb()
    try:
        yield RedisResultCache(client)
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.fixture
def sample_result() -> JobResult:
    return JobResult(
        test_cases=[
            TestCase(
                name="test1", inputs=[SymbolicInput(name="x", value="0", bytes_hex="00000000")]
            )
        ],
        messages="ok",
        warnings="",
        stats={"paths": 1, "instructions": 100},
    )


async def test_round_trips_result_through_real_redis(cache, sample_result):
    await cache.set("k", sample_result)
    assert await cache.get("k") == sample_result


async def test_get_miss_returns_none(cache):
    assert await cache.get("absent") is None


async def test_set_applies_bounded_ttl(cache, sample_result):
    await cache.set("k", sample_result)
    client = Redis.from_url(_REDIS_URL)
    try:
        ttl = await client.ttl("cache:k")
    finally:
        await client.aclose()
    assert 0 < ttl <= _CACHE_TTL_SECONDS
