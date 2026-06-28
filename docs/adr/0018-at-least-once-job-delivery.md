# 0018. At-least-once job delivery and worker-death recovery

**Status:** Accepted, 2026-06-26

## Context

The Stage 2 split (ADR-0016) moved KLEE off the API process onto a Celery worker. A worker that dies mid-job takes the job with it. The job sits in the store at `running` and the user polls a status that never resolves. ADR-0016 named this gap and left it to be closed here.

Recovering the job means the broker notices the worker is gone and hands the task to another worker. The Redis transport has no real acknowledgement channel. A reserved message is held until a single global visibility timeout expires, then restored to the queue. So one timer is the whole recovery mechanism, and the rest follows from sizing it correctly.

A job's wall-clock is bounded, because `max_time` is capped at 300s in the flag schema (ADR-0005). That bound is what makes a fixed timeout safe.

## Decision

Deliver each job at least once. `task_acks_late` holds the acknowledgement until `run_job` returns, so a worker that dies mid-job never acknowledged its task and the broker redelivers it. `task_reject_on_worker_lost` requeues the task when the worker process is lost rather than marking it failed. `worker_prefetch_multiplier` stays 1 so a worker does not hold tasks it is not running.

On Redis the redelivery is driven by the visibility timeout, not by `reject_on_worker_lost`. Set it to twice the `max_time` ceiling, from the same shared constant the schema caps `max_time` with. The timeout has to exceed the worst-case job wall-clock. If it is shorter, a job that is still running is redelivered to a second worker while the first still holds it, and the two collide. Twice the ceiling clears 300s plus compile, parse, and flush overhead with margin for a loaded host, and recovers a dead worker's job inside that window instead of the one-hour Redis default.

The timeout is one global number. The Redis transport has no per-message visibility, so a 10s job is reclaimed no faster than a 300s job after a worker death. This is a transport limit, not a choice.

Redelivery runs `run_job` again, which forces three changes:

- **Reclaim the container name.** A dead worker leaves its container orphaned under the deterministic name `klee-job-{id}`, because the container runs under dockerd, not as a child of the worker. The redelivered run would hit a name collision and fail the job it exists to save. The runner does a best-effort `docker rm -f` of the name before `docker run`. This is safe only because the visibility timeout guarantees redelivery happens after the original worker is dead, so the only holder of the name is an orphan. The deterministic naming that cancel depends on (ADR-0013, ADR-0009) is unchanged.
- **Short-circuit a finished job.** A worker can write the result and die in the gap before the acknowledgement, so a redelivered task can find its job already `done`. `run_job` returns at once instead of re-running KLEE for a result already in the store.
- **Cap the redelivery loop.** A job that reliably kills its worker would redeliver forever and take down workers in turn. `run_job` increments an internal `attempts` count on the job, and once three attempts have not completed it marks the job `failed` with a user-facing reason instead of running again. The count lives in the store, not the response. A failed job is never cached (ADR-0017), so a resubmission runs fresh.

The broker stays Redis. Celery abstracts the transport, so only the visibility-timeout line is Redis-specific. A later swap to RabbitMQ (instant requeue on consumer loss, no timeout to size) or SQS (per-message visibility, native dead-letter queues) is a config change, not an application change.

## Consequences

- A worker dying mid-job no longer loses it. The job is redelivered and finishes on another worker, inside the visibility-timeout window.
- Recovery latency is the same for every job. A short job whose worker dies waits the global timeout to be reclaimed, the same as a long one. The Redis transport cannot do better. Faster reclaim of short jobs is the reason to revisit the broker later, parked as a future issue.
- The visibility timeout is coupled to the `max_time` ceiling through the shared constant. Raising the ceiling raises the timeout with it. A change that decouples them brings back the concurrent-double-run hazard, so the constant says so where it is defined.
- `rm -f` before every run force-removes whatever holds the name. Its safety rests entirely on the visibility timeout being longer than the worst-case job. The two are one decision, not two.
- The poison cap bounds a bad job to three attempts rather than the whole fleet, at the cost of three runs before it gives up. The user gets a clear reason and can resubmit.
- The JobStore Protocol grows (ADR-0002): an attempts counter and a failed-with-reason write, one more method on each implementation.
- The in-process path gets no redelivery. It has no broker to redeliver from, so an API restart still loses its background jobs, unchanged from ADR-0016. That is the zero-config dev path, where losing in-flight work on a restart is acceptable.

## References

- ADR-0001: stage-based additive architecture.
- ADR-0002: JobStore protocol surface, which this grows.
- ADR-0005: the `max_time` ceiling the timeout is sized against.
- ADR-0013: cancel as a user-triggered halt, whose deterministic naming the reclaim preserves.
- ADR-0016: the dispatcher seam, whose worker-death gap this closes.
- ADR-0017: result cache, why a failed job is not cached.
