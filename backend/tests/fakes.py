import asyncio
from datetime import UTC, datetime
from uuid import UUID

from klee_web.jobs.runner import OnParsing, OnProgress
from klee_web.jobs.store import JobNotFound
from klee_web.models import (
    HaltReason,
    Job,
    JobOutcome,
    JobRequest,
    JobResult,
    JobStatus,
    KleeFlags,
    SymbolicInput,
    TestCase,
    UsageStats,
)


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


class FakeKleeRunner:
    def __init__(
        self,
        canned_result: JobResult | None = None,
        raise_exc: Exception | None = None,
        cancel_returns: bool = True,
    ) -> None:
        self._canned_result = canned_result
        self._raise_exc = raise_exc
        self._cancel_returns = cancel_returns
        self.calls: list[tuple[str, KleeFlags]] = []
        self.cancel_calls: list[UUID] = []

    async def execute(
        self,
        source: str,
        flags: KleeFlags,
        job_id: UUID,
        on_progress: OnProgress | None = None,
        on_parsing: OnParsing | None = None,
    ) -> JobResult:
        self.calls.append((source, flags))
        if self._raise_exc is not None:
            raise self._raise_exc
        if self._canned_result is None:
            raise RuntimeError("FakeKleeRunner needs either canned_result or raise_exc")
        if on_progress is not None:
            await on_progress(self._canned_result)
        if on_parsing is not None:
            await on_parsing()
        return self._canned_result

    async def cancel(self, job_id: UUID) -> bool:
        self.cancel_calls.append(job_id)
        return self._cancel_returns


def get_sign_result(klee_version: str | None = None) -> JobResult:
    return JobResult(
        test_cases=[
            TestCase(
                name="test000001", inputs=[SymbolicInput(name="a", value="0", bytes_hex="00000000")]
            ),
            TestCase(
                name="test000002",
                inputs=[SymbolicInput(name="a", value="16843009", bytes_hex="01010101")],
            ),
            TestCase(
                name="test000003",
                inputs=[SymbolicInput(name="a", value="-2147483648", bytes_hex="00000080")],
            ),
        ],
        messages="KLEE: done: completed paths = 3\nKLEE: done: generated tests = 3",
        warnings="",
        stats={"Instructions": 100, "NumStates": 1, "FullBranches": 2, "WallTime": 0},
        halt_reason=HaltReason.completed,
        klee_version=klee_version,
    )
