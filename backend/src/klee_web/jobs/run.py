from uuid import UUID

from klee_web.jobs.runner import KleeRunner, KleeRunnerError
from klee_web.jobs.store import JobStore
from klee_web.models import HaltReason, JobRequest, JobResult, JobStatus


async def run_job(
    job_id: UUID,
    request: JobRequest,
    store: JobStore,
    runner: KleeRunner,
) -> None:
    await store.update_status(job_id, JobStatus.running)

    async def on_progress(partial: JobResult) -> None:
        await store.set_partial_result(job_id, partial)

    async def on_parsing() -> None:
        await store.update_status(job_id, JobStatus.parsing)

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
    except KleeRunnerError:
        await store.update_status(job_id, JobStatus.failed)
