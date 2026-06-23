# 0001. Stage-based additive architecture

**Status:** Accepted, 2026-05-18

## Context

KLEE Web is delivered in three stages with a hard schedule:

1. **Stage 1 (by end of May 2026):** synchronous monolith. React + FastAPI + Docker runner, runnable locally with `make up`. No queue, no cache, no sandboxing beyond stock Docker.
2. **Stage 2 (summer):** Celery workers, Redis as broker and result cache, worker pool. The execution path becomes asynchronous; the API path stays the same.
3. **Stage 3 (late summer):** nginx edge proxy, gVisor sandbox runtime, observability, admin UI.

The Stage 1 deadline is two weeks. The temptation is to ship the simplest possible Stage 1 (run KLEE inline inside `POST /jobs`, return the result directly, no abstraction) and rewrite for Stage 2 when the work-decoupling becomes necessary. The previous KLEE Web implementation took a related shortcut and accumulated structural debt that survived for a decade.

We need Stage 1 to be both: small enough to ship in two weeks, and shaped such that Stages 2 and 3 add functionality rather than replace it.

## Decision

Adopt the **strictly additive principle**: each stage adds capabilities, never rewrites existing code. Stage 1 is built with the eventual shape of Stages 2 and 3 already in mind. Stage transitions are configuration and wiring changes, not refactors.

Three concrete commitments fall out of this:

### 1. API contract is async-shaped from day one

`POST /jobs` accepts source + flags, returns a `job_id` immediately. `GET /jobs/{id}` returns the job's current status (`pending`, `running`, `done`, `failed`) and, if done, the result. The frontend polls.

In Stage 1, the work happens synchronously inside `POST /jobs` before the response is sent (storing the result against the `job_id`). In Stage 2, the same function is wrapped in a Celery task and the response returns the `job_id` before work starts. **The HTTP contract and the frontend code are identical.**

### 2. `JobStore` and `KleeRunner` are Python `Protocol`s, not concrete classes

The FastAPI endpoints depend on protocols, injected via `Depends`:

- `JobStore` defines `create`, `get`, `update_status`, `set_result`. Stage 1 implements with an in-memory dict guarded by `asyncio.Lock` (`InMemoryJobStore`). Stage 2 implements with Redis (`RedisJobStore`). The endpoints never know which.
- `KleeRunner` defines `execute(source, flags) -> JobResult`. Stage 1 implements by `subprocess.run`ing `docker run` directly (`DockerKleeRunner`). Stage 2 wraps it in a Celery task. The endpoints call `runner.execute(...)` either way.

The swap happens in one file (`backend/src/klee_web/deps.py`). Endpoints, frontend, and Pydantic models are untouched at the stage boundary.

### 3. `runner/` is a top-level sibling of `backend/`, not a subfolder

```
klee-web/
├── backend/    FastAPI service
├── runner/     Docker image and entrypoint
└── frontend/
```

In Stage 1 the backend and runner share a host (the backend shells out to `docker run`). In Stage 2 the runner is deployed onto separate worker VMs, with Celery as the transport. The directory layout already reflects the deployment topology, so no restructuring happens at the stage boundary. It also enforces a discipline: backend code cannot reach into runner internals because it has no Python import path to them.

### Stage 3 follows the same pattern at a different level

gVisor is selected via Docker runtime flag (`--runtime=runsc`). Zero application code change. nginx sits in front of FastAPI without FastAPI knowing. Observability is sidecars on the worker. Each Stage 3 addition is a configuration change against a stable API surface.

## Consequences

**Positive**

- No rewrite cost at stage boundaries. Stage 2 hoists `KleeRunner.execute` into a Celery task; everything else is unchanged. Stage 3 is operational configuration, not code.
- Tests written against the protocols (e.g. an endpoint test that uses a `FakeJobStore`) are reusable across stages. Stage 2 doesn't invalidate the Stage 1 test suite.
- The API contract is stable from day one. The frontend can be developed without knowing whether execution is synchronous or queued.

**Negative**

- Stage 1 has small upfront over-design relative to the simplest possible implementation. `POST /jobs` returns a `job_id` and an in-memory dict tracks state, when it could just return the result. We accept this cost as the price of avoiding a rewrite.
- The principle requires discipline. Any time a Stage 1 design choice would force a Stage 2 or 3 rewrite, the choice is wrong. This must be checked before writing code, not after.

**Load-bearing**

- The async-shaped API contract. Breaking it (e.g. returning the result directly from `POST /jobs` for "simplicity") would force a frontend rewrite at Stage 2.
- The protocol-based seams. Coupling endpoints directly to `InMemoryJobStore` or `DockerKleeRunner` would force endpoint rewrites at Stage 2.
- The `runner/` separation. Pulling runner code into `backend/src/klee_web/runner/` would conflate two deployment units.

**Out of scope for this ADR**

- The specific protocol surfaces (covered when those types are first introduced, likely ADR-0004 onwards).
- Caching strategy (Stage 2, separate ADR).
- Sandboxing choice between gVisor and Firecracker (Stage 3, separate ADR).
- Observability stack (Stage 3, separate ADR).

## References

- Old klee-web at `https://github.com/klee/klee-web` as a counter-example: the original ran a similar three-tier design but accumulated rewrites at each layer over time.
