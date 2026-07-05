#!/usr/bin/env python3
"""Compile /work/input.c with clang, run KLEE on it, write outputs to /work/output/.

Reads max_time and max_memory from KLEE_MAX_TIME and KLEE_MAX_MEMORY env vars.
On compile failure, writes clang stderr to /work/output/compile_error.txt and
exits 0: the runner did its job, the user's code is what didn't compile, and the
backend distinguishes this from a runner crash via the presence of that file.

KLEE's stdout carries the user program's own output (its printf/cout), so we
capture it and write it to /work/output/program_output.txt. KLEE's stderr (its
own diagnostics) is left to flow to the container so the backend still sees it.

When KLEE_QUERY_FORMAT=kquery, pass --write-kqueries so KLEE emits a .kquery
(path constraint) file per test case.

KLEE_EXTRA_FLAGS carries allowlisted power-user flags (validated by the backend,
ADR-0019). They are shlex-split and spliced into the prefix, before the bitcode.
--external-calls is pinned to concrete so a user cannot broaden the policy.

KLEE_POSIX_ARGS carries the symbolic-input options (--sym-stdin/--sym-files/
--sym-args) the backend renders from structured fields. These are POSIX-runtime
options, so they are shlex-split and appended AFTER the bitcode, not the prefix.

A SIGTERM to this process (how the backend cancels a job) is translated into a
SIGINT to KLEE, the signal KLEE halts gracefully on: KLEE stops exploring and
dumps the test cases found so far, the same partial result a --max-time expiry
produces.
"""

import contextlib
import os
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path

INPUT = Path("/work/input.c")
BITCODE = Path("/work/code.bc")
OUTPUT_DIR = Path("/work/output")
KLEE_INCLUDE = "/home/klee/klee_src/include"
GRACE_SECONDS = 10  # after forwarding the halt, SIGKILL KLEE if it has not flushed and exited
HOST_TIMEOUT_MARGIN = 15  # bound KLEE at max_time + this, for when it overruns its own --max-time


def build_klee_command(
    max_time: str, max_memory: str, query_format: str, extra_flags: str, posix_args: str
) -> list[str]:
    cmd = [
        "klee",
        "--libc=uclibc",
        "--posix-runtime",
        "--external-calls=concrete",
        f"--max-time={max_time}",
        f"--max-memory={max_memory}",
        f"--output-dir={OUTPUT_DIR}",
    ]
    if query_format == "kquery":
        cmd.append("--write-kqueries")
    cmd += shlex.split(extra_flags)
    cmd.append(str(BITCODE))
    cmd += shlex.split(posix_args)
    return cmd


def main() -> int:
    max_time = os.environ.get("KLEE_MAX_TIME", "60")
    max_memory = os.environ.get("KLEE_MAX_MEMORY", "512")
    query_format = os.environ.get("KLEE_QUERY_FORMAT", "none")
    extra_flags = os.environ.get("KLEE_EXTRA_FLAGS", "")
    posix_args = os.environ.get("KLEE_POSIX_ARGS", "")

    compile_proc = subprocess.run(
        [
            "clang",
            "-I",
            KLEE_INCLUDE,
            "-emit-llvm",
            "-c",
            "-g",
            "-O0",
            str(INPUT),
            "-o",
            str(BITCODE),
        ],
        capture_output=True,
        text=True,
    )
    if compile_proc.returncode != 0:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "compile_error.txt").write_text(compile_proc.stderr)
        return 0

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    klee_cmd = build_klee_command(max_time, max_memory, query_format, extra_flags, posix_args)

    # New session so KLEE and any solver it forks share a process group we can signal as
    # a unit. KLEE runs STP in a forked child that would otherwise survive a kill of KLEE
    # alone and keep grinding the query, holding the stdout pipe open and hanging us.
    proc = subprocess.Popen(klee_cmd, stdout=subprocess.PIPE, text=True, start_new_session=True)
    halted = False

    def _killpg(sig: int) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, sig)

    def _force_kill(signum, frame):
        _killpg(signal.SIGKILL)

    def _forward_halt(signum, frame):
        # Cancel: the backend's SIGTERM. Ask KLEE to halt on SIGINT (it dumps the test
        # cases found so far), and SIGKILL the group after the grace if it has not.
        nonlocal halted
        halted = True
        _killpg(signal.SIGINT)
        signal.signal(signal.SIGALRM, _force_kill)
        signal.alarm(GRACE_SECONDS)

    signal.signal(signal.SIGTERM, _forward_halt)
    signal.signal(signal.SIGINT, _forward_halt)

    timed_out = False
    try:
        stdout, _ = proc.communicate(timeout=int(max_time) + HOST_TIMEOUT_MARGIN)
    except subprocess.TimeoutExpired:
        # KLEE ignored its own --max-time, a hard query never yields to the timer. Ask
        # the group to halt, then SIGKILL it if it stays wedged. communicate's own
        # timeout drives the grace, reliable where an alarm during a blocking read is not.
        timed_out = True
        _killpg(signal.SIGINT)
        try:
            stdout, _ = proc.communicate(timeout=GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _killpg(signal.SIGKILL)
            stdout, _ = proc.communicate()
    signal.alarm(0)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "program_output.txt").write_text(stdout or "")
    if timed_out:
        # Tell the parser this was a time-limit stop, not a clean empty run.
        (OUTPUT_DIR / "host_timeout").touch()
    # A bound-kill is a time-limit halt, not a runner crash: exit 0 so the backend
    # parses the result instead of raising on a non-zero docker exit.
    return 0 if (halted or timed_out) else proc.returncode


if __name__ == "__main__":
    sys.exit(main())
