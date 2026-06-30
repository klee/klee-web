import asyncio
from uuid import UUID, uuid4

from klee_web.deps import get_runner
from klee_web.jobs.cache import cache_key
from klee_web.jobs.runner import FakeKleeRunner, KleeRunnerError
from klee_web.models import HaltReason, Job, JobRequest, JobResult, JobStatus, TestCase


async def test_post_jobs_returns_202_with_job_id(client):
    response = await client.post("/jobs", json={"source": "int main() { return 0; }"})
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    UUID(body["job_id"])  # raises if not a valid UUID


async def test_post_jobs_calls_runner_with_source_and_flags(client, runner, wait_for_jobs):
    payload = {
        "source": "int main() { return 0; }",
        "flags": {"max_time": 120, "max_memory": 256},
    }
    await client.post("/jobs", json=payload)
    await wait_for_jobs()
    assert len(runner.calls) == 1
    called_source, called_flags = runner.calls[0]
    assert called_source == payload["source"]
    assert called_flags.max_time == 120
    assert called_flags.max_memory == 256


async def test_post_jobs_happy_path_stores_result_and_advances_to_done(
    client,
    store,
    sample_result,
    wait_for_jobs,
):
    response = await client.post("/jobs", json={"source": "int main(){}"})
    job_id = UUID(response.json()["job_id"])
    await wait_for_jobs()
    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.done
    assert job.result == sample_result


async def test_post_jobs_runner_failure_marks_job_failed(client, app, store, wait_for_jobs):
    failing_runner = FakeKleeRunner(raise_exc=KleeRunnerError("KLEE crashed"))
    app.dependency_overrides[get_runner] = lambda: failing_runner

    response = await client.post("/jobs", json={"source": "int main(){}"})
    assert response.status_code == 202
    job_id = UUID(response.json()["job_id"])
    await wait_for_jobs()
    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.failed


async def test_post_jobs_rejects_empty_source(client):
    response = await client.post("/jobs", json={"source": ""})
    assert response.status_code == 422


async def test_post_jobs_rejects_oversized_source(client):
    response = await client.post("/jobs", json={"source": "a" * 64_001})
    assert response.status_code == 422


