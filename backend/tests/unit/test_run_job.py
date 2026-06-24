import asyncio
from uuid import UUID

from klee_web.jobs.run import run_job
from klee_web.jobs.runner import FakeKleeRunner, KleeRunnerError
from klee_web.models import HaltReason, Job, JobRequest, JobResult, JobStatus, KleeFlags, TestCase

SOURCE = "int main() { return 0; }"


async def _seed_job(store) -> Job:
    """run_job assumes create_job already inserted the job; seed it first."""
    job = Job()
    await store.create(job)
    return job


async def test_run_job_happy_path_advances_to_done_and_stores_result(store, runner, sample_result):
    job = await _seed_job(store)

    await run_job(job.id, JobRequest(source=SOURCE), store, runner)

    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.done
    assert stored.result == sample_result


async def test_run_job_passes_source_and_flags_to_runner(store, runner):
    job = await _seed_job(store)
    request = JobRequest(source=SOURCE, flags=KleeFlags(max_time=120, max_memory=256))

    await run_job(job.id, request, store, runner)

    assert len(runner.calls) == 1
    called_source, called_flags = runner.calls[0]
    assert called_source == SOURCE
    assert called_flags.max_time == 120
    assert called_flags.max_memory == 256


async def test_run_job_runner_failure_marks_job_failed(store):
    job = await _seed_job(store)
    runner = FakeKleeRunner(raise_exc=KleeRunnerError("KLEE crashed"))

    await run_job(job.id, JobRequest(source=SOURCE), store, runner)

    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.failed
    assert stored.result is None


async def test_run_job_streams_partial_result_while_running(store, sample_result):
    partial = JobResult(
        test_cases=[TestCase(name="partial", inputs={"x": "1"})],
        messages="",
        warnings="",
        stats={},
    )
    partial_emitted = asyncio.Event()
    finish = asyncio.Event()

    class BlockingRunner:
        async def execute(self, source, flags, job_id, on_progress=None, on_parsing=None):
            if on_progress is not None:
                await on_progress(partial)
            partial_emitted.set()
            await finish.wait()
            return sample_result

        async def cancel(self, job_id):
            return True

    job = await _seed_job(store)
    task = asyncio.create_task(run_job(job.id, JobRequest(source=SOURCE), store, BlockingRunner()))

    await partial_emitted.wait()
    mid = await store.get(job.id)
    assert mid is not None
    assert mid.status == JobStatus.running
    assert mid.result == partial

    finish.set()
    await task
    final = await store.get(job.id)
    assert final is not None
    assert final.status == JobStatus.done
    assert final.result == sample_result


async def test_run_job_flips_to_parsing_after_klee_exit(store, sample_result):
    parsing_signaled = asyncio.Event()
    finish = asyncio.Event()

    class ParsingRunner:
        async def execute(self, source, flags, job_id, on_progress=None, on_parsing=None):
            if on_parsing is not None:
                await on_parsing()
            parsing_signaled.set()
            await finish.wait()
            return sample_result

        async def cancel(self, job_id):
            return True

    job = await _seed_job(store)
    task = asyncio.create_task(run_job(job.id, JobRequest(source=SOURCE), store, ParsingRunner()))

    await parsing_signaled.wait()
    mid = await store.get(job.id)
    assert mid is not None
    assert mid.status == JobStatus.parsing

    finish.set()
    await task
    final = await store.get(job.id)
    assert final is not None
    assert final.status == JobStatus.done


async def test_run_job_short_circuits_when_cancelled_before_start(store, runner):
    job = await _seed_job(store)
    await store.request_cancel(job.id)

    await run_job(job.id, JobRequest(source=SOURCE), store, runner)

    assert runner.calls == []
    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.done
    assert stored.result is not None
    assert stored.result.halt_reason == HaltReason.cancelled
    assert stored.result.test_cases == []
    assert stored.result.stats == {}


async def test_run_job_cancel_watcher_signals_and_tags(store, sample_result, monkeypatch):
    monkeypatch.setattr("klee_web.jobs.run._CANCEL_POLL_SECONDS", 0.01)
    running = asyncio.Event()
    finish = asyncio.Event()
    cancel_calls: list[UUID] = []

    class CancellableRunner:
        async def execute(self, source, flags, job_id, on_progress=None, on_parsing=None):
            running.set()
            await finish.wait()
            return sample_result

        async def cancel(self, job_id):
            cancel_calls.append(job_id)
            return True

    job = await _seed_job(store)
    task = asyncio.create_task(
        run_job(job.id, JobRequest(source=SOURCE), store, CancellableRunner())
    )
    await running.wait()

    await store.request_cancel(job.id)
    for _ in range(200):
        if cancel_calls:
            break
        await asyncio.sleep(0.01)
    assert job.id in cancel_calls

    finish.set()
    await task
    stored = await store.get(job.id)
    assert stored is not None
    assert stored.result is not None
    assert stored.result.halt_reason == HaltReason.cancelled
