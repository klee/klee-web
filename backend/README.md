# backend/

FastAPI service. Receives job submissions, runs KLEE through the runner, returns results.

## Contents

- `pyproject.toml`: dependencies and tooling config
- `src/klee_web/main.py`: FastAPI app
- `src/klee_web/api/jobs.py`: `POST /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel`. POST returns `202` with a `job_id`, serving a cached result on a matching submission or else creating the job and handing it to the dispatcher. GET polls the store. Cancel flips the job terminal (ADR-0013)
- `src/klee_web/api/health.py`: `GET /health` (liveness, always `up`) and `GET /ready` (readiness, pings Redis, `200` or `503`). Infra callers poll readiness, browser clients poll liveness
- `src/klee_web/api/admin.py`: `GET /admin/telemetry` (fleet), `GET /admin/stats` (usage), and `PATCH /admin/workers/{name}/capacity` (live per-worker maximum). Gated at the nginx edge before any public deploy
- `src/klee_web/health.py`: `Readiness` protocol + `AlwaysReady` and `RedisReadiness`, the readiness check behind `/ready`
- `src/klee_web/models.py`: Pydantic schemas (`JobRequest`, `Job`, `JobCreated`, `JobResult`, `JobStatus`, `HaltReason`, `JobOutcome`, `KleeFlags`, `QueryFormat`, `TestCase`, `SymbolicInput`) plus the ops models (`Telemetry`, `WorkerTelemetry`, `QueueTelemetry`, `UsageStats`). `Job.outcome` is a computed field from `outcome_of_job` / `outcome_of_result`, the single terminal-outcome classifier the frontend also reads
- `src/klee_web/symbolic_input.py`: the `SymStdin` / `SymFiles` / `SymArgs` sub-models carried on `KleeFlags`, plus `render_posix_args`, which renders them into the `--sym-*` POSIX-runtime args passed to the runner after the bitcode
- `src/klee_web/flag_allowlist.py`: default-deny validation for the free-text `extra_flags` field, with per-flag boolean / bounded-integer / enum value policies (ADR-0019)
- `src/klee_web/jobs/dispatch.py`: `JobDispatcher` protocol + `InProcessDispatcher` (Stage 1, `asyncio.create_task`) and `CeleryDispatcher` (Stage 2, enqueue). `deps.py` picks one on `CELERY_BROKER_URL` (ADR-0016)
- `src/klee_web/jobs/run.py`: `run_job`, the shared job body both dispatchers reach: mark running, run KLEE, write the result, cache a completed run, record the outcome, and watch for a cancel
- `src/klee_web/jobs/store.py`: `JobStore` protocol + `InMemoryJobStore` and `RedisJobStore`. `set_partial_result` writes mid-flight progress, `set_result` flips status to `done`, `request_cancel` sets the cancel flag
- `src/klee_web/jobs/runner.py`: `KleeRunner` protocol + `DockerKleeRunner` and `FakeKleeRunner`. Stream-only transport: source in on the container's stdin, the whole output dir back as a tar on stdout, no bind mount (ADR-0021). Runtime is picked by `KLEE_RUNTIME` (`runc` default, `runsc`, `runsc-kvm`), and `--network none` is always set
- `src/klee_web/jobs/cache.py`: `ResultCache` protocol + `InMemoryResultCache` and `RedisResultCache`, keyed on the submission (ADR-0017)
- `src/klee_web/jobs/telemetry.py`: `FleetTelemetry` for worker pool sizes, active/reserved jobs, and queue depth, plus `FleetControl` for changing a worker's autoscaler maximum through Celery remote control
- `src/klee_web/jobs/usage.py`: `UsageStatsStore` protocol + `InMemoryUsageStatsStore` and `RedisUsageStatsStore` (`INCR` counters for outcomes, cache hits, and aggregate KLEE totals), read at `/admin/stats`
- `src/klee_web/celery_app.py`: the Celery app and the `run_klee_job` task the worker runs (Stage 2)
- `src/klee_web/parsing/klee_output.py`: parse KLEE output dir into a `JobResult`. Detects halt reason from `HaltTimer invoked` in `messages.txt` (`max_time`) or `KLEE: done:` in `info` (`completed`)
- `src/klee_web/parsing/ktest.py`: vendored KLEE ktest reader (NCSA, trimmed to `KTest.fromfile`)
- `src/klee_web/deps.py`: dependency providers (`get_job_store`, `get_runner`, `get_cache`, `get_dispatcher`, `get_readiness`, `get_telemetry`, `get_usage_stats`), each selecting the Stage 1 or Stage 2 implementation from config
- `tests/unit/`: handler, dispatch, run-job, store, cache, model, config, and parser tests (parser golden fixtures: `happy_path`, `compile_error`, `runtime_error`, `max_time`)
- `tests/integration/`: real-Docker runner, Redis store and cache, and the Celery worker end to end

