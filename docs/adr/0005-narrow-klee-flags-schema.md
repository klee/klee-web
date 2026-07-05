# 0005. Narrow KleeFlags schema for Stage 1

**Status:** Accepted, 2026-05-19

## Context

KLEE accepts dozens of command-line flags. Exposing them through the API has two failure modes:

1. A free-form flag string would be concatenated into the KLEE invocation, creating a command-injection vector.
2. The full flag taxonomy is overwhelming for the target audience (students, KLEE newcomers), most of whom only need bounded execution.

The API needs a flag surface that is safe by construction and small enough to be obvious.

## Decision

Ship a narrow Pydantic schema (`KleeFlags`) with two typed fields:

- `max_time`: integer seconds, range 1 to 300, default 60.
- `max_memory`: integer megabytes, range 64 to 2048, default 512.

The defaults are chosen as a reasonable baseline for short interactive runs. Bounds act as safety clamps. Pydantic enforces both before any handler logic runs.

## Consequences

**Positive**

- Beginner-safe surface: users do not need to learn KLEE's flag taxonomy to submit a useful job.
- Removes the command-injection vector: no free-form string ever reaches the KLEE invocation.
- Validation lives in Pydantic, surfaces as HTTP 422 before the handler executes.
- Two fields are enough for the bounded-execution use case Stage 1 targets.

**Negative**

- Power users cannot pass custom flags. Expansion is tracked as a future GitHub issue, to land once Stage 1 stabilises or a concrete request appears.

## References

- ADR-0001: stage-based additive architecture (the staging context that makes "ship narrow now, widen later" a deliberate choice).
- ADR-0012: extends this schema with `query_format` (the first concrete-request expansion).
- ADR-0019: broadens the schema with an allowlisted free-text field, and revises the no-free-text property above.
