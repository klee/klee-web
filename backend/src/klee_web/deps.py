from functools import lru_cache

from klee_web.config import get_settings
from klee_web.jobs.runner import DockerKleeRunner, KleeRunner
from klee_web.jobs.store import InMemoryJobStore, JobStore


@lru_cache
def get_job_store() -> JobStore:
    settings = get_settings()
    if settings.redis_url:
        from redis.asyncio import Redis

        from klee_web.jobs.store import RedisJobStore

        return RedisJobStore(Redis.from_url(settings.redis_url))
    return InMemoryJobStore()


@lru_cache
def get_runner() -> KleeRunner:
    if get_settings().klee_fake_runner:
        from klee_web.jobs.fake_data import get_sign_result
        from klee_web.jobs.runner import FakeKleeRunner

        return FakeKleeRunner(canned_result=get_sign_result())
    return DockerKleeRunner()
