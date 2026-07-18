import asyncio
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

_READY_TIMEOUT_SECONDS = 2.0


class Readiness(Protocol):
    async def is_ready(self) -> bool: ...


class RedisReadiness:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def is_ready(self) -> bool:
        try:
            async with asyncio.timeout(_READY_TIMEOUT_SECONDS):
                await self._client.ping()
        except (RedisError, OSError, TimeoutError):
            return False
        return True
