from typing import Any, cast

import pytest

from klee_web.jobs.telemetry import (
    CapacityAboveLimit,
    CeleryFleetControl,
    WorkerControlRejected,
    WorkerUnavailable,
)


class FakeCeleryControl:
    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def autoscale(self, **kwargs):
        self.calls.append(kwargs)
        return self.replies


class FakeCeleryApp:
    def __init__(self, replies):
        self.control = FakeCeleryControl(replies)


async def test_sets_one_workers_maximum_capacity() -> None:
    app = FakeCeleryApp([{"worker1@host": {"ok": "autoscale now max=3 min=1"}}])
    control = CeleryFleetControl(cast(Any, app), maximum=4)

    await control.set_max_concurrency("worker1@host", 3)

    assert app.control.calls == [
        {
            "max": 3,
            "min": 1,
            "destination": ["worker1@host"],
            "reply": True,
            "timeout": 1.0,
        }
    ]


async def test_rejects_capacity_above_deployment_maximum() -> None:
    app = FakeCeleryApp([])
    control = CeleryFleetControl(cast(Any, app), maximum=4)

    with pytest.raises(CapacityAboveLimit):
        await control.set_max_concurrency("worker1@host", 5)

    assert app.control.calls == []


async def test_reports_worker_that_does_not_reply() -> None:
    control = CeleryFleetControl(cast(Any, FakeCeleryApp([])), maximum=4)

    with pytest.raises(WorkerUnavailable):
        await control.set_max_concurrency("worker1@host", 2)


async def test_reports_celery_rejection() -> None:
    app = FakeCeleryApp([{"worker1@host": {"error": "Autoscale not enabled"}}])
    control = CeleryFleetControl(cast(Any, app), maximum=4)

    with pytest.raises(WorkerControlRejected, match="Autoscale not enabled"):
        await control.set_max_concurrency("worker1@host", 2)


async def test_reports_none_as_worker_unavailable() -> None:
    control = CeleryFleetControl(cast(Any, FakeCeleryApp(None)), maximum=4)

    with pytest.raises(WorkerUnavailable):
        await control.set_max_concurrency("worker1@host", 2)


async def test_rejects_reply_without_ok_or_error() -> None:
    app = FakeCeleryApp([{"worker1@host": {}}])
    control = CeleryFleetControl(cast(Any, app), maximum=4)

    with pytest.raises(WorkerControlRejected, match="Unexpected Celery reply"):
        await control.set_max_concurrency("worker1@host", 2)


async def test_rejects_non_dictionary_reply_item() -> None:
    control = CeleryFleetControl(cast(Any, FakeCeleryApp([None])), maximum=4)

    with pytest.raises(WorkerControlRejected, match="Unexpected Celery reply"):
        await control.set_max_concurrency("worker1@host", 2)


async def test_rejects_non_dictionary_worker_reply() -> None:
    app = FakeCeleryApp([{"worker1@host": None}])
    control = CeleryFleetControl(cast(Any, app), maximum=4)

    with pytest.raises(WorkerControlRejected, match="Unexpected Celery reply"):
        await control.set_max_concurrency("worker1@host", 2)
