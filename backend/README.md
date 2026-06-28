# backend/

FastAPI service. Receives job submissions, runs KLEE through the runner, returns results.

## Stage 1 contents

- `pyproject.toml`: dependencies and tooling config
- `src/klee_web/main.py`: FastAPI app
- `src/klee_web/api/jobs.py`: `POST /jobs`, `GET /jobs/{id}`. POST returns immediately and schedules the runner on `asyncio.create_task`; GET polls the store
- `src/klee_web/models.py`: Pydantic schemas (`JobRequest`, `Job`, `JobResult`, `JobStatus`, `KleeFlags`, `TestCase`, `HaltReason`)
- `src/klee_web/jobs/store.py`: `JobStore` protocol + `InMemoryJobStore`. `set_partial_result` for mid-flight progress writes; `set_result` flips status to `done`
- `src/klee_web/jobs/runner.py`: `KleeRunner` protocol + `DockerKleeRunner`. Spawns a watcher coroutine that polls the output dir every second and emits partials via an `on_progress` callback
- `src/klee_web/parsing/klee_output.py`: parse KLEE output dir into a `JobResult`. Detects halt reason from `HaltTimer invoked` in `messages.txt` (`max_time`) or `KLEE: done:` in `info` (`completed`)
- `src/klee_web/parsing/ktest.py`: vendored KLEE ktest reader (NCSA, trimmed to `KTest.fromfile`)
- `src/klee_web/deps.py`: dependency providers (`get_job_store`, `get_runner`)
- `tests/unit/`: handler tests, parser tests with golden fixtures (`happy_path`, `compile_error`, `runtime_error`, `max_time`)
- `tests/integration/`: end-to-end with real Docker

## Why `JobStore` and `KleeRunner` are protocols

Stage 1 ships in-memory and direct-Docker implementations. Stage 2 swaps in `RedisJobStore` and a Celery-driven runner. The endpoints depend on the protocols via `Depends`, never on the concrete classes. One file (`deps.py`) changes at the stage boundary; everything else is untouched. See `../docs/adr/0001-stage-based-additive-architecture.md`.

## Stage 2: running with Celery

By default the backend runs each job in-process, with no Redis and no worker. That is the zero-config dev path (`make up`). To run the Stage 2 split locally, with a real Celery worker pulling jobs off Redis, from the repo root:

```
make up-celery
```

It brings up Redis through `docker compose`, then runs the API, a Celery worker (`-Q klee-jobs --concurrency=2`), and the frontend as host processes, with `REDIS_URL` (the store, db 0) and `CELERY_BROKER_URL` (the broker, db 1) set. With both set the API enqueues jobs instead of running them inline, and the worker runs KLEE and writes results to the shared `RedisJobStore`. Ctrl+C brings Redis back down.

### Manual worker smoke

`tests/integration/test_celery_worker.py` covers the enqueue-to-store path with an embedded worker and a fake runner. To smoke the real path end to end, with `make up-celery` running:

1. Submit a job from the frontend (the pre-loaded program is enough).
2. Watch the worker log pick up `run_klee_job` and spawn a container.
3. Poll `GET /jobs/{id}` until the status is `done` and confirm the test cases.

This stays manual on purpose. It overlaps the runner integration test and the Playwright e2e, and it needs real Docker, so it is not in the automated suite.

### Manual worker-death smoke

`acks_late` and the visibility timeout redeliver a job whose worker dies mid-run (ADR-0018). The deterministic pieces (terminal short-circuit, attempts cap, container reclaim) are unit-tested; the actual kill stays manual, because making a genuine worker death reproducible in CI is brittle. With `make up-celery` running:

1. Submit a job with a longer `max_time` (say 60) so it is still running when you kill the worker.
2. Watch the worker log pick up `run_klee_job` and spawn `klee-job-{id}`. Confirm `GET /jobs/{id}` is `running`.
3. `kill -9` the worker process mid-run. The job stays `running` (the worker never acked), and its container keeps running orphaned under `klee-job-{id}` (it runs under dockerd, not as the worker's child).
4. Start a fresh worker (the same `celery ... worker` line `make up-celery` uses).
5. After the visibility timeout the broker redelivers the task. The redelivered run force-removes the orphaned container, re-runs KLEE, and the job lands `done`.

The wait in step 5 is the Redis visibility timeout (`MAX_TIME_CEILING * 2` = 600s). To smoke it faster, lower `broker_transport_options["visibility_timeout"]` in `celery_app.py` temporarily.
