import asyncio
from typing import Protocol

from redis.asyncio import Redis

from klee_web.models import JobOutcome, UsageStats

_PREFIX = "usage:"
_CACHE_HITS_KEY = f"{_PREFIX}cache_hits"
_TEST_CASES_KEY = f"{_PREFIX}test_cases_generated"
_INSTRUCTIONS_KEY = f"{_PREFIX}instructions_executed"


def _outcome_key(outcome: JobOutcome) -> str:
    return f"{_PREFIX}outcome:{outcome.value}"


class UsageStatsStore(Protocol):
    async def record_execution(
        self, outcome: JobOutcome, test_cases: int = 0, instructions: int = 0
    ) -> None: ...
    async def record_cache_hit(self) -> None: ...
    async def snapshot(self) -> UsageStats: ...


class InMemoryUsageStatsStore:
    def __init__(self) -> None:
        self._outcomes: dict[JobOutcome, int] = {o: 0 for o in JobOutcome}
        self._cache_hits = 0
        self._test_cases = 0
        self._instructions = 0
        self._lock = asyncio.Lock()

    async def record_execution(
        self, outcome: JobOutcome, test_cases: int = 0, instructions: int = 0
    ) -> None:
        async with self._lock:
            self._outcomes[outcome] += 1
            self._test_cases += test_cases
            self._instructions += instructions

    async def record_cache_hit(self) -> None:
        async with self._lock:
            self._cache_hits += 1

    async def snapshot(self) -> UsageStats:
        async with self._lock:
            return UsageStats(
                outcomes=dict(self._outcomes),
                cache_hits=self._cache_hits,
                test_cases_generated=self._test_cases,
                instructions_executed=self._instructions,
            )


class RedisUsageStatsStore:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def record_execution(
        self, outcome: JobOutcome, test_cases: int = 0, instructions: int = 0
    ) -> None:
        # Stats are approximate, so separate INCRs (not a transaction) are fine.
        await self._client.incr(_outcome_key(outcome))
        if test_cases:
            await self._client.incrby(_TEST_CASES_KEY, test_cases)
        if instructions:
            await self._client.incrby(_INSTRUCTIONS_KEY, instructions)

    async def record_cache_hit(self) -> None:
        await self._client.incr(_CACHE_HITS_KEY)

    async def snapshot(self) -> UsageStats:
        keys = [_outcome_key(o) for o in JobOutcome] + [
            _CACHE_HITS_KEY,
            _TEST_CASES_KEY,
            _INSTRUCTIONS_KEY,
        ]
        raw = dict(zip(keys, await self._client.mget(keys), strict=True))

        def count(key: str) -> int:
            value = raw[key]
            return int(value) if value is not None else 0

        return UsageStats(
            outcomes={o: count(_outcome_key(o)) for o in JobOutcome},
            cache_hits=count(_CACHE_HITS_KEY),
            test_cases_generated=count(_TEST_CASES_KEY),
            instructions_executed=count(_INSTRUCTIONS_KEY),
        )
