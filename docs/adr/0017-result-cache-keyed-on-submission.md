# 0017. Result cache keyed on the submission

**Status:** Accepted, 2026-06-25

> **Amendment, 2026-07-18:** ADR-0024 retires `InMemoryResultCache`. The cache-key and API short-circuit decisions remain.

## Context

Stage 2 caches results so an identical resubmission does not run KLEE again. The brief calls the key a "program hash", but the program text alone is the wrong key. A submission is source plus flags, and the flags change the result: `query_format=kquery` adds a path constraint per test case, `max_time` and `max_memory` bound exploration. A source-only key would let a `query_format=none` run satisfy a later `kquery` submission and return results missing the constraints the user asked for.

Reuse is sound only because KLEE is deterministic on the same source, flags, version, and solver. That same caveat sets the limits of what is safe to cache and how long a cached result stays valid.

The cache also has to fit the Stage 2 split (ADR-0016): the API process and the worker both need it, and a hit should not pay for the machinery a miss needs.

## Decision

The key is a SHA-256 over the whole `JobRequest`, source and all flags, serialised canonically. Identical means same source and same flags. The user-facing term is an identical submission.

Only a job that reached `done` with `halt_reason == completed` is cached. A completed run explored every path, so it is a reproducible function of the input. A timed-out run is bounded by wall-clock and explores a different set of paths from one machine or load to the next, so it is not reproducible and is not cached. Cancelled runs are user-timed, failed runs may be a transient infrastructure hiccup, and a compile error is deterministic but is only ever re-hit on byte-identical broken source. None are cached.

The read sits in `POST /jobs` before dispatch, the write in `run_job` after a completed result. On a hit the handler creates the job already `done` with the cached result and skips dispatch, so the first poll returns it and the hit never enters the queue or holds a worker slot. The write lives in `run_job` because that is the single place a fresh result is produced, shared by the in-process and Celery paths. Read and write share one pure `cache_key`.

A `ResultCache` Protocol with `get` and `set` carries `InMemoryResultCache` and `RedisResultCache`, and `get_cache` selects on `REDIS_URL`, the same shape as `get_job_store` (ADR-0014). The in-memory cache is the zero-config default, so the in-process path caches too.

The TTL is a flat 24h, set on write and never refreshed on read. A fixed lifetime is deliberate, because it is also the only invalidation. A runner-image change would otherwise serve old results forever, and a TTL refreshed on every hit would keep a popular stale entry alive against exactly that. It covers the common case, a user resubmitting within a session, and bounds how long a stale entry can outlive an image bump.

## Consequences

- An identical resubmission returns on the first poll and never touches the worker pool. The short-circuit is additive: the contract and the frontend are untouched, the ADR-0001 promise kept again.
- A program that always times out re-runs on every submission. The cache helps least where a run costs most. This is the price of caching only reproducible results, and it is the right price.
- There is no version in the key, so a runner-image bump serves stale results until the 24h TTL clears them. Acceptable for a rare, deliberate bump, and parked as a future issue rather than built now.
- Concurrent identical submissions both run. The cache dedupes later submissions, not simultaneous ones. The write is idempotent, so the cost is wasted compute in a narrow window, never a wrong result. Single-flight is parked as a future issue.
- The read and the write live in different modules. That is the two halves of a cache in their natural places, the request and the result, over one shared `cache_key`, not duplicated logic.
- A miss pays a cache `get` per submission, one per `POST`, not per poll. Cheap for a human-paced UI.

## References

- ADR-0001: stage-based additive architecture, the additive promise this keeps.
- ADR-0014: RedisJobStore, the same Protocol-plus-`REDIS_URL`-provider shape and TTL reasoning.
- ADR-0015: centralised Settings, the selection mechanism.
- ADR-0016: the shared `run_job` and the API/worker split the write sits in.
