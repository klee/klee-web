# 0020. Native per-path replay for program output

**Status:** Accepted, 2026-07-06

## Context

Per-path output (what each test case's path actually printed) has one source: run the compiled program on that path's concrete input and capture its stdout. KLEE interprets bitcode and does not hand back per-path stdout, so producing it means a second execution mode in the runner: compile the user's C to a native binary and run it, once per ktest.

## Decision

After KLEE finishes, replay each ktest natively: compile the source against `libkleeRuntest` and run it under `klee-replay` with `KTEST_FILE` set (klee-replay does not set it, but `klee_make_symbolic` needs it), capturing that path's stdout. (Mechanism superseded 2026-07-10: ADR-0022's fork-per-ktest zygote driver replaced `klee-replay` and `libkleeRuntest`. The decision here, native per-path replay in the leftover budget, stands.)

- **Shared budget, not a separate one.** Replay runs in KLEE's leftover time (`max_time - elapsed`), bounded by a per-test timeout. No extra or mirrored replay budget, so worst-case wall time does not double and the user sees one clock. A cancel skips replay, and replay is skipped when the leftover is below a floor (the path-explosion case, where per-path output is noise anyway). This raises the selectable `max_time` ceiling from 300 to 600, since one budget now covers both phases.
- **Sleeps neutralised** by an `LD_PRELOAD` no-op stub. KLEE models sleep away during symbolic execution, so replay must too, or a per-iteration sleep spends the whole budget for no output gain.
- **Best-effort.** Each path's stdout is written atomically, so a replay killed by the cutoff never promotes a truncated file and completed paths survive. Any replay failure leaves per-path output absent, it never fails the job.

## Consequences

- This extends native execution, it does not introduce it. ADR-0019 already assumed the container runs attacker-influenced native code, since `--external-calls=concrete` reaches real libc. Replay widens that from the program's external calls to the whole program, run N times. Same containment: the sandbox stays mandatory and public exposure still waits on Stage 3.
- A large run gets only partial per-path output, bounded by the leftover budget and the per-test timeout. Accepted, since per-path output across thousands of paths is not useful anyway.
- The sleep stub is a deliberate divergence from a plain native run. Justified because it matches what KLEE itself modelled, and per-path output is about what a path printed, not timing.
- The phase lives entirely in the runner entrypoint, so Stage 2 lifts it onto workers and Stage 3 runs it under gVisor as a runtime flag, though the replay mechanism itself is optimized for the sandbox in ADR-0022. `program_output` is an optional field on `TestCase`, an additive schema change like ADR-0012 and ADR-0019.

## References

- ADR-0019: allowlisted free-text KLEE flags (native execution already assumed, this extends it).
- ADR-0009: per-job containers (the sandbox this leans on).
- ADR-0013: cancel as a user-triggered halt (replay is skipped on cancel).
