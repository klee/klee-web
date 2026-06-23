# 0015. Centralised configuration via a Settings object

**Status:** Accepted, 2026-06-23

## Context

Stage 2 reads configuration from the environment. Stage 1 had one such value, `KLEE_FAKE_RUNNER`. Stage 2 adds `REDIS_URL`, and the queue work will add a broker URL, a result-cache TTL, and worker limits. The reads so far are inline `os.environ.get` calls in `deps.py`.

Inline reads scale badly. The variable name is an untyped string, so a typo returns `None` and falls through to a default with no error. For `REDIS_URL` that means a silent drop to the in-memory store, which under a separate worker process is a split-brain rather than a crash. There is no single place that lists what the application reads from the environment, and no validation of the values.

The portability research question sharpens this. The values that differ between deployment targets are exactly the redeploy-delta the question measures. They are easier to count and reason about in one declared surface than scattered across call sites.

## Decision

A single `Settings` class (`pydantic-settings` `BaseSettings`) declares every configuration value as a typed field. `get_settings()` builds it once per process behind `@lru_cache`, so the environment is read once. The dependency providers in `deps.py` read fields off `Settings` instead of calling `os.environ` directly.

Each field maps to an environment variable by name and carries a default. Optional values keep the silent default that is correct for development: `redis_url` defaults to `None`, which selects `InMemoryJobStore`, so a developer needs no configuration. A value declared without a default fails loudly the first time settings are read, with a Pydantic validation error, rather than degrading in silence.

The scope is the values actually read today: `redis_url` and `klee_fake_runner`. Constants with no current need to vary stay constants. `IMAGE_TAG` in the runner is one such case. It moves into `Settings` when Stage 2 needs a versioned or registry-qualified tag, not before.

## Consequences

- Every environment value the application reads is visible in one class. That class is also the redeploy-delta surface the portability question measures.
- A misspelled field is an attribute error the type checker catches, not a silent fallback to a default.
- Tests override configuration by constructing or replacing `Settings`, rather than mutating `os.environ`.
- `pydantic-settings` is a new dependency. It is small and sits on the Pydantic stack the project already uses.
- `@lru_cache` means the environment is read once per process. A test that mutates the environment must call `get_settings.cache_clear()`, the same constraint already noted for the cached Redis client.

## References

- ADR-0014: RedisJobStore on Redis hashes, where `REDIS_URL` is introduced as configuration.
- ADR-0008: KleeRunner protocol surface, the home of the FakeKleeRunner that `KLEE_FAKE_RUNNER` selects.
