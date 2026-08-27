# 0008. KleeRunner protocol surface

**Status:** Accepted, 2026-05-21

> **Amendment, 2026-08-27:** `execute` now also receives the Job identifier and optional progress and parsing callbacks. The Protocol includes `cancel(job_id)`. `DockerKleeRunner` uses the identifier to name and cancel the container, while its stream transport leaves the progress callback unused. The failure split and typed result remain unchanged.

## Context

Stage 1 ships `DockerKleeRunner`: shell out to `docker run`, parse the output. Stage 2 moves execution into Celery workers on separate VMs. Stage 3 may swap the container runtime. Endpoints must not change across stages, so the abstraction is held once.

Two structurally different failure modes must be distinguishable: runner failures (docker missing, image missing, container crash, OOM) versus user failures (source did not compile, KLEE found a bug). Conflating them forces handlers to demultiplex via string-matching exception messages.

## Decision

`KleeRunner` is a `typing.Protocol` in `backend/src/klee_web/jobs/runner.py`. One async method:

```python
class KleeRunner(Protocol):
    async def execute(self, source: str, flags: KleeFlags) -> JobResult: ...
```

`KleeRunnerError` accompanies it for runner failures only. Compile failures flow through `JobResult.compile_error`; KLEE-detected runtime errors flow through `TestCase.error` on the failing test case.

### Single method

Source + flags in, `JobResult` out. Exposing `start`/`wait`/`read_output` would leak Docker-subprocess shape into Stage 2's Celery-task shape.

### Async

`asyncio.create_subprocess_exec` is awaitable; a 5-minute KLEE run cannot stall the event loop. Stage 2's Celery `AsyncResult` is also awaitable. Sync now would force a handler-signature rewrite at the stage boundary.

### Error split

The runner DID succeed when the user's C failed to compile or KLEE found a bug; it did NOT succeed when docker crashed. Mapping both to one exception conflates "show the user clang's stderr" with "log an operator incident".

### Returns `JobResult`, not raw bytes

The runner owns the translation from KLEE's filesystem output to the typed schema. Splitting that across the abstraction would have Stage 2's worker ship raw output back to the backend for re-parsing.

## Consequences

**Positive**

- One type-checked surface across Stage 1 Docker and Stage 2 Celery. Swap is a one-line change in `deps.py`.
- `FakeKleeRunner` is ~30 lines, no inheritance.
- Handler in `api/jobs.py` catches exactly one exception type from the runner.

**Negative**

- KLEE-detected runtime errors ride on `TestCase.error`, not the exception path. A new contributor might expect them as exceptions; the schema and parser surface the truth.
- No streaming. Path-discovery progress would need a parallel protocol.

**Load-bearing**

- The single-method async shape is inherited by Stage 2's runner. Adding a lifecycle method at the stage boundary breaks the additive principle.
- "Runner failures raise, user failures populate `JobResult`" must hold in every implementation, including Celery.

**Out of scope**

- Streaming partial output. Caching identical (source, flags) pairs (Stage 2 cache concern). Authorisation around who may call `execute` (Stage 3).

## References

- ADR-0001: stage-based additive architecture.
- ADR-0002: JobStore protocol surface (parallel decision).
- ADR-0007: JobCreated response model (the polling discipline that makes async-runner viable).
