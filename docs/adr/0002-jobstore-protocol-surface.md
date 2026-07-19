# 0002. JobStore protocol surface

**Status:** Accepted, 2026-05-19

**Amended 2026-06-21:** The protocol has since grown from four methods to six, both additions made within Stage 1 as features landed rather than at a stage boundary. `set_partial_result` was added for progress streaming, when `POST /jobs` became non-blocking and a running job emits partial results. `request_cancel` was added for user cancel (ADR-0013), along with the `Job.cancel_requested` flag. The decision and reasoning below stand. The load-bearing invariant is the stability of the protocol shape across the Stage 1 to Stage 2 swap, not the literal count, and `RedisJobStore` implements all six (ADR-0014).

> **Amendment, 2026-07-18:** ADR-0024 retires `InMemoryJobStore`. The Protocol remains, and handler tests now use a test-only fake.

## Context

Stage 1 of klee-web (per ADR-0001) needs an in-memory store for tracking job state across the lifetime of an HTTP request. Stage 2 will need the same operations against Redis, with the endpoints unchanged. The endpoints must depend on something the type checker can verify, without knowing which implementation is wired at runtime.

Per the strictly additive principle in ADR-0001, the abstraction over storage must be designed once and held across stages. Changing it at the stage boundary defeats the purpose. The shape of the abstraction is therefore load-bearing on the whole staged plan.

## Decision

`JobStore` is a `typing.Protocol` defined in `backend/src/klee_web/jobs/store.py`. Four async methods:

```python
class JobStore(Protocol):
    async def create(self, job: Job) -> None: ...
    async def get(self, job_id: UUID) -> Job | None: ...
    async def update_status(self, job_id: UUID, status: JobStatus) -> None: ...
    async def set_result(self, job_id: UUID, result: JobResult) -> None: ...
```

A `JobNotFound` exception accompanies the protocol for the missing-UUID cases.

### Why Protocol over ABC

Structural typing. Implementations satisfy `JobStore` by having the right methods; no `class X(JobStore):` inheritance declaration needed. Three concrete benefits:

1. Implementations do not import the protocol module. Refactoring or renaming `JobStore` does not ripple into every implementation's imports.
2. Test doubles are throwaway classes without parent. `FakeJobStore` (or any one-off in a test) only needs the four methods; no inheritance hierarchy to maintain.
3. Retroactive type-matching. A third-party class with the right shape can be plugged in without modification.

ABC would be the right tool if `JobStore` had shared implementation across subclasses. It does not. In-memory and Redis implementations share zero code; they share only the shape. Protocol expresses the same constraint without the unused coupling.

### Why all methods async

`asyncio.Lock` (used by `InMemoryJobStore`) is acquired via `async with`. The Stage 2 Redis implementation will need network I/O against a real Redis server, which is async by nature in modern Python (`redis-py` async client). Declaring `async` now keeps the protocol stable across the stage boundary; the in-memory implementation pays a trivial overhead for that consistency.

If Stage 1 had been sync, the Stage 2 swap would require changing every handler signature from sync to async, which is exactly the kind of stage-boundary rewrite the strictly additive principle is meant to prevent.

### Why `get` returns `Job | None` instead of raising

The handler decides what a missing UUID means in its context. For `GET /jobs/{job_id}`, missing means HTTP 404; for some future internal scan, missing might just mean "skip". Forcing the store to raise on miss would couple it to one handler choice. Returning `Job | None` lets each caller decide. The pattern matches stdlib `dict.get`.

### Why `update_status` and `set_result` raise on missing UUID

Fail loudly. If a handler asks the store to mutate a UUID that does not exist, that is a programmer bug (the handler used a stale or wrong ID), not a user-facing condition. A silent no-op would mask the bug and produce wrong state downstream. `JobNotFound` surfaces it immediately.

### Why `set_result` is atomic

`set_result` writes `job.result` AND advances `job.status` to `done` in one `async with self._lock:` block. This removes a real bug class: without atomicity, a concurrent GET could see a job whose `result` was populated but whose `status` was still `running`, between the two writes. With `set_result` atomic, no consumer ever observes that inconsistent intermediate state.

A separate `update_status` exists for the `pending -> running` and `-> failed` transitions where there is no result to attach.

## Consequences

**Positive**

- Endpoint code depends only on `JobStore` (the protocol) via `Depends(get_job_store)`. The endpoint never references `InMemoryJobStore` or `RedisJobStore` by name. The Stage 2 swap is a one-line change in `deps.py`.
- Test fakes are minimal. Handler tests use the real `InMemoryJobStore` (it is cheap enough); a `FakeJobStore` could substitute at any time without inheritance.
- The four-method shape is small enough to implement quickly in Redis later, and broad enough to support polling-based status updates.

**Negative**

- Stored `Job` instances are mutable. `set_result` modifies the stored object in place rather than replacing it. If a `Job` reference is retained outside the store (handler code holding a local variable, for instance), the mutation is visible there too. For Stage 1 this is acceptable because handlers do not retain `Job` references after store operations; revisit if state mutation becomes a bug source.
- `update_status` does not enforce a state machine. The store does not check that `pending -> done` is invalid (only `pending -> running -> done` is intended). Handlers are responsible for valid transitions. A future revision could add explicit state-machine validation as a wrapper around any `JobStore`.

**Load-bearing**

- The four-method shape is inherited by Stage 2's `RedisJobStore`. Adding or removing a method at the stage boundary breaks the additive principle.
- The async-method signatures must not change. Stage 2's Redis driver is also async; if Stage 1 had been sync, the Stage 2 swap would require touching every handler signature.
- The raise-on-missing rule must hold for both implementations. `RedisJobStore` must also raise `JobNotFound` (not a Redis-specific exception) on missing keys, so handlers can catch one exception type across stages.
- `set_result` atomicity must hold under Redis too. In Redis this likely means a Lua script or `MULTI/EXEC` transaction; the atomicity is part of the contract, not an in-memory accident.

**Out of scope**

- `KleeRunner` protocol surface (its own ADR, written once Stage 1 runner work is complete and the protocol stops being one method).
- State-machine validation (could be added later as a thin wrapper around any `JobStore`).
- Cache eviction policy for the eventual `RedisJobStore` (Stage 2 ADR).
- Authorisation (who can `set_result` on which job). Stage 3 concern.

## References

- ADR-0001: stage-based additive architecture.
- PEP 544: structural subtyping with Protocols.
