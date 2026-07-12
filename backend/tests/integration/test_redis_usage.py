import os

import pytest
from redis.asyncio import Redis

from klee_web.jobs.usage import RedisUsageStatsStore
from klee_web.models import JobOutcome

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


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
async def store():
    client = Redis.from_url(_REDIS_URL)
    await client.flushdb()
    try:
        yield RedisUsageStatsStore(client)
    finally:
        await client.flushdb()
        await client.aclose()


async def test_empty_snapshot_is_zero_filled(store) -> None:
    snap = await store.snapshot()
    assert set(snap.outcomes) == set(JobOutcome)
    assert all(v == 0 for v in snap.outcomes.values())
    assert snap.cache_hits == 0
    assert snap.test_cases_generated == 0
    assert snap.instructions_executed == 0


async def test_records_accumulate_across_calls(store) -> None:
    await store.record_execution(JobOutcome.completed, test_cases=3, instructions=100)
    await store.record_execution(JobOutcome.completed, test_cases=1, instructions=20)
    await store.record_execution(JobOutcome.max_time)
    await store.record_cache_hit()
    snap = await store.snapshot()
    assert snap.outcomes[JobOutcome.completed] == 2
    assert snap.outcomes[JobOutcome.max_time] == 1
    assert snap.outcomes[JobOutcome.failed] == 0
    assert snap.test_cases_generated == 4
    assert snap.instructions_executed == 120
    assert snap.cache_hits == 1
