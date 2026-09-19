from uuid import UUID, uuid4

from klee_web.jobs.cache import cache_key
from klee_web.models import (
    HaltReason,
    Job,
    JobRequest,
    JobResult,
    JobStatus,
    SymbolicInput,
    TestCase,
)


async def test_post_jobs_returns_202_with_job_id(client):
    response = await client.post("/jobs", json={"source": "int main() { return 0; }"})
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    UUID(body["job_id"])  # raises if not a valid UUID


async def test_post_jobs_creates_pending_job_and_dispatches(client, store, dispatcher):
    payload = {
        "source": "int main() { return 0; }",
        "flags": {"max_time": 120, "max_memory": 256},
    }
    response = await client.post("/jobs", json=payload)
    job_id = UUID(response.json()["job_id"])

    job = await store.get(job_id)
    assert job is not None
    assert job.status == JobStatus.pending
    assert job.result is None
    assert dispatcher.calls == [(job_id, JobRequest.model_validate(payload))]


async def test_post_jobs_rejects_empty_source(client):
    response = await client.post("/jobs", json={"source": ""})
    assert response.status_code == 422


async def test_post_jobs_rejects_oversized_source(client):
    response = await client.post("/jobs", json={"source": "a" * 64_001})
    assert response.status_code == 422


async def test_get_jobs_returns_completed_job(client, store, sample_result):
    job = Job(status=JobStatus.done, result=sample_result)
    await store.create(job)

    get_response = await client.get(f"/jobs/{job.id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["status"] == "done"
    assert body["result"] is not None


async def test_get_jobs_returns_404_for_unknown_id(client):
    response = await client.get(f"/jobs/{uuid4()}")
    assert response.status_code == 404


async def test_cancel_unknown_job_returns_404(client):
    response = await client.post(f"/jobs/{uuid4()}/cancel")
    assert response.status_code == 404


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


async def test_cancel_finished_job_returns_409(client, store, sample_result):
    job = Job(status=JobStatus.done, result=sample_result)
    await store.create(job)

    cancel = await client.post(f"/jobs/{job.id}/cancel")
    assert cancel.status_code == 409
    stored = await store.get(job.id)
    assert stored is not None
    assert stored.cancel_requested is False


async def test_post_jobs_serves_cache_hit_without_dispatching(
    client, cache, dispatcher, usage, klee_version, runner_image
):
    payload = {"source": "int main(){}"}
    cached = JobResult(
        test_cases=[
            TestCase(
                name="cached", inputs=[SymbolicInput(name="x", value="0", bytes_hex="00000000")]
            )
        ],
        messages="from cache",
        warnings="",
        stats={"paths": 1},
        halt_reason=HaltReason.completed,
        klee_version=klee_version,
    )
    await cache.set(
        cache_key(JobRequest(source=payload["source"]), runner_image=runner_image), cached
    )

    response = await client.post("/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    assert dispatcher.calls == []

    get = await client.get(f"/jobs/{job_id}")
    body = get.json()
    assert body["status"] == "done"
    assert body["result"]["messages"] == "from cache"


async def test_post_jobs_second_identical_submission_hits_cache(
    client, cache, dispatcher, usage, klee_version, runner_image
):
    cached = JobResult(
        test_cases=[
            TestCase(name="t", inputs=[SymbolicInput(name="x", value="0", bytes_hex="00000000")])
        ],
        messages="",
        warnings="",
        stats={"paths": 1},
        halt_reason=HaltReason.completed,
        klee_version=klee_version,
    )

    payload = {"source": "int main(){}"}
    await client.post("/jobs", json=payload)
    assert len(dispatcher.calls) == 1

    # Simulate the worker completing the first job and caching its result.
    await cache.set(cache_key(JobRequest(source=payload["source"]), runner_image), cached)

    response = await client.post("/jobs", json=payload)
    assert response.status_code == 202
    assert len(dispatcher.calls) == 1  # second identical submission served from cache, no re-run

    job_id = response.json()["job_id"]
    get = await client.get(f"/jobs/{job_id}")
    body = get.json()
    assert body["result"]["klee_version"] == klee_version
    assert (await usage.snapshot()).cache_hits == 1  # check klee version and cache hits


async def test_post_jobs_cache_hit_records_a_cache_hit(
    client, cache, usage, klee_version, runner_image
):
    payload = {"source": "int main(){}"}
    cached = JobResult(
        test_cases=[],
        messages="from cache",
        warnings="",
        stats={},
        halt_reason=HaltReason.completed,
        klee_version=klee_version,
    )
    await cache.set(
        cache_key(JobRequest(source=payload["source"]), runner_image=runner_image), cached
    )

    await client.post("/jobs", json=payload)

    assert (await usage.snapshot()).cache_hits == 1
