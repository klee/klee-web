import asyncio
from uuid import uuid4

from klee_web.jobs.runner import reclaim_container


class _FakeProc:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return b"", b""


async def test_reclaim_force_removes_the_jobs_container_by_name(monkeypatch):
    calls: list[tuple[object, ...]] = []

    async def fake_exec(*args, **kwargs):
        calls.append(args)
        return _FakeProc(returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    job_id = uuid4()
    await reclaim_container(job_id)

    assert calls == [("docker", "rm", "-f", f"klee-job-{job_id}")]


async def test_reclaim_swallows_nonzero_exit(monkeypatch):
    async def fake_exec(*args, **kwargs):
        return _FakeProc(returncode=1)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    await reclaim_container(uuid4())  # no such container is the common case, must not raise


async def test_reclaim_swallows_missing_docker(monkeypatch):
    async def fake_exec(*args, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    await reclaim_container(uuid4())  # docker absent must not abort the job
