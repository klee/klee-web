import asyncio
import os
import subprocess
import sys
import time

import pytest
import redis as redis_sync
from redis.asyncio import Redis

from klee_web.config import get_settings
from klee_web.jobs.telemetry import CeleryFleetControl, CeleryFleetTelemetry

_STORE_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
_AUTOSCALE_WORKER_NAME = "autoscale@localhost"


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


@pytest.fixture
def autoscale_worker():
    from tests.integration.autoscale_app import RELEASE_KEY, app

    broker = redis_sync.Redis.from_url(_BROKER_URL)
    broker.flushdb()
    broker.close()

    env = os.environ.copy()
    env["CELERY_BROKER_URL"] = _BROKER_URL
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "tests.integration.autoscale_app",
            "worker",
            "-Q",
            "klee-jobs",
            "--pool=prefork",
            "--autoscale=4,1",
            f"--hostname={_AUTOSCALE_WORKER_NAME}",
            "--loglevel=warning",
        ],
        env=env,
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if app.control.ping(destination=[_AUTOSCALE_WORKER_NAME], timeout=0.5):
                break
            if process.poll() is not None:
                raise RuntimeError("autoscale worker exited during startup")
        else:
            raise RuntimeError("autoscale worker did not start")
        yield app
    finally:
        broker = redis_sync.Redis.from_url(_BROKER_URL)
        broker.set(RELEASE_KEY, "1")
        broker.close()
        app.control.shutdown(destination=[_AUTOSCALE_WORKER_NAME])
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=5)


async def wait_for_worker(telemetry, worker_name, predicate, timeout: float = 15):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await telemetry.snapshot()
        for worker in snapshot.workers:
            if worker.name == worker_name and predicate(worker):
                return worker
        await asyncio.sleep(0.1)
    raise AssertionError("worker telemetry did not reach the expected state")


async def test_snapshot_sees_the_live_worker(worker) -> None:
    from klee_web.celery_app import TASK_QUEUE, app

    client = Redis.from_url(_BROKER_URL)
    await client.flushdb()
    try:
        snapshot = await CeleryFleetTelemetry(app, client, TASK_QUEUE, 4).snapshot()
        assert snapshot.max_worker_concurrency == 4
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
        snapshot = await CeleryFleetTelemetry(app, client, TASK_QUEUE, 4).snapshot()
        assert snapshot.max_worker_concurrency == 4
        assert snapshot.workers == []
        assert snapshot.queue is not None
        assert snapshot.queue.depth == 3
    finally:
        await client.flushdb()
        await client.aclose()


async def test_autoscaler_defers_lower_capacity_until_jobs_finish(autoscale_worker) -> None:
    from klee_web.celery_app import TASK_QUEUE
    from tests.integration.autoscale_app import RELEASE_KEY

    client = Redis.from_url(_BROKER_URL)
    telemetry = CeleryFleetTelemetry(autoscale_worker, client, TASK_QUEUE, 4)
    try:
        await wait_for_worker(
            telemetry,
            _AUTOSCALE_WORKER_NAME,
            lambda worker: worker.concurrency == 1 and worker.max_concurrency == 4,
        )

        for _ in range(4):
            autoscale_worker.send_task("autoscale_probe", queue=TASK_QUEUE)

        await wait_for_worker(
            telemetry,
            _AUTOSCALE_WORKER_NAME,
            lambda worker: worker.concurrency == 4 and worker.active == 4,
        )
        await CeleryFleetControl(autoscale_worker, maximum=4).set_max_concurrency(
            _AUTOSCALE_WORKER_NAME,
            2,
        )

        lowered = await wait_for_worker(
            telemetry,
            _AUTOSCALE_WORKER_NAME,
            lambda worker: worker.max_concurrency == 2,
        )
        assert lowered.concurrency == 4
        assert lowered.active == 4

        await client.set(RELEASE_KEY, "1")
        settled = await wait_for_worker(
            telemetry,
            _AUTOSCALE_WORKER_NAME,
            lambda worker: worker.active == 0 and worker.concurrency <= 2,
        )
        assert settled.max_concurrency == 2
    finally:
        await client.set(RELEASE_KEY, "1")
        await client.flushdb()
        await client.aclose()
