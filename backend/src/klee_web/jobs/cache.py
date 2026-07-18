import hashlib
import json
from typing import Protocol

from redis.asyncio import Redis

from klee_web.models import JobRequest, JobResult


def cache_key(request: JobRequest) -> str:
    payload = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class ResultCache(Protocol):
    async def get(self, key: str) -> JobResult | None: ...
    async def set(self, key: str, result: JobResult) -> None: ...


_CACHE_TTL_SECONDS = 24 * 60 * 60


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
