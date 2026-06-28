import asyncio
import tempfile
from collections.abc import Awaitable, Callable
from contextlib import suppress
from pathlib import Path
from typing import Protocol
from uuid import UUID

from klee_web.models import JobResult, KleeFlags
from klee_web.parsing.klee_output import parse_output_dir

IMAGE_TAG = "klee-web-runner"
_WATCH_INTERVAL_SECONDS = 1.0


def _container_name(job_id: UUID) -> str:
    return f"klee-job-{job_id}"


async def reclaim_container(job_id: UUID) -> None:
    """Force-remove any container orphaned under this job's deterministic name.

    A dead worker leaves its container under klee-job-{id} (it runs under dockerd, not
    as the worker's child), which would collide with a redelivered run's --name. Run
    before every docker run, best-effort: a missing container (the common case, a
    non-zero exit) and a missing docker binary (OSError) are both swallowed, because
    reclaim must never abort the job it exists to save. Safe only because the visibility
    timeout means redelivery happens after the original worker is dead (ADR-0018)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "rm",
            "-f",
            _container_name(job_id),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
    except OSError:
        pass


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
    """Runs the klee-web-runner container per job and parses /work/output back into a JobResult."""

    async def execute(
        self,
        source: str,
        flags: KleeFlags,
        job_id: UUID,
        on_progress: OnProgress | None = None,
        on_parsing: OnParsing | None = None,
    ) -> JobResult:
        with tempfile.TemporaryDirectory(prefix="klee-job-") as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            (tmpdir / "input.c").write_text(source)
            output_dir = tmpdir / "output"

            await reclaim_container(job_id)

            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    _container_name(job_id),
                    "-v",
                    f"{tmpdir}:/work",
                    "-e",
                    f"KLEE_MAX_TIME={flags.max_time}",
                    "-e",
                    f"KLEE_MAX_MEMORY={flags.max_memory}",
                    "-e",
                    f"KLEE_QUERY_FORMAT={flags.query_format.value}",
                    IMAGE_TAG,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError as e:
                raise KleeRunnerError("docker CLI not found on PATH") from e

            watcher: asyncio.Task[None] | None = None
            if on_progress is not None:
                watcher = asyncio.create_task(_watch_output_dir(output_dir, on_progress))

            try:
                _, stderr = await proc.communicate()
            finally:
                if watcher is not None:
                    watcher.cancel()
                    with suppress(asyncio.CancelledError):
                        await watcher

            if proc.returncode != 0:
                raise KleeRunnerError(
                    f"docker run exited with {proc.returncode}: "
                    f"{stderr.decode(errors='replace').strip()}"
                )

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


async def _watch_output_dir(output_dir: Path, on_progress: OnProgress) -> None:
    """Poll the output directory and emit partial results as KLEE writes files.

    Cancellation is the normal exit path: the caller cancels this task once docker
    exits, then awaits the cancellation to guarantee no further on_progress call
    races with the final set_result.
    """
    while True:
        await asyncio.sleep(_WATCH_INTERVAL_SECONDS)
        if not output_dir.exists():
            continue
        partial = await asyncio.to_thread(parse_output_dir, output_dir, include_test_cases=False)
        await on_progress(partial)
