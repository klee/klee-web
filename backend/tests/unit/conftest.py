import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from klee_web.api.jobs import router as jobs_router
from klee_web.deps import get_cache, get_dispatcher, get_job_store, get_usage_stats
from klee_web.models import JobResult, SymbolicInput, TestCase
from tests.fakes import (
    FakeJobDispatcher,
    FakeJobStore,
    FakeKleeRunner,
    FakeResultCache,
    FakeUsageStatsStore,
)


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


@pytest.fixture
def store() -> FakeJobStore:
    return FakeJobStore()


@pytest.fixture
def runner(sample_result) -> FakeKleeRunner:
    return FakeKleeRunner(canned_result=sample_result)


@pytest.fixture
def cache() -> FakeResultCache:
    return FakeResultCache()


@pytest.fixture
def usage() -> FakeUsageStatsStore:
    return FakeUsageStatsStore()


@pytest.fixture
def dispatcher() -> FakeJobDispatcher:
    return FakeJobDispatcher()


@pytest.fixture
def app(store, cache, usage, dispatcher) -> FastAPI:
    app = FastAPI()
    app.include_router(jobs_router)
    app.dependency_overrides[get_job_store] = lambda: store
    app.dependency_overrides[get_dispatcher] = lambda: dispatcher
    app.dependency_overrides[get_cache] = lambda: cache
    app.dependency_overrides[get_usage_stats] = lambda: usage
    return app


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