async def test_get_jobs_returns_completed_job(client, wait_for_jobs):
    post_response = await client.post("/jobs", json={"source": "int main(){}"})
    job_id = post_response.json()["job_id"]
    await wait_for_jobs()

    get_response = await client.get(f"/jobs/{job_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "done"
    assert body["result"] is not None


async def test_get_jobs_returns_404_for_unknown_id(client):
    response = await client.get(f"/jobs/{uuid4()}")
    assert response.status_code == 404


async def test_post_runs_in_background_and_streams_partial_results(
    client,
    app,
    store,
    wait_for_jobs,
    sample_result,
):
    """POST returns immediately; partial lands while running; final lands at completion."""
    partial_emitted = asyncio.Event()
    finish_when = asyncio.Event()
    partial = JobResult(
        test_cases=[TestCase(name="test_partial", inputs={"x": "1"})],
        messages="",
        warnings="",
        stats={},
    )

    class BlockingStreamingRunner:
        async def execute(self, source, flags, job_id, on_progress=None, on_parsing=None):
            if on_progress is not None:
                await on_progress(partial)
            partial_emitted.set()
            await finish_when.wait()
            return sample_result

    app.dependency_overrides[get_runner] = lambda: BlockingStreamingRunner()

    response = await client.post("/jobs", json={"source": "int main(){}"})
    assert response.status_code == 202
    job_id = UUID(response.json()["job_id"])

    # Mid-execution: partial has landed, status is still running.
    await partial_emitted.wait()
    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.running
    assert job.result == partial

    # Let the runner finish. Final state: done with the final result.
    finish_when.set()
    await wait_for_jobs()
    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.done
    assert job.result == sample_result


async def test_post_flips_to_parsing_between_klee_exit_and_result(
    client,
    app,
    store,
    wait_for_jobs,
    sample_result,
):
    """When KLEE exits, status becomes 'parsing' until the final result lands, so
    the UI can show it is loading results rather than appearing to hang."""
    parsing_signaled = asyncio.Event()
    finish_when = asyncio.Event()

    class ParsingRunner:
        async def execute(self, source, flags, job_id, on_progress=None, on_parsing=None):
            if on_parsing is not None:
                await on_parsing()
            parsing_signaled.set()
            await finish_when.wait()
            return sample_result

    app.dependency_overrides[get_runner] = lambda: ParsingRunner()

    response = await client.post("/jobs", json={"source": "int main(){}"})
    job_id = UUID(response.json()["job_id"])

    await parsing_signaled.wait()
    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.parsing

    finish_when.set()
    await wait_for_jobs()
    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.done


class CancellableRunner:
    """Blocks execute on a finish event so a cancel can land mid-run. cancel records
    its calls and returns a settable bool, decoupling 'cancel landed' from 'execute
    returned' the way a real container does (signal now, exit later after flush)."""

    def __init__(self, result: JobResult, cancel_returns: bool = True) -> None:
        self._result = result
        self._cancel_returns = cancel_returns
        self.running = asyncio.Event()
        self.finish = asyncio.Event()
        self.cancel_calls: list[UUID] = []

    async def execute(self, source, flags, job_id, on_progress=None, on_parsing=None):
        self.running.set()
        await self.finish.wait()
        return self._result

    async def cancel(self, job_id):
        self.cancel_calls.append(job_id)
        return self._cancel_returns


async def test_cancel_unknown_job_returns_404(client):
    response = await client.post(f"/jobs/{uuid4()}/cancel")
    assert response.status_code == 404


async def test_cancel_running_job_returns_202_and_tags_result_cancelled(
    client,
    app,
    store,
    sample_result,
    wait_for_jobs,
):
    runner = CancellableRunner(sample_result, cancel_returns=True)
    app.dependency_overrides[get_runner] = lambda: runner

    post = await client.post("/jobs", json={"source": "int main(){}"})
    job_id = UUID(post.json()["job_id"])
    await runner.running.wait()

    cancel = await client.post(f"/jobs/{job_id}/cancel")
    assert cancel.status_code == 202
    job = await store.get(job_id)
    assert job is not None
    assert job.cancel_requested is True

    runner.finish.set()
    await wait_for_jobs()
    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.done
    assert job.result is not None
    assert job.result.halt_reason == HaltReason.cancelled


async def test_cancel_eagerly_flips_a_running_job_to_cancelled(client, store):
    """Cancel resolves the job to terminal at once, without a worker writing the result,
    so a dead or frozen job's UI unblocks and the user can resubmit."""
    job = Job(status=JobStatus.running)
    await store.create(job)

    response = await client.post(f"/jobs/{job.id}/cancel")

    assert response.status_code == 202
    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.done
    assert stored.result is not None
    assert stored.result.halt_reason == HaltReason.cancelled


async def test_cancel_preserves_partials_in_the_eager_flip(client, store, sample_result):
    job = Job(status=JobStatus.running, result=sample_result)
    await store.create(job)

    await client.post(f"/jobs/{job.id}/cancel")

    stored = await store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.done
    assert stored.result is not None
    assert stored.result.test_cases == sample_result.test_cases
    assert stored.result.halt_reason == HaltReason.cancelled


async def test_cancel_finished_job_returns_409(client, store, wait_for_jobs):
    post = await client.post("/jobs", json={"source": "int main(){}"})
    job_id = UUID(post.json()["job_id"])
    await wait_for_jobs()

    cancel = await client.post(f"/jobs/{job_id}/cancel")
    assert cancel.status_code == 409
    job = await store.get(job_id)
    assert job is not None
    assert job.cancel_requested is False


async def test_post_jobs_serves_cache_hit_without_dispatching(client, runner, cache, wait_for_jobs):
    payload = {"source": "int main(){}"}
    cached = JobResult(
        test_cases=[TestCase(name="cached", inputs={"x": "0"})],
        messages="from cache",
        warnings="",
        stats={"paths": 1},
        halt_reason=HaltReason.completed,
    )
    await cache.set(cache_key(JobRequest(source=payload["source"])), cached)

    response = await client.post("/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    await wait_for_jobs()
    assert runner.calls == []  # cache hit: KLEE never ran

    get = await client.get(f"/jobs/{job_id}")
    body = get.json()
    assert body["status"] == "done"
    assert body["result"]["messages"] == "from cache"


async def test_post_jobs_second_identical_submission_hits_cache(client, app, wait_for_jobs):
    completed = JobResult(
        test_cases=[TestCase(name="t", inputs={"x": "0"})],
        messages="",
        warnings="",
        stats={"paths": 1},
        halt_reason=HaltReason.completed,
    )
    runner = FakeKleeRunner(canned_result=completed)
    app.dependency_overrides[get_runner] = lambda: runner

    payload = {"source": "int main(){}"}
    await client.post("/jobs", json=payload)
    await wait_for_jobs()
    assert len(runner.calls) == 1

    await client.post("/jobs", json=payload)
    await wait_for_jobs()
    assert len(runner.calls) == 1  # second identical submission served from cache, no re-run
