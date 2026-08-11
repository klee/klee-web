from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from redis.asyncio import Redis

from klee_web.models import Job, JobResult, JobStatus


class JobNotFound(Exception):
    """Raised when an operation references a UUID that is not in the store."""


class JobStore(Protocol):
    async def create(self, job: Job) -> None: ...
    async def get(self, job_id: UUID) -> Job | None: ...
    async def update_status(self, job_id: UUID, status: JobStatus) -> None: ...
    async def set_partial_result(self, job_id: UUID, result: JobResult) -> None: ...
    async def set_result(self, job_id: UUID, result: JobResult) -> None: ...
    async def request_cancel(self, job_id: UUID) -> None: ...


_JOB_TTL_SECONDS = 48 * 60 * 60


def _key(job_id: UUID) -> str:
    return f"job:{job_id}"


def _to_hash(job: Job) -> dict[str, str]:
    return {
        "id": str(job.id),
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at is not None else "",
        "result": job.result.model_dump_json() if job.result is not None else "",
        "cancel_requested": "1" if job.cancel_requested else "0",
    }


def _from_hash(data: dict[bytes, bytes]) -> Job:
    result = data[b"result"]
    started_at = data[b"started_at"]
    return Job(
        id=UUID(data[b"id"].decode()),
        status=JobStatus(data[b"status"].decode()),
        created_at=datetime.fromisoformat(data[b"created_at"].decode()),
        started_at=datetime.fromisoformat(started_at.decode()) if started_at else None,
        result=JobResult.model_validate_json(result) if result else None,
        cancel_requested=data[b"cancel_requested"] == b"1",
    )


class RedisJobStore:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def create(self, job: Job) -> None:
        key = _key(job.id)
        # redis-py stub types the mapping key as an invariant union; str fields are valid.
        await self._client.hset(key, mapping=_to_hash(job))  # type: ignore[arg-type]
        await self._client.expire(key, _JOB_TTL_SECONDS)

    async def get(self, job_id: UUID) -> Job | None:
        data = cast(dict[bytes, bytes], await self._client.hgetall(_key(job_id)))
        return _from_hash(data) if data else None

    async def update_status(self, job_id: UUID, status: JobStatus) -> None:
        fields = {"status": status.value}
        if status == JobStatus.running:
            fields["started_at"] = datetime.now(UTC).isoformat()
        await self._write_fields(job_id, fields)

    async def set_partial_result(self, job_id: UUID, result: JobResult) -> None:
        await self._write_fields(job_id, {"result": result.model_dump_json()})

    async def set_result(self, job_id: UUID, result: JobResult) -> None:
        await self._write_fields(
            job_id,
            {"status": JobStatus.done.value, "result": result.model_dump_json()},
        )

    async def request_cancel(self, job_id: UUID) -> None:
        await self._write_fields(job_id, {"cancel_requested": "1"})

    async def _write_fields(self, job_id: UUID, fields: dict[str, str]) -> None:
        key = _key(job_id)
        if not await self._client.exists(key):
            raise JobNotFound(job_id)
        await self._client.hset(key, mapping=fields)  # type: ignore[arg-type]
        await self._client.expire(key, _JOB_TTL_SECONDS)
