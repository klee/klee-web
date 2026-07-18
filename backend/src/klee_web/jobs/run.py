import asyncio
import contextlib
from uuid import UUID

from klee_web.jobs.cache import ResultCache, cache_key
from klee_web.jobs.runner import KleeRunner, KleeRunnerError
from klee_web.jobs.store import JobStore
from klee_web.jobs.usage import UsageStatsStore
from klee_web.models import (
    HaltReason,
    JobOutcome,
    JobRequest,
    JobResult,
    JobStatus,
    outcome_of_result,
)

_CANCEL_POLL_SECONDS = 1.0


def _cancelled_result() -> JobResult:
    """A job cancelled before KLEE ran: nothing produced, halted by the cancel."""
    return JobResult(
        test_cases=[],
        messages="",
        warnings="",
        stats={},
        halt_reason=HaltReason.cancelled,
    )


async def run_job(
    job_id: UUID,
    request: JobRequest,
    store: JobStore,
    runner: KleeRunner,
    cache: ResultCache,
    usage: UsageStatsStore,
) -> None:
    async def record_outcome(outcome: JobOutcome, result: JobResult | None = None) -> None:
        await usage.record_execution(
            outcome,
            test_cases=len(result.test_cases) if result is not None else 0,
            instructions=result.stats.get("Instructions", 0) if result is not None else 0,
        )

    job = await store.get(job_id)
    if job is not None and job.cancel_requested:
        await store.set_result(job_id, _cancelled_result())
        await record_outcome(JobOutcome.cancelled)
        return

    await store.update_status(job_id, JobStatus.running)

    async def on_progress(partial: JobResult) -> None:
        await store.set_partial_result(job_id, partial)

    async def on_parsing() -> None:
        await store.update_status(job_id, JobStatus.parsing)

    async def watch_cancel() -> None:
        while True:
            await asyncio.sleep(_CANCEL_POLL_SECONDS)
            current = await store.get(job_id)
            if current is not None and current.cancel_requested:
                await runner.cancel(job_id)

    watcher = asyncio.create_task(watch_cancel())
    try:
        result = await runner.execute(
            request.source,
            request.flags,
            job_id,
            on_progress=on_progress,
            on_parsing=on_parsing,
        )
        job = await store.get(job_id)
        if job is not None and job.cancel_requested:
            result.halt_reason = HaltReason.cancelled
        await store.set_result(job_id, result)
        if result.halt_reason == HaltReason.completed:
            await cache.set(cache_key(request), result)
        await record_outcome(outcome_of_result(result), result)
    except KleeRunnerError:
        await store.update_status(job_id, JobStatus.failed)
        await record_outcome(JobOutcome.failed)
    finally:
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher
