# 0017. Result cache keyed on the submission

**Status:** Accepted, 2026-06-25

> **Amendment, 2026-07-18:** ADR-0024 retires `InMemoryResultCache`. The cache-key and API short-circuit decisions remain.
>
> **Amendment, 2026-08-11:** The key now includes the exact Runner image identity and a hash of the `JobResult` schema alongside the canonical `JobRequest`. This invalidates entries when KLEE, Runner code, or the result contract changes. The cache TTL is 48 hours and reads do not refresh it.

> **Amendment, 2026-08-22:** Successful Redis cache reads now refresh the result's 48-hour retention window. Job-record reads retain their existing fixed-expiry behaviour.

## Context

Stage 2 caches results so an identical resubmission does not run KLEE again. The brief calls the key a "program hash", but the program text alone is the wrong key. A submission is source plus flags, and the flags change the result: `query_format=kquery` adds a path constraint per test case, `max_time` and `max_memory` bound exploration. A source-only key would let a `query_format=none` run satisfy a later `kquery` submission and return results missing the constraints the user asked for.

Reuse is sound only because KLEE is deterministic on the same source, flags, version, and solver. That same caveat sets the limits of what is safe to cache and how long a cached result stays valid.

The cache also has to fit the Stage 2 split (ADR-0016): the API process and the worker both need it, and a hit should not pay for the machinery a miss needs.

## Decision

The key is a SHA-256 over the canonical serialisation of the whole `JobRequest` (source and all flags), the exact Runner image identity, and a hash of the `JobResult` schema. Reuse requires all three to match. The user-facing term is an identical submission.

Only a job that reached `done` with `halt_reason == completed` is cached. A completed run explored every path, so it is a reproducible function of the input. A timed-out run is bounded by wall-clock and explores a different set of paths from one machine or load to the next, so it is not reproducible and is not cached. Cancelled runs are user-timed, failed runs may be a transient infrastructure hiccup, and a compile error is deterministic but is only ever re-hit on byte-identical broken source. None are cached.

The read sits in `POST /jobs` before dispatch, the write in `run_job` after a completed result. On a hit the handler creates the job already `done` with the cached result and skips dispatch, so the first poll returns it and the hit never enters the queue or holds a worker slot. The write lives in `run_job` because that is the single place a fresh result is produced by the worker. Read and write share one pure `cache_key`.

A `ResultCache` Protocol with `get` and `set` defines the cache boundary. `get_cache` constructs `RedisResultCache` using the required `REDIS_URL`, the same shape as `get_job_store` (ADR-0014). ADR-0024 retired the in-memory runtime cache; test doubles remain under `tests/`.

The result-cache TTL is a sliding 48-hour retention window. A write starts the window, and every successful read restores it to the full 48 hours. `RedisResultCache.get` uses Redis `GETEX`, so retrieving the value and refreshing its expiry are one atomic cache operation. A miss returns no value and does not create a key. Because `GETEX` updates expiry metadata, a cache hit is also a Redis write and the expiry update is recorded in Redis's append-only file (AOF).

This sliding policy applies only to result-cache entries. `RedisJobStore.get` continues to read a job record without changing its expiry, so job-record reads retain their fixed-expiry behaviour. Job-record writes keep their existing TTL refresh semantics from ADR-0014.

## Consequences

- An identical resubmission returns on the first poll and never touches the worker pool. The short-circuit is additive: the contract and the frontend are untouched, the ADR-0001 promise kept again.
- A program that always times out re-runs on every submission. The cache helps least where a run costs most. This is the price of caching only reproducible results, and it is the right price.
- A popular completed result can remain cached while it continues to receive hits. Each hit writes updated expiry metadata to Redis and its AOF.
- Runner image identity and result-schema changes produce different cache keys, so sliding expiry does not allow hits on an old key to serve results for a new image or schema. Entries that receive no further hits expire after 48 hours.
- Concurrent identical submissions both run. The cache dedupes later submissions, not simultaneous ones. The write is idempotent, so the cost is wasted compute in a narrow window, never a wrong result. Single-flight is parked as a future issue.
- The read and the write live in different modules. That is the two halves of a cache in their natural places, the request and the result, over one shared `cache_key`, not duplicated logic.
- A miss pays a cache `get` per submission, one per `POST`, not per poll. Cheap for a human-paced UI.

## References

- ADR-0001: stage-based additive architecture, the additive promise this keeps.
- ADR-0014: RedisJobStore, the same Protocol-plus-`REDIS_URL`-provider shape and TTL reasoning.
- ADR-0015: centralised Settings, the selection mechanism.
- ADR-0016: the shared `run_job` and the API/worker split the write sits in.
- ADR-0024: the Redis-only runtime topology and retirement of the in-memory cache.
