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


class CapacityAboveLimit(ValueError):
    def __init__(self, requested: int, maximum: int) -> None:
        self.requested = requested
        self.maximum = maximum
        super().__init__(f"requested capacity {requested} exceeds deployment maximum {maximum}")


class WorkerUnavailable(RuntimeError):
    pass


class WorkerControlRejected(RuntimeError):
    pass


class FleetControl(Protocol):
    async def set_max_concurrency(self, worker_name: str, maximum: int) -> None: ...


class UnavailableFleetControl:
    async def set_max_concurrency(self, worker_name: str, maximum: int) -> None:
        raise WorkerUnavailable(worker_name)


class CeleryFleetControl:
    def __init__(self, celery_app: Celery, maximum: int) -> None:
        self._app = celery_app
        self._maximum = maximum

    async def set_max_concurrency(self, worker_name: str, maximum: int) -> None:
        if maximum > self._maximum:
            raise CapacityAboveLimit(maximum, self._maximum)

        replies = await asyncio.to_thread(
            self._app.control.autoscale,
            max=maximum,
            min=1,
            destination=[worker_name],
            reply=True,
            timeout=_INSPECT_TIMEOUT_SECONDS,
        )
        if not replies:
            raise WorkerUnavailable(worker_name)

        reply = None
        for item in replies:
            if not isinstance(item, dict):
                raise WorkerControlRejected("Unexpected Celery reply")
            if worker_name in item:
                worker_reply = item[worker_name]
                if not isinstance(worker_reply, dict):
                    raise WorkerControlRejected("Unexpected Celery reply")
                reply = worker_reply
                break
        if reply is None:
            raise WorkerUnavailable(worker_name)
        if "error" in reply:
            raise WorkerControlRejected(reply["error"])
        if "ok" not in reply:
            raise WorkerControlRejected("Unexpected Celery reply")


def build_worker_telemetry(
    stats: dict[str, Any] | None,
    active: dict[str, Any] | None,
    reserved: dict[str, Any] | None,
) -> list[WorkerTelemetry]:
    stats = stats or {}
    active = active or {}
    reserved = reserved or {}
    workers = []
    for name, info in stats.items():
        pool_concurrency = info.get("pool", {}).get("max-concurrency", 0)
        autoscaler = info.get("autoscaler")
        current = autoscaler["current"] if autoscaler else pool_concurrency
        maximum = autoscaler["max"] if autoscaler else pool_concurrency
        workers.append(
            WorkerTelemetry(
                name=name,
                concurrency=current,
                max_concurrency=maximum,
                active=len(active.get(name, [])),
                reserved=len(reserved.get(name, [])),
            )
        )
    return workers


class NullFleetTelemetry:
    def __init__(self, max_worker_concurrency: int) -> None:
        self._max_worker_concurrency = max_worker_concurrency

    async def snapshot(self) -> Telemetry:
        return Telemetry(
            max_worker_concurrency=self._max_worker_concurrency,
            workers=[],
            queue=None,
        )


class CeleryFleetTelemetry:
    def __init__(
        self,
        celery_app: Celery,
        redis: Redis,
        queue_name: str,
        max_worker_concurrency: int,
    ) -> None:
        self._app = celery_app
        self._redis = redis
        self._queue_name = queue_name
        self._max_worker_concurrency = max_worker_concurrency

    async def snapshot(self) -> Telemetry:
        workers = await asyncio.to_thread(self._inspect_workers)
        queue = await self._queue_snapshot()
        return Telemetry(
            max_worker_concurrency=self._max_worker_concurrency,
            workers=workers,
            queue=queue,
        )

    def _inspect_workers(self) -> list[WorkerTelemetry]:
        inspect = self._app.control.inspect(timeout=_INSPECT_TIMEOUT_SECONDS)
        return build_worker_telemetry(inspect.stats(), inspect.active(), inspect.reserved())

    async def _queue_snapshot(self) -> QueueTelemetry | None:
        try:
            depth = int(await self._redis.llen(self._queue_name))
        except (RedisError, OSError):
            return None
        return QueueTelemetry(name=self._queue_name, depth=depth)
