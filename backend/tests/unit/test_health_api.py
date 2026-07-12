from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from klee_web.api.health import router as health_router
from klee_web.deps import get_readiness


class StubReadiness:
    def __init__(self, ready: bool) -> None:
        self._ready = ready

    async def is_ready(self) -> bool:
        return self._ready


def make_client(ready: bool) -> AsyncClient:
    app = FastAPI()
    app.include_router(health_router)
    app.dependency_overrides[get_readiness] = lambda: StubReadiness(ready)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health_reports_up() -> None:
    async with make_client(ready=True) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "up"}


async def test_ready_when_dependencies_reachable() -> None:
    async with make_client(ready=True) as client:
        response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_not_ready_when_dependency_unreachable() -> None:
    async with make_client(ready=False) as client:
        response = await client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
