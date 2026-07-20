# KLEE output sample fixtures

Captured runner output directories consumed by the parser tests in `tests/unit/test_klee_output.py`. Each subdirectory pairs the `input.c` that was run with the `output/` directory the runner produced.

## Scenarios

- `happy_path/`: canonical KLEE tutorial program (`get_sign`), three paths, three test cases, no errors.
- `compile_error/`: same program with `#include <klee/klee.h>` removed. Entrypoint writes `compile_error.txt` and exits 0; `output/` contains only that file.
- `runtime_error/`: divide-by-zero with `x` symbolic. KLEE emits `test000001.div.err` alongside the `.ktest` files.
- `max_time/`: bubble sort on 14 symbolic ints, run with `--max-time=3`. KLEE writes `HaltTimer invoked` to `messages.txt` and dumps remaining states. Trimmed to three `.ktest` files; the full run produced 251.
- `program_output/`: symbolic branch with `printf` calls. Captures the whole-run stdout in `program_output.txt`.
- `kquery/`: nested symbolic branches run with KQuery output enabled. Each test case has a matching path-constraint file.

## Files in each `output/`

- `messages.txt`, `warnings.txt`: KLEE text logs.
- `info`: invocation, PID, timing, exploration summary.
- `run.stats`: SQLite3 with KLEE's statistics. Final row is totals.
- `program_output.txt`: stdout captured from the symbolic KLEE run.
- `host_timeout`: optional empty marker written when the host-enforced bound stops KLEE.
- `test*.ktest`: binary test case files decoded by the vendored Python `KTest` reader. `ktest-tool` inside the Runner image remains useful for manual inspection.
- `test*.*.err`: error report. Extension encodes error type (e.g. `.div.err`, `.ptr.err`).
- `test*.kquery`: optional path constraint for the matching test case when KQuery output is enabled.
- `test*.stdout`: optional stdout captured by native replay for the matching test case.
- `compile_error.txt`: clang stderr. Present only when compilation failed.

## Excluded from the captured output

- `assembly.ll`: LLVM IR dump in text. KLEE-internal debugging artefact.
- `run.istats`: per-instruction profiling data for kcachegrind / `klee-stats`.

Both are large and KLEE Web never surfaces them. The parser ignores files it does not recognise.
