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
async def redis_client():
    client = Redis.from_url(_REDIS_URL)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def cache(redis_client):
    await redis_client.flushdb()
    try:
        yield RedisResultCache(redis_client)
    finally:
        await redis_client.flushdb()


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


async def test_get_miss_returns_none_without_creating_key(cache, redis_client):
    assert await cache.get("absent") is None
    assert await redis_client.exists("cache:absent") == 0


async def test_set_applies_bounded_ttl(cache, sample_result, redis_client):
    await cache.set("k", sample_result)
    ttl = await redis_client.ttl("cache:k")
    assert 0 < ttl <= _CACHE_TTL_SECONDS


async def test_cache_hit_refreshes_ttl(cache, sample_result, redis_client):
    await cache.set("k", sample_result)
    await redis_client.expire("cache:k", 10)

    assert await cache.get("k") == sample_result
    ttl = await redis_client.ttl("cache:k")

    assert _CACHE_TTL_SECONDS - 1 <= ttl <= _CACHE_TTL_SECONDS
