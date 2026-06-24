import asyncio
import os

import pytest
from redis.asyncio import Redis

from klee_web.config import get_settings
from klee_web.jobs.dispatch import CeleryDispatcher
from klee_web.jobs.fake_data import get_sign_result
from klee_web.jobs.store import RedisJobStore
from klee_web.models import Job, JobRequest, JobStatus

_STORE_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")


def _redis_ready() -> bool:
    import redis

    try:
        client = redis.Redis.from_url(_STORE_URL, socket_connect_timeout=1)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _redis_ready(),
    reason=f"redis not reachable at {_STORE_URL}",
)


@pytest.fixture
def worker(monkeypatch):
    """A real Celery worker in a background thread, consuming our queue against Redis."""
    monkeypatch.setenv("REDIS_URL", _STORE_URL)
    monkeypatch.setenv("CELERY_BROKER_URL", _BROKER_URL)
    monkeypatch.setenv("KLEE_FAKE_RUNNER", "1")
    get_settings.cache_clear()

    from celery.contrib.testing.worker import start_worker

    from klee_web.celery_app import app

    app.conf.broker_url = _BROKER_URL
    with start_worker(app, perform_ping_check=False):
        yield
    get_settings.cache_clear()


async def test_enqueued_job_runs_on_the_worker_and_lands_in_the_store(worker):
    client = Redis.from_url(_STORE_URL)
    await client.flushdb()
    store = RedisJobStore(client)
    try:
        job = Job()
        await store.create(job)

        await CeleryDispatcher().dispatch(job.id, JobRequest(source="int main(){}"))

        stored = None
        for _ in range(100):
            stored = await store.get(job.id)
            assert stored is not None
            if stored.status == JobStatus.done:
                break
            await asyncio.sleep(0.1)
        else:
            pytest.fail("worker did not finish the job within the timeout")

        assert stored is not None
        assert stored.status == JobStatus.done
        assert stored.result == get_sign_result()
    finally:
        await client.flushdb()
        await client.aclose()
