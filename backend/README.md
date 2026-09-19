# backend/

FastAPI service. Receives Job submissions, enqueues them through Celery, and returns state and results stored in Redis.

## Contents

- `pyproject.toml`: dependencies and tooling config
- `src/klee_web/main.py`: FastAPI app
- `src/klee_web/api/jobs.py`: `POST /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel`. POST returns `202` with a `job_id`, serving a cached result on a matching submission or else creating the job and handing it to the dispatcher. GET polls the store. Cancel flips the job terminal (ADR-0013)
- `src/klee_web/api/health.py`: `GET /health` (liveness, always `up`) and `GET /ready` (readiness, pings Redis, `200` or `503`). Infra callers poll readiness, browser clients poll liveness
- `src/klee_web/api/admin.py`: `GET /admin/telemetry` (fleet), `GET /admin/stats` (usage), and `PATCH /admin/workers/{name}/capacity` (live per-worker maximum). Gated at the nginx edge by Basic Auth
- `src/klee_web/health.py`: `Readiness` protocol + `RedisReadiness`, the Redis readiness check behind `/ready`
- `src/klee_web/models.py`: Pydantic schemas (`JobRequest`, `Job`, `JobCreated`, `JobResult`, `JobStatus`, `HaltReason`, `JobOutcome`, `KleeFlags`, `QueryFormat`, `TestCase`, `SymbolicInput`) plus the ops models (`Telemetry`, `WorkerTelemetry`, `QueueTelemetry`, `UsageStats`). `JobResult.klee_version` records the producing KLEE version. `Job.outcome` is a computed field from `outcome_of_job` / `outcome_of_result`, the single terminal-outcome classifier the frontend also reads
- `src/klee_web/symbolic_input.py`: the `SymStdin` / `SymFiles` / `SymArgs` sub-models carried on `KleeFlags`, plus `render_posix_args`, which renders them into the `--sym-*` POSIX-runtime args passed to the runner after the bitcode
- `src/klee_web/flag_allowlist.py`: default-deny validation for the free-text `extra_flags` field, with per-flag boolean / bounded-integer / enum value policies (ADR-0019)
- `src/klee_web/jobs/dispatch.py`: `JobDispatcher` protocol + `CeleryDispatcher`, which enqueues the complete `JobRequest` (ADR-0016, amended by ADR-0024)
- `src/klee_web/jobs/run.py`: `run_job`, the Worker job body: mark running, run KLEE, write the result, cache a completed run, record the outcome, and watch for a cancel
- `src/klee_web/jobs/store.py`: `JobStore` protocol + `RedisJobStore`. `set_partial_result` writes mid-flight progress, `set_result` flips status to `done`, `request_cancel` sets the cancel flag
- `src/klee_web/jobs/runner.py`: `KleeRunner` protocol + `DockerKleeRunner`. Stream-only transport: source in on the container's stdin, the whole output dir back as a tar on stdout, no bind mount (ADR-0021). Backend Settings require `RUNNER_IMAGE` as a local image ID or immutable registry digest. Supported deployments pick `runsc` or `runsc-kvm`. `runc` remains an integration-test control. Every run disables the network, prevents setuid privilege escalation, makes the root read-only, and mounts bounded temporary storage at `/work`
- `src/klee_web/jobs/cache.py`: `ResultCache` protocol + `RedisResultCache`, keyed on the canonical submission, exact Runner image identity, and `JobResult` schema (ADR-0017, amended by ADR-0024)
- `src/klee_web/jobs/telemetry.py`: `FleetTelemetry` for worker pool sizes, active/reserved jobs, and queue depth, plus `FleetControl` for changing a worker's autoscaler maximum through Celery remote control
- `src/klee_web/jobs/usage.py`: `UsageStatsStore` protocol + `RedisUsageStatsStore` (`INCR` counters for outcomes, cache hits, and aggregate KLEE totals), read at `/admin/stats`
- `src/klee_web/celery_app.py`: the Celery app, Worker dependency construction, and the `run_klee_job` task
- `src/klee_web/parsing/klee_output.py`: parse KLEE output dir into a `JobResult`. Detects halt reason from `HaltTimer invoked` in `messages.txt` (`max_time`) or `KLEE: done:` in `info` (`completed`)
- `src/klee_web/parsing/ktest.py`: vendored KLEE ktest reader (NCSA, trimmed to `KTest.fromfile`)
- `src/klee_web/deps.py`: API dependency providers (`get_job_store`, `get_cache`, `get_dispatcher`, `get_readiness`, `get_telemetry`, `get_fleet_control`, `get_usage_stats`)
- `tests/unit/`: handler, dispatch, run-job, store, cache, model, config, and parser tests (parser golden fixtures: `happy_path`, `compile_error`, `runtime_error`, `max_time`)
- `tests/integration/`: real-Docker Runner, Redis store, cache, usage, readiness and telemetry, plus the Celery Worker end to end

