import asyncio
from uuid import uuid4

import fakeredis
import pytest

from klee_web.jobs.store import InMemoryJobStore, JobNotFound, RedisJobStore
from klee_web.models import Job, JobStatus


@pytest.fixture(params=["memory", "redis"])
async def store(request):
    if request.param == "memory":
        yield InMemoryJobStore()
        return
    client = fakeredis.FakeAsyncRedis(server=fakeredis.FakeServer())
    yield RedisJobStore(client)
    await client.aclose()


async def test_create_then_get_returns_same_job(store):
    job = Job()
    await store.create(job)
    retrieved = await store.get(job.id)
    assert retrieved == job


async def test_get_unknown_id_returns_none(store):
    assert await store.get(uuid4()) is None


async def test_two_distinct_jobs_can_coexist(store):
    a, b = Job(), Job()
    await store.create(a)
    await store.create(b)
    assert (await store.get(a.id)) == a
    assert (await store.get(b.id)) == b


async def test_update_status_changes_status(store):
    job = Job()
    await store.create(job)
    await store.update_status(job.id, JobStatus.running)
    retrieved = await store.get(job.id)
    assert retrieved is not None
    assert retrieved.status == JobStatus.running


async def test_update_status_on_unknown_id_raises_job_not_found(store):
    with pytest.raises(JobNotFound):
        await store.update_status(uuid4(), JobStatus.running)


async def test_set_result_stores_result_and_advances_status_to_done(store, sample_result):
    job = Job()
    await store.create(job)
    await store.set_result(job.id, sample_result)
    retrieved = await store.get(job.id)
    assert retrieved is not None
    assert retrieved.status == JobStatus.done
    assert retrieved.result == sample_result


async def test_set_result_on_unknown_id_raises_job_not_found(store, sample_result):
    with pytest.raises(JobNotFound):
        await store.set_result(uuid4(), sample_result)


async def test_set_partial_result_writes_result_without_advancing_status(store, sample_result):
    job = Job()
    await store.create(job)
    await store.update_status(job.id, JobStatus.running)
    await store.set_partial_result(job.id, sample_result)
    retrieved = await store.get(job.id)
    assert retrieved is not None
    assert retrieved.result == sample_result
    assert retrieved.status == JobStatus.running


async def test_set_partial_result_on_unknown_id_raises_job_not_found(store, sample_result):
    with pytest.raises(JobNotFound):
        await store.set_partial_result(uuid4(), sample_result)


async def test_request_cancel_sets_flag(store):
    job = Job()
    await store.create(job)
    assert job.cancel_requested is False
    await store.request_cancel(job.id)
    retrieved = await store.get(job.id)
    assert retrieved is not None
    assert retrieved.cancel_requested is True


async def test_request_cancel_on_unknown_id_raises_job_not_found(store):
    with pytest.raises(JobNotFound):
        await store.request_cancel(uuid4())


async def test_increment_attempts_returns_incrementing_counts(store):
    job = Job()
    await store.create(job)
    assert await store.increment_attempts(job.id) == 1
    assert await store.increment_attempts(job.id) == 2
    retrieved = await store.get(job.id)
    assert retrieved is not None
    assert retrieved.attempts == 2


async def test_increment_attempts_on_unknown_id_raises_job_not_found(store):
    with pytest.raises(JobNotFound):
        await store.increment_attempts(uuid4())


async def test_set_failed_marks_status_and_reason(store):
    job = Job()
    await store.create(job)
    await store.set_failed(job.id, "gave up after 3 attempts")
    retrieved = await store.get(job.id)
    assert retrieved is not None
    assert retrieved.status == JobStatus.failed
    assert retrieved.failure_reason == "gave up after 3 attempts"


async def test_set_failed_on_unknown_id_raises_job_not_found(store):
    with pytest.raises(JobNotFound):
        await store.set_failed(uuid4(), "reason")


async def test_concurrent_creates_dont_lose_jobs(store):
    jobs = [Job() for _ in range(50)]
    await asyncio.gather(*(store.create(j) for j in jobs))
    for job in jobs:
        retrieved = await store.get(job.id)
        assert retrieved == job
