import asyncio
import io
import tarfile
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from klee_web.models import JobResult, KleeFlags
from klee_web.parsing.klee_output import parse_output_dir
from klee_web.symbolic_input import render_posix_args

IMAGE_TAG = "klee-web-runner"


@dataclass(frozen=True)
class RunnerCaps:
    cpus: float
    memory_mb: int
    swap_mb: int
    pids_limit: int


def _container_name(job_id: UUID) -> str:
    return f"klee-job-{job_id}"


def resolve_runtime(configured: str | None, kvm_present: bool | None = None) -> str | None:
    """Map the KLEE_RUNTIME config value to a docker --runtime, or None for the default runc.

    "auto" selects the gVisor platform: runsc-kvm where /dev/kvm exists, runsc otherwise.
    kvm_present is injected in tests; production probes /dev/kvm when it is None.
    """
    if configured in (None, "", "runc"):
        return None
    if configured == "auto":
        if kvm_present is None:
            kvm_present = Path("/dev/kvm").exists()
        return "runsc-kvm" if kvm_present else "runsc"
    return configured


def build_run_args(
    job_id: UUID,
    flags: KleeFlags,
    posix_args: str,
    runtime: str | None,
    caps: RunnerCaps,
) -> list[str]:
    args = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--name",
        _container_name(job_id),
        "--cpus",
        f"{caps.cpus:g}",
        "--memory",
        f"{caps.memory_mb}m",
        "--memory-swap",
        f"{caps.memory_mb + caps.swap_mb}m",
        "--pids-limit",
        str(caps.pids_limit),
    ]
    if runtime is not None:
        args += ["--runtime", runtime]
    args += [
        "-e",
        f"KLEE_MAX_TIME={flags.max_time}",
        "-e",
        f"KLEE_MAX_MEMORY={flags.max_memory}",
        "-e",
        f"KLEE_QUERY_FORMAT={flags.query_format.value}",
        "-e",
        f"KLEE_EXTRA_FLAGS={flags.extra_flags}",
        "-e",
        f"KLEE_POSIX_ARGS={posix_args}",
        IMAGE_TAG,
    ]
    return args


OnProgress = Callable[[JobResult], Awaitable[None]]
OnParsing = Callable[[], Awaitable[None]]


class KleeRunnerError(Exception):
    """Raised when the runner itself fails: docker missing, container crash, no output dir.

    User-code compile errors are NOT raised here; they flow through JobResult.compile_error.
    """


class KleeRunner(Protocol):
    async def execute(
        self,
        source: str,
        flags: KleeFlags,
        job_id: UUID,
        on_progress: OnProgress | None = None,
        on_parsing: OnParsing | None = None,
    ) -> JobResult: ...
    async def cancel(self, job_id: UUID) -> bool: ...


class FakeKleeRunner:
    """Test double. Returns a canned result, or raises a canned exception. Records calls."""

    def __init__(
        self,
        canned_result: JobResult | None = None,
        raise_exc: Exception | None = None,
        cancel_returns: bool = True,
    ) -> None:
        self._canned_result = canned_result
        self._raise_exc = raise_exc
        self._cancel_returns = cancel_returns
        self.calls: list[tuple[str, KleeFlags]] = []
        self.cancel_calls: list[UUID] = []

    async def execute(
        self,
        source: str,
        flags: KleeFlags,
        job_id: UUID,
        on_progress: OnProgress | None = None,
        on_parsing: OnParsing | None = None,
    ) -> JobResult:
        self.calls.append((source, flags))
        if self._raise_exc is not None:
            raise self._raise_exc
        if self._canned_result is None:
            raise RuntimeError("FakeKleeRunner needs either canned_result or raise_exc")
        if on_progress is not None:
            await on_progress(self._canned_result)
        if on_parsing is not None:
            await on_parsing()
        return self._canned_result

    async def cancel(self, job_id: UUID) -> bool:
        self.cancel_calls.append(job_id)
        return self._cancel_returns


class DockerKleeRunner:
    """Runs the klee-web-runner container per job and parses its output into a JobResult.

    Transport is stream-only: the source goes in on the container's stdin and the whole
    output directory comes back as a tar on its stdout. There is no bind mount, so the
    same image runs unchanged under any runtime without a shared filesystem (a microVM,
    a serverless sandbox), not only runc.
    """

    def __init__(self, caps: RunnerCaps, runtime: str | None = None) -> None:
        self._caps = caps
        self._runtime = runtime

    async def execute(
        self,
        source: str,
        flags: KleeFlags,
        job_id: UUID,
        on_progress: OnProgress | None = None,
        on_parsing: OnParsing | None = None,
    ) -> JobResult:
        # on_progress is unused here: streaming partials needs a shared output directory
        # to poll, which the stream transport deliberately removes. run_job still drives
        # the running/parsing/done states.
        posix_args = render_posix_args(flags.sym_files, flags.sym_args, flags.sym_stdin)
        try:
            proc = await asyncio.create_subprocess_exec(
                *build_run_args(job_id, flags, posix_args, self._runtime, self._caps),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise KleeRunnerError("docker CLI not found on PATH") from e

        stdout, stderr = await proc.communicate(input=source.encode())

        if proc.returncode != 0:
            raise KleeRunnerError(
                f"docker run exited with {proc.returncode}: "
                f"{stderr.decode(errors='replace').strip()}"
            )

        with tempfile.TemporaryDirectory(prefix="klee-job-") as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            try:
                with tarfile.open(fileobj=io.BytesIO(stdout), mode="r|") as tar:
                    tar.extractall(tmpdir, filter="data")
            except tarfile.TarError as e:
                raise KleeRunnerError("runner produced no readable output archive") from e
            output_dir = tmpdir / "output"
            if not output_dir.exists():
                raise KleeRunnerError("runner produced no output directory")
            if on_parsing is not None:
                await on_parsing()
            return await asyncio.to_thread(parse_output_dir, output_dir)

    async def cancel(self, job_id: UUID) -> bool:
        """Signal the job's container to halt. Returns True only if a live container
        received the signal; a missing container (not started yet, or already gone)
        means there is nothing to cancel."""
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "kill",
            "--signal=TERM",
            _container_name(job_id),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        return proc.returncode == 0
