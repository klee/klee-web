from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from klee_web.api.admin import router as admin_router
from klee_web.deps import get_telemetry, get_usage_stats
from klee_web.jobs.usage import InMemoryUsageStatsStore
from klee_web.models import JobOutcome, QueueTelemetry, Telemetry, UsageStats, WorkerTelemetry


class FakeFleetTelemetry:
    def __init__(self, telemetry: Telemetry) -> None:
        self._telemetry = telemetry

    async def snapshot(self) -> Telemetry:
        return self._telemetry


def make_client(telemetry: Telemetry) -> AsyncClient:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_telemetry] = lambda: FakeFleetTelemetry(telemetry)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_telemetry_returns_workers_and_queue() -> None:
    telemetry = Telemetry(
        workers=[WorkerTelemetry(name="worker1@host", concurrency=4, active=2, reserved=1)],
        queue=QueueTelemetry(name="klee-jobs", depth=3),
    )
    async with make_client(telemetry) as client:
        response = await client.get("/admin/telemetry")
    assert response.status_code == 200
    assert response.json() == {
        "workers": [{"name": "worker1@host", "concurrency": 4, "active": 2, "reserved": 1}],
        "queue": {"name": "klee-jobs", "depth": 3},
    }


async def test_telemetry_empty_fleet_in_process() -> None:
    async with make_client(Telemetry(workers=[], queue=None)) as client:
        response = await client.get("/admin/telemetry")
    assert response.status_code == 200
    assert response.json() == {"workers": [], "queue": None}


async def test_telemetry_reports_dead_fleet_with_backlog() -> None:
    # The alarm state: no worker answered, but jobs are still piling up in the queue.
    telemetry = Telemetry(workers=[], queue=QueueTelemetry(name="klee-jobs", depth=5))
    async with make_client(telemetry) as client:
        response = await client.get("/admin/telemetry")
    assert response.status_code == 200
    body = response.json()
    assert body["workers"] == []
    assert body["queue"]["depth"] == 5


def make_stats_client(usage: InMemoryUsageStatsStore) -> AsyncClient:
    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_usage_stats] = lambda: usage
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_stats_returns_the_usage_snapshot() -> None:
    usage = InMemoryUsageStatsStore()
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
    async with make_stats_client(InMemoryUsageStatsStore()) as client:
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
