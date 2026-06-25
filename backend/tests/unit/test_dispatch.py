import asyncio

from klee_web.jobs.dispatch import InProcessDispatcher, drain
from klee_web.models import Job, JobRequest, JobStatus

SOURCE = "int main() { return 0; }"


async def test_in_process_dispatcher_runs_job_in_background(store, runner, cache, sample_result):
    job = Job()
    await store.create(job)
    dispatcher = InProcessDispatcher(store, runner, cache)

    await dispatcher.dispatch(job.id, JobRequest(source=SOURCE))
    await drain()

    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.done
    assert stored.result == sample_result


async def test_dispatch_does_not_block_on_the_job(store, cache, sample_result):
    entered = asyncio.Event()
    finish = asyncio.Event()

    class BlockingRunner:
        async def execute(self, source, flags, job_id, on_progress=None, on_parsing=None):
            entered.set()
            await finish.wait()
            return sample_result

        async def cancel(self, job_id):
            return True

    job = Job()
    await store.create(job)
    dispatcher = InProcessDispatcher(store, BlockingRunner(), cache)

    await dispatcher.dispatch(job.id, JobRequest(source=SOURCE))
    await entered.wait()
    mid = await store.get(job.id)
    assert mid is not None
    assert mid.status == JobStatus.running

    finish.set()
    await drain()
    final = await store.get(job.id)
    assert final is not None
    assert final.status == JobStatus.done