## Why `JobStore` and `KleeRunner` are protocols

Stage 1 ships in-memory and direct-Docker implementations. Stage 2 swaps in `RedisJobStore` and a Celery-driven runner. The endpoints depend on the protocols via `Depends`, never on the concrete classes. One file (`deps.py`) changes at the stage boundary; everything else is untouched. See `../docs/adr/0001-stage-based-additive-architecture.md`.

## Stage 2: running with Celery

By default the backend runs each job in-process, with no Redis and no worker. That is the zero-config dev path (`make up`). To run the Stage 2 split locally, with a real Celery worker pulling jobs off Redis, from the repo root:

```
make up-celery
```

It brings up Redis through `docker compose`, then runs the API, a Celery worker (`-Q klee-jobs --autoscale=4,1`), and the frontend as host processes, with `REDIS_URL` (the store, db 0) and `CELERY_BROKER_URL` (the broker, db 1) set. With both set the API enqueues jobs instead of running them inline, and the worker runs KLEE and writes results to the shared `RedisJobStore`. Override the worker maximum with `make up-celery WORKER_CONCURRENCY_MAX=8`. Ctrl+C brings Redis back down.

### Manual worker smoke

`tests/integration/test_celery_worker.py` covers the enqueue-to-store path with an embedded worker and a fake runner. To smoke the real path end to end, with `make up-celery` running:

1. Submit a job from the frontend (the pre-loaded program is enough).
2. Watch the worker log pick up `run_klee_job` and spawn a container.
3. Poll `GET /jobs/{id}` until the status is `done` and confirm the test cases.

This stays manual on purpose. It overlaps the runner integration test and the Playwright e2e, and it needs real Docker, so it is not in the automated suite.

### Manual worker-death smoke

A dead worker's job is lost, not redelivered (ADR-0018, at-most-once). Celery acks a task on receipt (`task_acks_late` stays off), so a worker that dies mid-run has already acked and the broker never re-sends the job. That is safe only because cancel resolves the stuck job API-side (ADR-0013, the eager flip), alive worker or not. A genuine worker death is brittle to reproduce in CI, so this stays manual. With `make up-celery` running:

1. Submit a job with a longer `max_time` (say 60) so it is still running when you kill the worker.
2. Watch the worker log pick up `run_klee_job` and spawn `klee-job-{id}`. Confirm `GET /jobs/{id}` is `running`.
3. `kill -9` the worker process mid-run. The job stays `running` (the worker already acked, and nothing redelivers it), and its container keeps running orphaned under `klee-job-{id}` (it runs under dockerd, not as the worker's child).
4. `POST /jobs/{id}/cancel` (or click Cancel in the UI). The API writes the terminal state straight to the store, so the job resolves at once with no worker alive and the UI unblocks.
5. The orphaned container keeps running until its own entrypoint bound stops it (up to `max_time`), then `--rm` removes it. That bounded waste is the accepted cost of not reclaiming (ADR-0018). Resubmit if you still want the result.

### Worker pool

`make up-celery` runs one worker. To run several against the one queue:

```
make up-pool
```

Same stack as `make up-celery`, with the single worker replaced by `WORKERS` host processes (default 2), each autoscaling from one process to `WORKER_CONCURRENCY_MAX` (default 4) and using a distinct Celery node name so they are tellable apart in the logs. Override either axis with `make up-pool WORKERS=4 WORKER_CONCURRENCY_MAX=2`. The broker spreads jobs across the pool: submit several at once and each worker claims a distinct task.

The pool is about throughput, not failover. It does not make an in-flight job survive its worker's death: a dying worker loses only the one job it had acked, while the jobs still queued in the broker are untouched and the live peers keep draining them. That one lost job is recovered by cancel (above), not by a peer. Cancel routes through the shared store, so it reaches the right job whichever worker held it.

Each worker runs as a host process, not a container. Containerising it would mean mounting the host docker socket so the worker could spawn sibling KLEE containers, i.e. handing a container root on the host. That is a deployment and security decision Stage 3 owns, not Stage 2.
