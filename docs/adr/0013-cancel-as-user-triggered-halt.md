# 0013. Cancel as a user-triggered halt

**Status:** Accepted, 2026-06-15 (amended 2026-06-23, 2026-06-29)

## Context

Jobs run with `--max-time`. When KLEE reaches that limit it halts cleanly, emits the test cases found so far, and the job ends `done` with a `halt_reason`. Until now there was no way for a user to stop a job early. Someone who spots a mistake mid-run (a typo, a wrong assumption) had to wait out the time limit.

The obvious design treats a user cancel as its own terminal outcome: kill the container, discard whatever was produced, add a `cancelled` `JobStatus`, and render it in a separate results view. That invents a parallel concept where one already exists.

## Decision

A user cancel is the same event as a time-limit expiry, differing only in what triggers it. Model it as a new halt reason, `HaltReason.cancelled`, not a new `JobStatus`. The job still ends `done` and reuses the existing results rendering.

Preserve partial test cases the way a timeout does. KLEE's graceful halt-and-dump is wired to SIGINT, so the runner container's entrypoint traps SIGTERM (the conventional stop signal) and forwards SIGINT to the `klee` child, waiting for the flush before exiting.

Expose it as `POST /jobs/{job_id}/cancel`, a command rather than a deletion, since the job resource is not removed. The `KleeRunner` Protocol gains `cancel(job_id)`: Stage 1 implements it as `docker kill --signal=TERM` against a deterministically named container, and Stage 2 swaps the body for a Celery `revoke`. Tagging is backend-authoritative through a `cancel_requested` flag. The output parser never learns about cancel.

## Consequences

- Cancel reuses the whole results path. No separate status, no separate view, and partial test cases are shown exactly as a timeout's are.
- The entrypoint signal-forwarding is written once and is unchanged across stages, the same property gVisor relies on: change the surroundings, not the unit of execution.
- The SIGTERM-to-SIGINT translation in the entrypoint is non-obvious. A future reader will expect a passthrough. It exists because KLEE halts gracefully only on SIGINT, while SIGTERM is what orchestrators send by default.
- Cancel is best-effort against the container-startup window. A cancel issued before the container is killable returns 409 and does nothing, and the user retries once it is up. This keeps a cancelled job from ever being mislabelled, at the cost of an occasional no-op click in the first second or two.

## Amendment, 2026-06-23 (Stage 2 mechanism)

The Decision anticipated Stage 2 swapping the cancel body for a Celery `revoke`. Building the worker showed that to be wrong. `revoke(terminate=True)` signals the worker process running the task, not the KLEE container, so it would bypass the entrypoint's SIGTERM-to-SIGINT forwarding and KLEE would never get its graceful dump. The partial test cases this ADR exists to preserve would be lost.

Stage 2 keeps the Stage 1 kill unchanged (`docker kill --signal=TERM` against the named container) and only moves who triggers it. Once a job runs on a worker the API cannot reach the container, so the cancel endpoint sets `cancel_requested` and nothing else. The executor that owns the container, the in-process task or the worker, watches that flag and runs `cancel(job_id)` locally. The mechanism is the same in both run modes, and the container always gets the same graceful signal.

This retires the startup-window 409. The flag persists, so a cancel on a pending or just-started job is honoured whenever the executor reaches it instead of returning a no-op to retry. The endpoint's 409 now means only that the job is already terminal.

## Amendment, 2026-06-29 (eager terminal flip)

The observed-flag model assumes an executor is alive to watch the flag. A dead or frozen Worker never reads it, so the Job stays `running`, the UI never resolves, and the user cannot resubmit while a Job shows active. Cancel did nothing for the case a user most wants it for.

So the cancel endpoint now also flips the Job to terminal (`done` with the cancelled halt reason) eagerly in the store, not only setting the flag. The flip is a Redis write from the API, so it lands whatever the Worker's state. The flag stays for the live case: a responsive executor still runs the graceful `docker kill --signal=TERM`, KLEE flushes, and its write enriches the Job with partial test cases. The flip is sticky: a late Worker write may add partials but cannot un-cancel, so a cancel always wins over a concurrent finish.

The flip resolves the UI at once and frees the user to resubmit, dead Worker or alive. It does not force-kill a frozen Worker's container. That is left to the bounded reapers (ADR-0018), which cap the runaway container and free a frozen Worker's slot on their own schedule. So cancel gains no `revoke` escalation, and the 2026-06-23 reasoning against `revoke` stands.

## References

- ADR-0008: KleeRunner protocol surface (the contract `cancel` extends).
- ADR-0009: per-job containers (deterministic naming relies on one container per job).
