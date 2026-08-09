#!/usr/bin/env python3
"""Read C source from stdin, compile it with clang, run KLEE, and stream the
output directory back as a tar on stdout.

There is no shared filesystem with the host. The source arrives on stdin and the
whole /work/output tree leaves as a tar on stdout, so the same image runs
unchanged under any runtime without a bind mount (a microVM, a serverless
sandbox), not only runc.

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
import glob
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path

INPUT = Path("/work/input.c")
BITCODE = Path("/work/code.bc")
OUTPUT_DIR = Path("/work/output")
KLEE_INCLUDE = "/home/klee/klee_src/include"
GRACE_SECONDS = 10  # after forwarding the halt, SIGKILL KLEE if it has not flushed and exited
HOST_TIMEOUT_MARGIN = 15  # bound KLEE at max_time + this, for when it overruns its own --max-time
REPLAY_PER_TEST_TIMEOUT = 10  # KLEE_REPLAY_TIMEOUT: read by replay_driver.c, kills one hanging replay
REPLAY_MIN_LEFTOVER = 1  # skip replay entirely below this many seconds of budget left
REPLAY_NOSLEEP_SO = "/usr/local/lib/replay_nosleep.so"  # LD_PRELOAD: no-op sleeps in replay
ZYGOTE_OBJ_DIR = "/usr/local/lib/klee-replay-zygote"  # prebuilt by the Dockerfile


def build_klee_command(
    max_time: str, max_memory: str, query_format: str, extra_flags: str, posix_args: str
) -> list[str]:
    cmd = [
        "klee",
        "--libc=uclibc",
        "--posix-runtime",
        "--external-calls=concrete",
        # KDAlloc aborts under gVisor and under THP-less guest kernels (ADR-0022).
        "--kdalloc=false",
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


def resolve_klee_lib_dir() -> Path | None:
    # libkleeBasic (the ktest reader the replay driver links) lives under a build dir
    # whose name is not guaranteed stable across image rebuilds, so glob for it rather
    # than hardcoding the path.
    for pattern in (
        "/tmp/klee_build*/lib/libkleeBasic.a",
        "/home/klee/klee_build/lib/libkleeBasic.a",
    ):
        matches = glob.glob(pattern)
        if matches:
            return Path(matches[0]).parent
    return None


def start_replay_phase(leftover: int) -> subprocess.Popen | None:
    # Best-effort: any failure here leaves per-path output absent but never fails the job.
    lib = resolve_klee_lib_dir()
    if lib is None:
        return None
    replay_bin = Path("/work/replay.out")
    # One compile-and-link: -Dmain renames main only in the user source being compiled,
    # never in the prebuilt objects. Objects come before -l libraries so the linker can
    # resolve their references. -lm restores replay for user programs calling libm.
    compiled = subprocess.run(
        ["clang", "-Dmain=__user_main", str(INPUT),
         f"{ZYGOTE_OBJ_DIR}/replay_driver.o",
         f"{ZYGOTE_OBJ_DIR}/file-creator.o",
         f"{ZYGOTE_OBJ_DIR}/klee_init_env.o",
         f"{ZYGOTE_OBJ_DIR}/fd_init.o",
         "-I", KLEE_INCLUDE, "-L", str(lib),
         "-lkleeBasic", "-lstdc++", "-lutil", "-lm",
         "-o", str(replay_bin)],
        capture_output=True,
    )
    if compiled.returncode != 0:
        return None
    env = {
        **os.environ,
        "LD_PRELOAD": REPLAY_NOSLEEP_SO,
        "KLEE_REPLAY_TIMEOUT": str(REPLAY_PER_TEST_TIMEOUT),
    }
    # New session so a cancel can kill the whole replay group (the driver amplifies a
    # lone TERM into a group-wide kill); timeout bounds the phase to the leftover budget,
    # then SIGKILLs 2s later if needed. The driver takes the output directory and
    # enumerates the ktests itself, so a path explosion never hits the argv size limit.
    return subprocess.Popen(
        ["timeout", "-k", "2", str(leftover), str(replay_bin), str(OUTPUT_DIR)],
        env=env,
        start_new_session=True,
        stdout=sys.stderr,
    )


def run_klee() -> int:
    start = time.monotonic()
    max_time = os.environ.get("KLEE_MAX_TIME", "60")
    max_memory = os.environ.get("KLEE_MAX_MEMORY", "512")
    query_format = os.environ.get("KLEE_QUERY_FORMAT", "none")
    extra_flags = os.environ.get("KLEE_EXTRA_FLAGS", "")
    posix_args = os.environ.get("KLEE_POSIX_ARGS", "")
    enable_replay = os.environ.get("KLEE_ENABLE_REPLAY", "1") == "1"

    compile_proc = subprocess.run(
        [
            "clang",
            "-I",
            KLEE_INCLUDE,
            "-emit-llvm",
            "-c",
            "-g",
            "-O0",
            "-Xclang",
            "-disable-O0-optnone",
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
    replay_proc: subprocess.Popen | None = None

    def _killpg(sig: int) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, sig)

    def _kill_replay(sig: int) -> None:
        if replay_proc is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(replay_proc.pid, sig)

    def _force_kill(signum, frame):
        _killpg(signal.SIGKILL)
        _kill_replay(signal.SIGKILL)

    def _forward_halt(signum, frame):
        # Cancel: the backend's SIGTERM. Ask KLEE to halt on SIGINT (it dumps the test
        # cases found so far). If a replay phase is running, SIGTERM its group so cancel is
        # immediate and the .stdout files already finished are kept. SIGKILL both after grace.
        nonlocal halted
        halted = True
        _killpg(signal.SIGINT)
        _kill_replay(signal.SIGTERM)
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

    # Optional per-path replay: when enabled, re-run each ktest natively in the leftover
    # budget to capture what that path printed. Skipped when disabled, on cancel (halted),
    # and when the run used its whole budget (leftover below the floor), which is the
    # path-explosion case where per-path output is noise anyway. A cancel arriving
    # mid-replay kills the group via _forward_halt.
    if enable_replay and not halted:
        leftover = int(max_time) - int(time.monotonic() - start)
        if leftover >= REPLAY_MIN_LEFTOVER:
            replay_proc = start_replay_phase(leftover)
            if replay_proc is not None:
                with contextlib.suppress(Exception):
                    replay_proc.wait()
            signal.alarm(0)  # clear any grace alarm a mid-replay cancel armed

    # A bound-kill is a time-limit halt, not a runner crash: exit 0 so the backend
    # parses the result instead of raising on a non-zero docker exit.
    return 0 if (halted or timed_out) else proc.returncode


def main() -> int:
    INPUT.parent.mkdir(parents=True, exist_ok=True)
    INPUT.write_bytes(sys.stdin.buffer.read())
    code = run_klee()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as tar:
        tar.add(OUTPUT_DIR, arcname="output")
    sys.stdout.buffer.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
