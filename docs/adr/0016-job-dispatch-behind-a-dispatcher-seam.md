# 0016. Job dispatch behind a JobDispatcher seam

**Status:** Accepted, 2026-06-24

## Context

Stage 1 runs a job in the API process: `POST /jobs` creates the job and schedules an asyncio background task that runs KLEE and writes the result. Stage 2 introduces the split, a separate worker process runs KLEE while the API keeps serving polls. ADR-0001 promised this hoist would not touch the endpoints or the frontend.

The in-process path is worth keeping, not just replacing. It is what makes a fresh clone run with no broker and no worker, which is zero-config dev and CI, and dropping it would replace Stage 1 behaviour rather than add to it. So both ways of running a job have to coexist, chosen without the endpoint knowing which.

## Decision

The orchestration that lives in `_run_job_in_background` (status to running, partial results, the final result, the failed path) moves into a shared `run_job(job_id, request, store, runner)` in the `jobs` package, out of the API layer so the worker never imports FastAPI.

A `JobDispatcher` protocol sits between the endpoint and execution, with one method, `dispatch(job_id, request)`. `InProcessDispatcher` schedules `run_job` as an asyncio background task on the API's event loop, the Stage 1 behaviour. `CeleryDispatcher` enqueues a Celery task onto a Redis-backed queue, and the worker runs `asyncio.run(run_job(...))`, building its own store and runner from `Settings` because those do not cross the process boundary. `get_dispatcher` selects between them on `CELERY_BROKER_URL`, the same shape as `get_job_store` selecting on `REDIS_URL`. `POST /jobs` calls `dispatch` and knows nothing else.

The worker is the backend package run with a Celery entrypoint, not a separate codebase. Celery is the transport only. Results live in `RedisJobStore`, so the Celery result backend stays off. Celery mode therefore requires the Redis store, and a settings validator fails loud if `CELERY_BROKER_URL` is set without `REDIS_URL`, since an in-memory store would split-brain across the two processes.

## Consequences

- The execution split is a config swap. Endpoints and frontend are untouched, the ADR-0001 promise made good a second time after the storage swap.
- Two execution paths exist, but they are two thin adapters over one `run_job`, not duplicated logic. The in-process path stays the zero-config default for dev and CI, Celery is opt-in.
- `run_job` leaving the API layer is what lets the worker avoid importing FastAPI. The cost is one more module in `jobs`.
- Celery without the Redis store is a silent split-brain, so the dependency is enforced at startup rather than discovered in production.
- A worker that dies mid-job loses it until unit 4 adds `acks_late` and redelivery. This is parity with the in-process path today, where an API restart loses the background job.

## References

- ADR-0001: stage-based additive architecture, the hoist this realises.
- ADR-0002: JobStore protocol surface, the same Protocol-plus-provider shape.
- ADR-0013: cancel as a user-triggered halt, whose Stage 2 amendment depends on this seam.
- ADR-0014: RedisJobStore, why the Celery result backend stays off.
