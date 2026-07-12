from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from klee_web.models import QueueTelemetry, Telemetry, WorkerTelemetry

if TYPE_CHECKING:
    from celery import Celery

_INSPECT_TIMEOUT_SECONDS = 1.0


class FleetTelemetry(Protocol):
    async def snapshot(self) -> Telemetry: ...


def build_worker_telemetry(
    stats: dict[str, Any] | None,
    active: dict[str, Any] | None,
    reserved: dict[str, Any] | None,
) -> list[WorkerTelemetry]:
    stats = stats or {}
    active = active or {}
    reserved = reserved or {}
    return [
        WorkerTelemetry(
            name=name,
            concurrency=info.get("pool", {}).get("max-concurrency", 0),
            active=len(active.get(name, [])),
            reserved=len(reserved.get(name, [])),
        )
        for name, info in stats.items()
    ]


class NullFleetTelemetry:
    async def snapshot(self) -> Telemetry:
        return Telemetry(workers=[], queue=None)


class CeleryFleetTelemetry:
    def __init__(self, celery_app: Celery, redis: Redis, queue_name: str) -> None:
        self._app = celery_app
        self._redis = redis
        self._queue_name = queue_name

    async def snapshot(self) -> Telemetry:
        workers = await asyncio.to_thread(self._inspect_workers)
        queue = await self._queue_snapshot()
        return Telemetry(workers=workers, queue=queue)

    def _inspect_workers(self) -> list[WorkerTelemetry]:
        inspect = self._app.control.inspect(timeout=_INSPECT_TIMEOUT_SECONDS)
        return build_worker_telemetry(inspect.stats(), inspect.active(), inspect.reserved())

    async def _queue_snapshot(self) -> QueueTelemetry | None:
        try:
            depth = int(await self._redis.llen(self._queue_name))
        except (RedisError, OSError):
            return None
        return QueueTelemetry(name=self._queue_name, depth=depth)
