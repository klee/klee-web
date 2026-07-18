import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from klee_web.api.admin import router as admin_router
from klee_web.deps import get_fleet_control, get_telemetry, get_usage_stats
from klee_web.jobs.telemetry import (
    CapacityAboveLimit,
    WorkerControlRejected,
    WorkerUnavailable,
)
from klee_web.models import JobOutcome, QueueTelemetry, Telemetry, UsageStats, WorkerTelemetry
from tests.fakes import FakeUsageStatsStore


class FakeFleetTelemetry:
    def __init__(self, telemetry: Telemetry) -> None:
        self._telemetry = telemetry

    async def snapshot(self) -> Telemetry:
        return self._telemetry


class FakeFleetControl:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, int]] = []

    async def set_max_concurrency(self, worker_name: str, maximum: int) -> None:
        self.calls.append((worker_name, maximum))
        if self.error:
            raise self.error


def make_client(telemetry: Telemetry) -> AsyncClient:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_telemetry] = lambda: FakeFleetTelemetry(telemetry)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_telemetry_returns_workers_and_queue() -> None:
    telemetry = Telemetry(
        max_worker_concurrency=4,
        workers=[
            WorkerTelemetry(
                name="worker1@host",
                concurrency=4,
                max_concurrency=4,
                active=2,
                reserved=1,
            )
        ],
        queue=QueueTelemetry(name="klee-jobs", depth=3),
    )
    async with make_client(telemetry) as client:
        response = await client.get("/admin/telemetry")
    assert response.status_code == 200
    assert response.json() == {
        "max_worker_concurrency": 4,
        "workers": [
            {
                "name": "worker1@host",
                "concurrency": 4,
                "max_concurrency": 4,
                "active": 2,
                "reserved": 1,
            }
        ],
        "queue": {"name": "klee-jobs", "depth": 3},
    }


async def test_telemetry_empty_fleet() -> None:
    async with make_client(Telemetry(max_worker_concurrency=4, workers=[], queue=None)) as client:
        response = await client.get("/admin/telemetry")
    assert response.status_code == 200
    assert response.json() == {"max_worker_concurrency": 4, "workers": [], "queue": None}


async def test_telemetry_reports_dead_fleet_with_backlog() -> None:
    # The alarm state: no worker answered, but jobs are still piling up in the queue.
    telemetry = Telemetry(
        max_worker_concurrency=4,
        workers=[],
        queue=QueueTelemetry(name="klee-jobs", depth=5),
    )
    async with make_client(telemetry) as client:
        response = await client.get("/admin/telemetry")
    assert response.status_code == 200
    body = response.json()
    assert body["workers"] == []
    assert body["queue"]["depth"] == 5


def make_stats_client(usage: FakeUsageStatsStore) -> AsyncClient:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_usage_stats] = lambda: usage
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_stats_returns_the_usage_snapshot() -> None:
    usage = FakeUsageStatsStore()
    await usage.record_execution(JobOutcome.completed, test_cases=4, instructions=900)
    await usage.record_execution(JobOutcome.max_time)
    await usage.record_cache_hit()

    async with make_stats_client(usage) as client:
        response = await client.get("/admin/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["outcomes"]["completed"] == 1
    assert body["outcomes"]["max_time"] == 1
    assert body["outcomes"]["failed"] == 0
    assert body["cache_hits"] == 1
    assert body["test_cases_generated"] == 4
    assert body["instructions_executed"] == 900


async def test_stats_empty_snapshot_is_zero_filled() -> None:
    async with make_stats_client(FakeUsageStatsStore()) as client:
        response = await client.get("/admin/stats")
    assert response.status_code == 200
    body = response.json()
    assert set(body["outcomes"]) == {o.value for o in JobOutcome}
    assert body == UsageStats(
        outcomes={o: 0 for o in JobOutcome},
        cache_hits=0,
        test_cases_generated=0,
        instructions_executed=0,
    ).model_dump(mode="json")


def make_control_client(control: FakeFleetControl) -> AsyncClient:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_fleet_control] = lambda: control
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_worker_capacity_openapi_declares_runtime_errors() -> None:
    app = FastAPI()
    app.include_router(admin_router)

    responses = app.openapi()["paths"]["/admin/workers/{worker_name}/capacity"]["patch"][
        "responses"
    ]

    assert set(responses) == {"204", "409", "422", "503"}
    for status_code in ("409", "503"):
        schema = responses[status_code]["content"]["application/json"]["schema"]
        assert schema["$ref"] == "#/components/schemas/ErrorResponse"


async def test_set_worker_capacity_targets_named_worker() -> None:
    control = FakeFleetControl()
    async with make_control_client(control) as client:
        response = await client.patch(
            "/admin/workers/worker1@host/capacity",
            json={"max_concurrency": 3},
        )

    assert response.status_code == 204
    assert control.calls == [("worker1@host", 3)]


async def test_set_worker_capacity_rejects_above_deployment_maximum() -> None:
    control = FakeFleetControl(CapacityAboveLimit(5, 4))
    async with make_control_client(control) as client:
        response = await client.patch(
            "/admin/workers/worker1@host/capacity",
            json={"max_concurrency": 5},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Maximum worker capacity is 4"}


async def test_set_worker_capacity_reports_unavailable_worker() -> None:
    control = FakeFleetControl(WorkerUnavailable("worker1@host"))
    async with make_control_client(control) as client:
        response = await client.patch(
            "/admin/workers/worker1@host/capacity",
            json={"max_concurrency": 3},
        )

    assert response.status_code == 503


async def test_set_worker_capacity_reports_celery_rejection() -> None:
    control = FakeFleetControl(WorkerControlRejected("Autoscale not enabled"))
    async with make_control_client(control) as client:
        response = await client.patch(
            "/admin/workers/worker1@host/capacity",
            json={"max_concurrency": 3},
        )

    assert response.status_code == 409


@pytest.mark.parametrize("invalid_capacity", [0, True])
async def test_set_worker_capacity_rejects_invalid_integer(invalid_capacity: int | bool) -> None:
    control = FakeFleetControl()
    async with make_control_client(control) as client:
        response = await client.patch(
            "/admin/workers/worker1@host/capacity",
            json={"max_concurrency": invalid_capacity},
        )

    assert response.status_code == 422
    assert control.calls == []
