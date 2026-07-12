import os

import pytest
from redis.asyncio import Redis

from klee_web.config import get_settings
from klee_web.jobs.telemetry import CeleryFleetTelemetry

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


async def test_snapshot_sees_the_live_worker(worker) -> None:
    from klee_web.celery_app import TASK_QUEUE, app

    client = Redis.from_url(_BROKER_URL)
    await client.flushdb()
    try:
        snapshot = await CeleryFleetTelemetry(app, client, TASK_QUEUE).snapshot()
        assert len(snapshot.workers) >= 1
        assert all(w.concurrency > 0 for w in snapshot.workers)
        assert snapshot.queue is not None
        assert snapshot.queue.name == TASK_QUEUE
        assert snapshot.queue.depth == 0
    finally:
        await client.aclose()


async def test_snapshot_reports_queue_backlog_with_no_workers() -> None:
    from klee_web.celery_app import TASK_QUEUE, app

    app.conf.update(broker_url=_BROKER_URL)
    client = Redis.from_url(_BROKER_URL)
    await client.flushdb()
    await client.rpush(TASK_QUEUE, "a", "b", "c")
    try:
        snapshot = await CeleryFleetTelemetry(app, client, TASK_QUEUE).snapshot()
        assert snapshot.workers == []
        assert snapshot.queue is not None
        assert snapshot.queue.depth == 3
    finally:
        await client.flushdb()
        await client.aclose()
