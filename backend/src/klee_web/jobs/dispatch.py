from typing import Protocol
from uuid import UUID

from klee_web.models import JobRequest


class JobDispatcher(Protocol):
    async def dispatch(self, job_id: UUID, request: JobRequest) -> None: ...


# Hard per-task ceiling above the job's own budget. The Celery supervisor enforces it, so
# it SIGKILLs and respawns a frozen worker whose own timers cannot fire. Sits above the
# entrypoint bound (ADR-0018, minimal failsafes).
_TASK_TIME_LIMIT_MARGIN = 60


class CeleryDispatcher:
    async def dispatch(self, job_id: UUID, request: JobRequest) -> None:
        from klee_web.celery_app import run_klee_job

        run_klee_job.apply_async(
            args=(str(job_id), request.model_dump(mode="json")),
            time_limit=request.flags.max_time + _TASK_TIME_LIMIT_MARGIN,
        )