## Why the protocols remain

The Protocols kept the HTTP API and core Job logic unchanged when Stage 2 moved execution from FastAPI onto a Celery Worker. They still prevent endpoints and `run_job` from depending on concrete infrastructure. Production has one implementation per seam, while endpoint and core-logic tests inject deterministic fakes from `tests/fakes.py`. See ADR-0024.

## Running the stack

From the repository root:

```
make deploy
```

Compose starts Redis, the API, a Celery Worker, and nginx with the built frontend. `REDIS_URL` (store, cache, and stats on db 0) and `CELERY_BROKER_URL` (broker on db 1) are required settings supplied by Compose. `RUNNER_IMAGE` supplies the same required local image ID or registry digest to the API cache key and Worker launch. `make deploy` resolves the local ID. Registry deployments resolve a publication tag to a digest before startup. The backend image carries the KLEE version selected by `.klee-version`. The API enqueues every cache miss. The Worker runs KLEE and writes through the shared Redis services. Use `make logs` to follow the detached stack and `make down` to stop it.

### Manual worker smoke

`tests/integration/test_celery_worker.py` covers the enqueue-to-store path with an embedded Worker and an injected test fake. Playwright covers the full path with a real Runner under gVisor. To smoke it manually, with `make deploy` running:

1. Submit a job from the frontend (the pre-loaded program is enough).
2. Watch the worker log pick up `run_klee_job` and spawn a container.
3. Poll `GET /jobs/{id}` until the status is `done` and confirm the test cases.

This remains a manual operator smoke. The Runner integration tests and Playwright e2e automate the same execution path at their respective boundaries.

### Manual worker-death smoke

A dead Worker's Job is lost, not redelivered (ADR-0018, at-most-once). Celery acks a task on receipt (`task_acks_late` stays off), so a Worker that dies mid-run has already acked and the broker never re-sends the Job. Cancel resolves the stuck Job API-side (ADR-0013, the eager flip), alive Worker or not. With `make deploy` running:

1. Submit a job with a longer `max_time` (say 60) so it is still running when you kill the worker.
2. Watch the worker log pick up `run_klee_job` and spawn `klee-job-{id}`. Confirm `GET /jobs/{id}` is `running`.
3. Find the Worker with `docker compose ps worker`, then kill that container. The restart policy brings the Worker container back, but the acknowledged Job stays `running` and its sibling Runner container continues until its own bound stops it.
4. `POST /jobs/{id}/cancel` (or click Cancel in the UI). The API writes the terminal state straight to the store, so the job resolves at once with no worker alive and the UI unblocks.
5. The orphaned container keeps running until its own entrypoint bound stops it (up to `max_time`), then `--rm` removes it. That bounded waste is the accepted cost of not reclaiming (ADR-0018). Resubmit if you still want the result.

### Worker pool

`make deploy` runs one Worker by default. To run several against the shared queue:

```
make deploy WORKER_REPLICAS=2 WORKER_CONCURRENCY_MAX=4
```

`WORKER_REPLICAS` controls Worker containers. Each autoscaler starts at one process and can grow to `WORKER_CONCURRENCY_MAX`. The two values multiply into the deployment's maximum concurrent Runner containers. Celery derives distinct Worker names from the container hostnames, and the broker distributes Jobs across the fleet.

The pool is about throughput, not failover. It does not make an in-flight job survive its worker's death: a dying worker loses its active acknowledged jobs, while reserved jobs remain eligible for broker restoration and jobs still queued in the broker are untouched. Each lost job is recovered by cancel (above), not by a peer. Cancel routes through the shared store, so it reaches the right job whichever worker held it.

Each Worker is a container with the host Docker socket mounted so it can launch sibling Runner containers. This gives the Worker control of the host Docker daemon. The public API cannot reach that socket, and submitted code remains inside the separate gVisor Runner container.
