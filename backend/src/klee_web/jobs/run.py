import asyncio
import contextlib
from uuid import UUID

from klee_web.jobs.cache import ResultCache, cache_key
from klee_web.jobs.runner import KleeRunner, KleeRunnerError
from klee_web.jobs.store import JobStore
from klee_web.models import HaltReason, JobRequest, JobResult, JobStatus

_CANCEL_POLL_SECONDS = 1.0
_TERMINAL_STATUSES = frozenset({JobStatus.done, JobStatus.failed})
_MAX_ATTEMPTS = 3
_POISON_REASON = (
    "Gave up after 3 attempts: a worker repeatedly stopped before finishing this job. "
    "Resubmit to try again."
)


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
    cache: ResultCache | None = None,
) -> None:
    job = await store.get(job_id)
    if job is not None and job.status in _TERMINAL_STATUSES:
        return  # a redelivery of an already-finished job must not re-run KLEE

    if job is not None and job.cancel_requested:
        await store.set_result(job_id, _cancelled_result())
        return

    attempts = await store.increment_attempts(job_id)
    if attempts > _MAX_ATTEMPTS:
        await store.set_failed(job_id, _POISON_REASON)
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
        if cache is not None and result.halt_reason == HaltReason.completed:
            await cache.set(cache_key(request), result)
    except KleeRunnerError:
        await store.update_status(job_id, JobStatus.failed)
    finally:
        watcher.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watcher
