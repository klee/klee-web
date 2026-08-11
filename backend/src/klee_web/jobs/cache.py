import hashlib
import json
from typing import Protocol

from redis.asyncio import Redis

from klee_web.models import JobRequest, JobResult


def _job_result_schema_hash() -> str:
    canonical_schema = json.dumps(
        JobResult.model_json_schema(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_schema.encode()).hexdigest()


_JOB_RESULT_SCHEMA_HASH = _job_result_schema_hash()


def cache_key(request: JobRequest, runner_image: str) -> str:
    payload = json.dumps(
        {
            "request": request.model_dump(mode="json"),
            "runner_image": runner_image,
            "result_schema_hash": _JOB_RESULT_SCHEMA_HASH,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class ResultCache(Protocol):
    async def get(self, key: str) -> JobResult | None: ...
    async def set(self, key: str, result: JobResult) -> None: ...


_CACHE_TTL_SECONDS = 48 * 60 * 60


def _key(key: str) -> str:
    return f"cache:{key}"


class RedisResultCache:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> JobResult | None:
        data = await self._client.get(_key(key))
        return JobResult.model_validate_json(data) if data else None

    async def set(self, key: str, result: JobResult) -> None:
        await self._client.set(_key(key), result.model_dump_json(), ex=_CACHE_TTL_SECONDS)
