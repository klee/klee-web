# 0018. Minimal failsafes: at-most-once delivery with cancel recovery

**Status:** Accepted, 2026-06-30

> **Amendment, 2026-08-25:** A container-owned watchdog now bounds the complete Runner lifecycle at `max_time + 60` seconds, including compilation and archive creation. It remains effective if the Worker dies. Celery gives the Worker task the same hard limit, while the KLEE subprocess keeps its separate host-side bound.

## Context

The Stage 2 split (ADR-0016) moved KLEE off the API process onto a Celery worker. A worker that dies mid-job takes the job with it. The job sits in the store at `running` and the user polls a status that never resolves. ADR-0016 named this gap and left it to be closed here.

There are two ways to close it. Make delivery reliable: hold the broker acknowledgement until the job finishes, so a dead worker's job is redelivered to another worker and completes on its own. Or make recovery cheap: let a dead worker's job drop, and give the user one action that always resolves it. Reliable delivery is a coupled stack: a visibility timeout sized against `max_time`, a container reclaim before each run, a poison cap for a job that keeps killing workers, and a resolver for the stalled state, plus a broker that requeues quickly to be worth it. Cheap recovery needs one thing to hold: cancel must work even when no worker is alive.

KLEE also does not honour its own `--max-time` while blocked inside a hard solver query, so a job can run past its budget. Either model needs something outside KLEE to stop a runaway.

## Decision

Take the minimal path: deliver each job at most once, and recover a lost job by cancel, not by redelivery. This is the old klee-web's model with one addition, a cancel button in place of a forced resubmit.

**At-most-once delivery.** Leave `task_acks_late` off, so Celery acknowledges a task when the worker pool accepts it for execution. A worker that dies mid-job has already acknowledged, so the broker does not redeliver and the job stays `running` until the user acts. `worker_prefetch_multiplier` is 1, but an active task's early acknowledgement frees consumer credit and lets the worker reserve another task. Active tasks are lost with a dead worker. Reserved tasks have not started and remain eligible for broker restoration, while tasks still in the broker are untouched.

**Cancel is the recovery.** A user cancel resolves a job from the API side, not the worker (ADR-0013, the eager flip). The endpoint writes the terminal state into the store directly, so it lands whether the worker is alive, dead, or never ran. This is what makes at-most-once safe: a dropped job is never stuck, because one click resolves it. The user resubmits if they still want the result, and an identical completed submission is served from the cache (ADR-0017).

**Three compute bounds.** Cancel handles the user-facing state. Three independent limits handle the compute:

1. **KLEE subprocess bound.** KLEE receives `--max-time`. The entrypoint also waits at most `max_time + 15` seconds, then uses the same SIGINT, grace, and SIGKILL sequence as cancellation if KLEE is blocked in a solver query. It writes a sentinel so the parser reports a time-limit stop.
2. **Complete Runner watchdog.** A watchdog starts with the container and hard-exits the entrypoint after `max_time + 60` seconds. It covers input, compilation, KLEE, replay, and archive creation. It remains active after Worker loss, so Docker can remove the stopped `--rm` container.
3. **Celery hard `task_time_limit`.** The Worker task has the same `max_time + 60` hard limit. The pool supervisor enforces it, so it frees the slot if the task process freezes. The container watchdog independently bounds the Runner if that task process dies.

**Broker stays Redis.** At-most-once asks nothing of the broker beyond plain delivery, so a faster-requeue broker (RabbitMQ requeuing on a dropped connection, SQS with per-message visibility) buys nothing here. Those only pay off on the redelivery path this ADR declines. Celery keeps the transport a config swap if that path is ever wanted.

## Consequences

- A worker dying mid-job drops that job. The user sees it stay `running` and cancels, which resolves it at once. Recovery is one action, not an automatic retry.
- A dropped job's container keeps running until the watchdog stops it, up to `max_time + 60` seconds from container start. This is bounded waste rather than an unbounded orphan. A reclaim before each run would remove the waste, but it only matters with redelivery, which we do not do.
- A job that reliably kills its worker is not capped at a number of attempts, because it is never redelivered. It dies once with its worker, and the user is free not to resubmit it. The poison-cap machinery is unnecessary.
- The JobStore Protocol stays at six methods (ADR-0002). The attempts counter and failed-with-reason write that redelivery needed are gone.
- Recovery rests entirely on the cancel eager flip. If that write fails, a dropped job is genuinely stuck, so the flip is the load-bearing failsafe and is tested as one (ADR-0013).
- Robustness is given up on purpose. A job lost to a worker crash is not recovered for the user automatically, where reliable delivery would have re-run it. The trade buys a smaller system: fewer coupled timers, no broker requirement beyond Redis, and no per-job reclaim.

## References

- ADR-0001: stage-based additive architecture, why the reapers live in the unit of execution.
- ADR-0002: JobStore protocol surface, which this leaves at six methods.
- ADR-0005: the `max_time` ceiling the entrypoint bound is sized against.
- ADR-0013: cancel as a user-triggered halt, whose eager flip is the recovery mechanism.
- ADR-0016: the dispatcher seam, whose worker-death gap this closes.
- ADR-0017: result cache, which serves an identical resubmission.
