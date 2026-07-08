# 0009. Per-job containers, not a long-lived runner process

**Status:** Accepted, 2026-05-21

> **Superseded in part (2026-07-08).** ADR-0021 replaces the bind-mount transport
> described below: the source now enters on stdin and the output leaves as a tar on
> stdout, so there is no `-v <tmpdir>:/work` and no `--user`. The per-job container
> lifetime this ADR decides is unchanged. The Positive "Stage 3 gVisor swap is a flag
> change, no application code" no longer holds: gVisor needs `--kdalloc=false`, and the
> sandbox pillar has since moved to Firecracker.

## Context

`DockerKleeRunner.execute` could either spin up a fresh container per job (`docker run --rm` each time) or maintain a single long-lived container that accepts work over some channel and runs KLEE many times. Both end up shelling out to KLEE; the difference is the container lifetime.

This choice is load-bearing on Stage 3, which swaps `--runtime=runsc` (gVisor) to harden the sandbox. The swap is trivial under per-job containers and harder under a long-lived process.

## Decision

One container per job. Each `POST /jobs` calls `docker run --rm -v <tmpdir>:/work -e KLEE_MAX_TIME=... -e KLEE_MAX_MEMORY=... klee-web-runner`. The container compiles, runs KLEE, writes outputs to the bind mount, exits. `--rm` deletes the container.

### Isolation

Every job starts from a known-clean filesystem. KLEE's tmp files, leaked fds, half-cleaned output dirs from one job cannot affect the next. A long-lived runner accumulates state; per-job containers eliminate that class of bug by construction.

### Resource accounting and crash resilience

Docker enforces memory and cpu limits at the container boundary. A KLEE that hits the limit gets killed cleanly without affecting other jobs. A KLEE that segfaults takes its container down, not the runner. A long-lived runner would have to detect, isolate, and recover from each crash on its own.

### Cleanup is `docker rm`

`--rm` removes the container record; the bind-mounted tmpdir on the host is cleaned up by `tempfile.TemporaryDirectory`'s context manager exit. Two trivial guarantees instead of a hand-rolled "purge state between jobs" routine inside a long-lived process.

### Stage 3 sandbox swap

gVisor is enabled per container via `--runtime=runsc` on `docker run`. Under per-job containers, that flag is a one-line change. A long-lived runner running gVisor would either need to be wrapped in gVisor itself (one big sandbox shared across all jobs, defeating the isolation point of gVisor), or would have to spawn nested containers (re-arriving at per-job containers but with extra plumbing).

### What we trade away

Container startup is roughly 100ms on a warm image, so we pay it on every job. For KLEE runs that complete in seconds to minutes, this is rounding error. A long-lived runner could also cache compiled bitcode across identical sources, but Stage 1 has no incentive to deduplicate (job submissions are not expected to repeat) and Stage 2's Redis result cache covers the repeat case better than runner-local caching would.

## Consequences

**Positive**

- Stage 3 gVisor swap is a flag change, no application code.
- Resource limits and cleanup are docker-native; no in-process bookkeeping.
- Crashed KLEE jobs do not affect the runner or other jobs.

**Negative**

- ~100ms container-startup cost per job. Acceptable given KLEE's own duration.
- No runner-local caching of compiled bitcode. Acceptable since the cache lives in Stage 2's Redis layer where it benefits a wider set of jobs.

**Load-bearing**

- Per-job container lifetime is inherited by Stage 2: the Celery worker still calls `docker run` per task. Stage 3's gVisor swap depends on this lifetime.
- Cleanup via `--rm` and host-side `TemporaryDirectory` is the cleanup contract. A future change that retains containers (for debugging, say) must explicitly opt out of `--rm`.

**Out of scope**

- Pooling pre-warmed containers to amortise startup. Not worth the complexity at Stage 1 / 2 traffic levels.
- Runner-local bitcode cache (deferred to Stage 2's Redis cache).

## References

- ADR-0001: stage-based additive architecture.
- ADR-0008: KleeRunner protocol surface (the abstraction this lifetime choice sits inside).
