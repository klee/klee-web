import logging
import sqlite3
import struct
from pathlib import Path

from klee_web.models import HaltReason, JobResult, SymbolicInput, TestCase
from klee_web.parsing.ktest import KTest

logger = logging.getLogger(__name__)

# Cap on captured program output: ample to read in the panel, small to ship and store.
PROGRAM_OUTPUT_MAX_BYTES = 100_000


def clamp_program_output(raw: bytes, max_bytes: int = PROGRAM_OUTPUT_MAX_BYTES) -> str:
    # Program output is arbitrary program bytes, so decode leniently: a non-UTF-8 byte,
    # or a multibyte char split by the cap, becomes U+FFFD rather than crashing the parse.
    if len(raw) <= max_bytes:
        return raw.decode("utf-8", errors="replace")
    head = raw[:max_bytes].decode("utf-8", errors="replace")
    marker = f"\n\n[program output truncated: showing first {max_bytes:,} of {len(raw):,} bytes]"
    return head + marker


def parse_output_dir(output_dir: Path, *, include_test_cases: bool = True) -> JobResult:
    compile_error_path = output_dir / "compile_error.txt"
    if compile_error_path.exists():
        return JobResult(
            test_cases=[],
            messages="",
            warnings="",
            stats={},
            compile_error=compile_error_path.read_text(),
        )

    # Progress polls pass include_test_cases=False: KLEE writes a ktest per
    # terminated path (thousands during a single run), so opening them all on
    # every watcher tick is the work that blocks the event loop. The running UI
    # shows only stats, so partials skip the ktests; the final parse reads them.
    test_cases: list[TestCase] = []
    if include_test_cases:
        err_files_by_stem = _err_files_by_stem(output_dir)
        for p in sorted(output_dir.glob("*.ktest")):
            try:
                test_cases.append(_test_case_from_ktest(p, err_files_by_stem.get(p.stem, [])))
            except (OSError, ValueError, EOFError, struct.error) as exc:
                # Corrupt/truncated ktest; no later parse fixes it. Drop it, keep the run.
                logger.warning("skipping unreadable ktest %s: %r", p, exc)
                continue

    messages = _read_or_empty(output_dir / "messages.txt")
    info = _read_or_empty(output_dir / "info")
    host_timed_out = (output_dir / "host_timeout").exists()
    return JobResult(
        test_cases=test_cases,
        messages=messages,
        warnings=_read_or_empty(output_dir / "warnings.txt"),
        stats=_read_stats(output_dir / "run.stats"),
        program_output=_read_program_output(output_dir / "program_output.txt"),
        halt_reason=_detect_halt_reason(messages, info, host_timed_out),
    )


def _detect_halt_reason(messages: str, info: str, host_timed_out: bool) -> HaltReason | None:
    # KLEE writes the HaltTimer marker to messages.txt when its own --max-time fires.
    # The entrypoint drops a host_timeout sentinel when it force-stops a KLEE that
    # ignored that limit (wedged in a solver query); both mean a time-limit stop.
    # "KLEE: done:" in info marks a clean termination. Absence of all three means
    # KLEE is still running, so we report None rather than guessing.
    if host_timed_out or "HaltTimer invoked" in messages:
        return HaltReason.max_time
    if "KLEE: done:" in info:
        return HaltReason.completed
    return None


def _read_or_empty(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def _read_program_output(path: Path) -> str:
    return clamp_program_output(path.read_bytes()) if path.exists() else ""


def _read_stats(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    try:
        con = sqlite3.connect(path)
        try:
            # run.stats is a time series of snapshots written every --stats-write-interval.
            # KLEE counters are monotonic, so the last row is the cumulative totals.
            cur = con.execute("SELECT * FROM stats ORDER BY rowid DESC LIMIT 1;")
            cols = [str(d[0]) for d in cur.description]
            row = cur.fetchone()
        finally:
            con.close()
    except sqlite3.Error:
        # Mid-write or locked DB; next watcher tick will retry.
        return {}
    if row is None:
        return {}
    return {c: int(v) for c, v in zip(cols, row, strict=True) if v is not None}


_INT_SIZE_FORMATS = {1: "<b", 2: "<h", 4: "<i", 8: "<q"}


def _err_files_by_stem(output_dir: Path) -> dict[str, list[Path]]:
    # KLEE names error files <test_stem>.<errortype>.err. Glob once and group by
    # test stem so each ktest is a dict lookup, not a fresh directory scan. The
    # old per-ktest glob was O(n^2) and dominated the final parse on large runs.
    by_stem: dict[str, list[Path]] = {}
    for err in output_dir.glob("*.err"):
        by_stem.setdefault(err.name.split(".", 1)[0], []).append(err)
    for files in by_stem.values():
        files.sort()
    return by_stem


def _test_case_from_ktest(path: Path, err_files: list[Path]) -> TestCase:
    ktest = KTest.fromfile(str(path))
    inputs = [
        SymbolicInput(name=name, value=_decode_object_value(data), bytes_hex=data.hex())
        for name, data in ktest.objects
    ]
    error = "\n".join(p.read_text() for p in err_files) if err_files else None
    kquery_path = path.with_suffix(".kquery")
    path_constraint = kquery_path.read_text() if kquery_path.exists() else None
    return TestCase(name=path.stem, inputs=inputs, error=error, path_constraint=path_constraint)


def _decode_object_value(data: bytes) -> str:
    fmt = _INT_SIZE_FORMATS.get(len(data))
    if fmt is not None:
        return str(struct.unpack(fmt, data)[0])
    return data.hex()
