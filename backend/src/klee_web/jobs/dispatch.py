import asyncio
from typing import Protocol
from uuid import UUID

from klee_web.jobs.run import run_job
from klee_web.jobs.runner import KleeRunner
from klee_web.jobs.store import JobStore
from klee_web.models import JobRequest


class JobDispatcher(Protocol):
    async def dispatch(self, job_id: UUID, request: JobRequest) -> None: ...


# Strong references to in-flight background jobs. Without this, asyncio may
# garbage-collect a task whose only reference was create_task's return value,
# killing the job mid-execution. Tasks remove themselves on completion.
_background_tasks: set[asyncio.Task[None]] = set()


class InProcessDispatcher:
    def __init__(self, store: JobStore, runner: KleeRunner) -> None:
        self._store = store
        self._runner = runner

    async def dispatch(self, job_id: UUID, request: JobRequest) -> None:
        task = asyncio.create_task(run_job(job_id, request, self._store, self._runner))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)


class CeleryDispatcher:
    async def dispatch(self, job_id: UUID, request: JobRequest) -> None:
        from klee_web.celery_app import run_klee_job

        run_klee_job.delay(str(job_id), request.model_dump(mode="json"))


async def drain() -> None:
    """Await all in-flight in-process jobs (used by tests and graceful shutdown)."""
    await asyncio.gather(*list(_background_tasks), return_exceptions=True)
