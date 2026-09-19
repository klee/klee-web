import os
from uuid import uuid4

import pytest
from redis.asyncio import Redis

from klee_web.jobs.store import JobNotFound, RedisJobStore
from klee_web.models import Job, JobResult, JobStatus, SymbolicInput, TestCase

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_JOB_TTL_SECONDS = 48 * 60 * 60


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
        yield RedisJobStore(client)
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


async def test_round_trips_job_through_real_redis(store):
    job = Job()
    await store.create(job)
    assert await store.get(job.id) == job


async def test_set_result_advances_status_and_stores_result(store, sample_result):
    job = Job()
    await store.create(job)
    await store.set_result(job.id, sample_result)
    retrieved = await store.get(job.id)
    assert retrieved is not None
    assert retrieved.status == JobStatus.done
    assert retrieved.result == sample_result


async def test_mutator_on_missing_id_raises_job_not_found(store):
    with pytest.raises(JobNotFound):
        await store.update_status(uuid4(), JobStatus.running)


async def test_create_sets_bounded_ttl(store):
    job = Job()
    await store.create(job)
    client = Redis.from_url(_REDIS_URL)
    try:
        ttl = await client.ttl(f"job:{job.id}")
    finally:
        await client.aclose()
    assert _JOB_TTL_SECONDS - 5 <= ttl <= _JOB_TTL_SECONDS


async def test_get_does_not_refresh_ttl(store):
    job = Job()
    await store.create(job)
    client = Redis.from_url(_REDIS_URL)
    try:
        await client.expire(f"job:{job.id}", 60)
        await store.get(job.id)
        ttl = await client.ttl(f"job:{job.id}")
    finally:
        await client.aclose()
    assert 0 < ttl <= 60
