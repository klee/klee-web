# 0014. RedisJobStore on Redis hashes

**Status:** Accepted, 2026-06-21

> **Amendment, 2026-07-18:** ADR-0024 makes `RedisJobStore` the only production implementation and removes the `REDIS_URL` selector. The Redis hash model and atomicity decisions remain.

## Context

Stage 2 moves job state out of the API process so a worker process can write status and results while the API keeps serving polls. This is the storage swap ADR-0001 planned and the one ADR-0002's `JobStore` Protocol was shaped for. The in-memory store's `asyncio.Lock` does not span processes, so the Redis implementation has to provide its own safety.

The concrete hazard is two writers on one job. The worker writes `status` and `result`, the API writes `cancel_requested`. If the job were a single JSON blob mutated read-modify-write, `request_cancel` could read the blob, the worker could call `set_result`, then `request_cancel` could write its stale blob back and erase the result. ADR-0002 names this class and makes `set_result` atomicity load-bearing for the Redis store.

The store must satisfy the live `JobStore` Protocol (now six methods, see the ADR-0002 amendment), raise the shared `JobNotFound` on a missing UUID, and bound its own growth. An in-memory dict never had to evict because a process restart cleared it. Redis persists, so jobs would otherwise accumulate forever.

## Decision

Store each `Job` as a Redis hash at `job:{id}`, one field per attribute (`id`, `status`, `created_at`, `result` as a JSON string, `cancel_requested` as `0`/`1`). `get` does `HGETALL` and rebuilds the `Job` through Pydantic.

Writes are field-level. The two writers touch disjoint fields, the worker only `status` and `result`, the API only `cancel_requested`, so neither can clobber the other. `set_result` writes `status` and `result` together in one multi-field `HSET`, a single atomic command, so no poll ever observes a populated `result` while `status` is still `running`. That is the atomicity ADR-0002 requires, with no Lua script and no `WATCH`/`MULTI`/`EXEC`. `cancel_requested` is `exclude=True` on the model and a JSON blob would drop it, so it is stored explicitly as its own field.

Mutators raise `JobNotFound` via `EXISTS` then `HSET`. `HSET` is an upsert, so a blind `HSET` on a missing key would silently create a malformed half-job. `EXISTS` detects absence and raises the shared `JobNotFound`, which is the fail-loud rule for a stale UUID, and it keeps `create` (writes a full new hash) distinct from the mutators (only ever touch a job that exists). The check-then-write window is closed in practice by the always-refreshed TTL and the absence of any delete path, so a Lua guard would defend a race that cannot occur here.

The TTL on `job:{id}` is a flat 24h, refreshed on every write. The floor is correctness: a TTL shorter than a running job would let `set_result` race the key's expiry at the end of a long run. The value above that floor tracks how long a user should be able to come back for results, which does not scale with how long the job ran, so a flat duration fits better than a multiple of `max_time`. The max-job-duration sizing belongs instead to Celery's visibility timeout, a separate mechanism on the queue, decided with the Celery work.

`RedisJobStore` takes an injected `redis.asyncio` client. `get_job_store` builds the client from `REDIS_URL` and selects `RedisJobStore` when that variable is set, otherwise `InMemoryJobStore`, which stays the zero-config default for development and tests. `REDIS_URL` differs per deployment target, so it is configuration rather than a constant. The client connects lazily and binds its pool to the event loop of first use. `@lru_cache` on `get_job_store` yields one pool per process, which is correct under single-process uvicorn and under future multi-worker alike.

Both implementations are verified by one parametrized contract suite that exercises only Protocol behaviour, alongside fakeredis-backed unit tests and one integration test against a real Redis.

## Consequences

- The Stage 2 storage swap is the `REDIS_URL`-gated branch in `get_job_store`. Endpoints and frontend are untouched, which is the ADR-0002 promise made good.
- The contract suite turns ADR-0002's claim that both implementations behave identically from prose into an executed test, and is the guard that the swap stays behaviour-preserving.
- The status and result store is our own `job:{id}` keyspace, not Celery's native result backend. This keeps the `GET /jobs/{id}` contract and the `JobStore` Protocol intact, at the cost of not reusing a built-in Celery feature.
- Redis is the wrong home for anything that must not expire. An audit trail and admin stats need durable storage (the Stage 3 Postgres), not a TTL'd key.
- `get` pays a per-poll cost: an `HGETALL`, a Pydantic validate, and a JSON parse of the `result` field. Fine for a human-paced polling UI, worth remembering if poll volume grows.
- `cancel_requested` now exists in two shapes, excluded from the API response model but an explicit stored field. A future change to the model has to keep storing it, or cross-process cancel breaks silently.

## References

- ADR-0001: stage-based additive architecture.
- ADR-0002: JobStore protocol surface, the contract this implements, including its six-method amendment.
- ADR-0013: cancel as a user-triggered halt, the origin of `request_cancel` and the `cancel_requested` flag.
