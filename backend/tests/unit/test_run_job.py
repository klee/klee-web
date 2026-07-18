import asyncio
from uuid import UUID

from klee_web.jobs.cache import cache_key
from klee_web.jobs.run import run_job
from klee_web.jobs.runner import KleeRunnerError
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
)
from tests.fakes import FakeKleeRunner

SOURCE = "int main() { return 0; }"


async def _seed_job(store) -> Job:
    """run_job assumes create_job already inserted the job; seed it first."""
    job = Job()
    await store.create(job)
    return job


async def test_run_job_happy_path_advances_to_done_and_stores_result(
    store, runner, cache, usage, sample_result
):
    job = await _seed_job(store)

    await run_job(job.id, JobRequest(source=SOURCE), store, runner, cache, usage)

    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.done
    assert stored.result == sample_result


async def test_run_job_passes_source_and_flags_to_runner(store, runner, cache, usage):
    job = await _seed_job(store)
    request = JobRequest(source=SOURCE, flags=KleeFlags(max_time=120, max_memory=256))

    await run_job(job.id, request, store, runner, cache, usage)

    assert len(runner.calls) == 1
    called_source, called_flags = runner.calls[0]
    assert called_source == SOURCE
    assert called_flags.max_time == 120
    assert called_flags.max_memory == 256


async def test_run_job_runner_failure_marks_job_failed(store, cache, usage):
    job = await _seed_job(store)
    runner = FakeKleeRunner(raise_exc=KleeRunnerError("KLEE crashed"))

    await run_job(job.id, JobRequest(source=SOURCE), store, runner, cache, usage)

    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.failed
    assert stored.result is None


async def test_run_job_streams_partial_result_while_running(store, cache, usage, sample_result):
    partial = JobResult(
        test_cases=[
            TestCase(
                name="partial", inputs=[SymbolicInput(name="x", value="1", bytes_hex="01000000")]
            )
        ],
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
    task = asyncio.create_task(
        run_job(job.id, JobRequest(source=SOURCE), store, BlockingRunner(), cache, usage)
    )

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


async def test_run_job_flips_to_parsing_after_klee_exit(store, cache, usage, sample_result):
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
    task = asyncio.create_task(
        run_job(job.id, JobRequest(source=SOURCE), store, ParsingRunner(), cache, usage)
    )

    await parsing_signaled.wait()
    mid = await store.get(job.id)
    assert mid is not None
    assert mid.status == JobStatus.parsing

    finish.set()
    await task
    final = await store.get(job.id)
    assert final is not None
    assert final.status == JobStatus.done


async def test_run_job_short_circuits_when_cancelled_before_start(store, runner, cache, usage):
    job = await _seed_job(store)
    await store.request_cancel(job.id)

    await run_job(job.id, JobRequest(source=SOURCE), store, runner, cache, usage)

    assert runner.calls == []
    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.done
    assert stored.result is not None
    assert stored.result.halt_reason == HaltReason.cancelled
    assert stored.result.test_cases == []
    assert stored.result.stats == {}


async def test_run_job_cancel_watcher_signals_and_tags(
    store, cache, usage, sample_result, monkeypatch
):
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
        run_job(job.id, JobRequest(source=SOURCE), store, CancellableRunner(), cache, usage)
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


async def test_run_job_caches_completed_result(store, cache, usage):
    job = await _seed_job(store)
    request = JobRequest(source=SOURCE)
    result = JobResult(
        test_cases=[
            TestCase(
                name="test1", inputs=[SymbolicInput(name="x", value="0", bytes_hex="00000000")]
            )
        ],
        messages="ok",
        warnings="",
        stats={"paths": 1},
        halt_reason=HaltReason.completed,
    )
    runner = FakeKleeRunner(canned_result=result)
    await run_job(job.id, request, store, runner, cache, usage)

    assert await cache.get(cache_key(request)) == result


async def test_run_job_does_not_cache_timed_out_result(store, cache, usage):
    job = await _seed_job(store)
    request = JobRequest(source=SOURCE)
    timed_out = JobResult(
        test_cases=[], messages="", warnings="", stats={}, halt_reason=HaltReason.max_time
    )
    runner = FakeKleeRunner(canned_result=timed_out)
    await run_job(job.id, request, store, runner, cache, usage)

    assert await cache.get(cache_key(request)) is None


async def test_run_job_does_not_cache_failed_job(store, cache, usage):
    job = await _seed_job(store)
    request = JobRequest(source=SOURCE)
    runner = FakeKleeRunner(raise_exc=KleeRunnerError("KLEE crashed"))
    await run_job(job.id, request, store, runner, cache, usage)

    assert await cache.get(cache_key(request)) is None


async def test_run_job_does_not_cache_compile_error(store, cache, usage):
    job = await _seed_job(store)
    request = JobRequest(source=SOURCE)
    compile_err = JobResult(
        test_cases=[], messages="", warnings="", stats={}, compile_error="input.c:1: error"
    )
    runner = FakeKleeRunner(canned_result=compile_err)
    await run_job(job.id, request, store, runner, cache, usage)

    assert await cache.get(cache_key(request)) is None


async def test_run_job_does_not_cache_cancelled_job(store, runner, cache, usage):
    job = await _seed_job(store)
    await store.request_cancel(job.id)
    request = JobRequest(source=SOURCE)
    await run_job(job.id, request, store, runner, cache, usage)

    assert await cache.get(cache_key(request)) is None


async def test_run_job_records_completed_outcome_and_totals(store, cache, usage):
    job = await _seed_job(store)
    result = JobResult(
        test_cases=[TestCase(name="t1", inputs=[]), TestCase(name="t2", inputs=[])],
        messages="",
        warnings="",
        stats={"Instructions": 250},
        halt_reason=HaltReason.completed,
    )
    runner = FakeKleeRunner(canned_result=result)
    await run_job(job.id, JobRequest(source=SOURCE), store, runner, cache, usage)

    snap = await usage.snapshot()
    assert snap.outcomes[JobOutcome.completed] == 1
    assert snap.test_cases_generated == 2
    assert snap.instructions_executed == 250


async def test_run_job_records_failed_outcome_with_zero_totals(store, cache, usage):
    job = await _seed_job(store)
    runner = FakeKleeRunner(raise_exc=KleeRunnerError("KLEE crashed"))
    await run_job(job.id, JobRequest(source=SOURCE), store, runner, cache, usage)

    snap = await usage.snapshot()
    assert snap.outcomes[JobOutcome.failed] == 1
    assert snap.test_cases_generated == 0
    assert snap.instructions_executed == 0


async def test_run_job_records_cancelled_outcome_when_cancelled_before_start(
    store, runner, cache, usage
):
    job = await _seed_job(store)
    await store.request_cancel(job.id)
    await run_job(job.id, JobRequest(source=SOURCE), store, runner, cache, usage)

    snap = await usage.snapshot()
    assert snap.outcomes[JobOutcome.cancelled] == 1
    assert runner.calls == []
