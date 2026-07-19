# 0024. One full-application topology

**Status:** Accepted, 2026-07-18

## Context

The in-memory stores and in-process dispatcher made Stage 1 runnable before Redis and Celery existed. Their Protocol boundaries then let Stage 2 move execution onto a Worker without changing the HTTP API or frontend.

After that migration, retaining both paths meant supporting two executable products. The fallback path duplicated construction logic and composed API tests through a Runner that the deployed API does not own. It also added nothing to the portability measurement, which concerns redeploying the full system rather than preserving an earlier development topology.

## Decision

Support one full-application topology: nginx, FastAPI, Redis, Celery Workers, and per-Job KLEE containers, orchestrated by Compose. Supported deployments use gVisor. `runc` remains only as a comparative integration-test control.

`REDIS_URL` and `CELERY_BROKER_URL` are required and validated at FastAPI startup. Production construction uses Redis stores, Celery dispatch and fleet services, and `DockerKleeRunner`. The API never constructs a Runner.

Keep the Protocols as boundaries for core logic and tests. Deterministic stores, caches, dispatchers, usage counters, and Runners live under `tests/` and are injected directly. Browser CI runs the Compose topology through a real gVisor Runner.

## Consequences

**Positive**

- There is one runtime architecture to deploy, test, document, and explain.
- Missing infrastructure configuration fails during startup rather than on the first Job request.
- Browser coverage exercises nginx, Redis, Celery, the Worker, Docker, and gVisor.
- The Protocol seams remain available without shipping alternative runtime implementations.

**Negative**

- A full local run requires Docker, Compose, Redis, Celery, and a registered gVisor runtime.
- The project no longer provides a hot-reload full-stack command.
- Browser CI has a heavier setup because it installs gVisor and starts the full stack.

## References

- ADR-0001: the stable API and Protocol boundaries remain, but Stage 1 is no longer retained as an executable topology.
- ADR-0002: the `JobStore` Protocol remains, but `InMemoryJobStore` does not.
- ADR-0015: centralised settings remain, but Redis and Celery no longer have optional defaults.
- ADR-0016: the dispatcher seam remains, but `InProcessDispatcher` does not.
- ADR-0017: the submission cache key remains, but `InMemoryResultCache` does not.
