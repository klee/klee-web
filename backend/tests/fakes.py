import asyncio
from datetime import UTC, datetime
from uuid import UUID

from klee_web.jobs.store import JobNotFound
from klee_web.models import Job, JobOutcome, JobRequest, JobResult, JobStatus, UsageStats


class FakeJobStore:
    def __init__(self) -> None:
        self._jobs: dict[UUID, Job] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: Job) -> None:
        async with self._lock:
            self._jobs[job.id] = job

    async def get(self, job_id: UUID) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_status(self, job_id: UUID, status: JobStatus) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            job.status = status
            if status == JobStatus.running:
                job.started_at = datetime.now(UTC)

    async def set_partial_result(self, job_id: UUID, result: JobResult) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            job.result = result

    async def set_result(self, job_id: UUID, result: JobResult) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            job.result = result
            job.status = JobStatus.done

    async def request_cancel(self, job_id: UUID) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFound(job_id)
            job.cancel_requested = True


class FakeResultCache:
    def __init__(self) -> None:
        self._entries: dict[str, JobResult] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> JobResult | None:
        async with self._lock:
            return self._entries.get(key)

    async def set(self, key: str, result: JobResult) -> None:
        async with self._lock:
            self._entries[key] = result


class FakeUsageStatsStore:
    def __init__(self) -> None:
        self._outcomes: dict[JobOutcome, int] = {outcome: 0 for outcome in JobOutcome}
        self._cache_hits = 0
        self._test_cases = 0
        self._instructions = 0
        self._lock = asyncio.Lock()

    async def record_execution(
        self, outcome: JobOutcome, test_cases: int = 0, instructions: int = 0
    ) -> None:
        async with self._lock:
            self._outcomes[outcome] += 1
            self._test_cases += test_cases
            self._instructions += instructions

    async def record_cache_hit(self) -> None:
        async with self._lock:
            self._cache_hits += 1

    async def snapshot(self) -> UsageStats:
        async with self._lock:
            return UsageStats(
                outcomes=dict(self._outcomes),
                cache_hits=self._cache_hits,
                test_cases_generated=self._test_cases,
                instructions_executed=self._instructions,
            )


class FakeJobDispatcher:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, JobRequest]] = []

    async def dispatch(self, job_id: UUID, request: JobRequest) -> None:
        self.calls.append((job_id, request))
