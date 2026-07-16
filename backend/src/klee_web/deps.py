from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from klee_web.config import get_settings
from klee_web.health import AlwaysReady, Readiness
from klee_web.jobs.cache import InMemoryResultCache, ResultCache
from klee_web.jobs.dispatch import InProcessDispatcher, JobDispatcher
from klee_web.jobs.runner import DockerKleeRunner, KleeRunner, RunnerCaps, resolve_runtime
from klee_web.jobs.store import InMemoryJobStore, JobStore
from klee_web.jobs.telemetry import FleetControl, FleetTelemetry
from klee_web.jobs.usage import InMemoryUsageStatsStore, UsageStatsStore


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
    settings = get_settings()
    if settings.klee_fake_runner:
        from klee_web.jobs.fake_data import get_sign_result
        from klee_web.jobs.runner import FakeKleeRunner

        return FakeKleeRunner(canned_result=get_sign_result())
    return DockerKleeRunner(
        caps=RunnerCaps(
            cpus=settings.runner_cpus,
            memory_mb=settings.runner_memory_mb,
            swap_mb=settings.runner_swap_mb,
            pids_limit=settings.runner_pids_limit,
            storage_mb=settings.runner_storage_mb,
        ),
        runtime=resolve_runtime(settings.klee_runtime),
    )


@lru_cache
def get_readiness() -> Readiness:
    settings = get_settings()
    if settings.redis_url:
        from redis.asyncio import Redis

        from klee_web.health import RedisReadiness

        return RedisReadiness(Redis.from_url(settings.redis_url))
    return AlwaysReady()


@lru_cache
def get_cache() -> ResultCache:
    settings = get_settings()
    if settings.redis_url:
        from redis.asyncio import Redis

        from klee_web.jobs.cache import RedisResultCache

        return RedisResultCache(Redis.from_url(settings.redis_url))
    return InMemoryResultCache()


@lru_cache
def get_telemetry() -> FleetTelemetry:
    settings = get_settings()
    if settings.celery_broker_url:
        from redis.asyncio import Redis

        from klee_web.celery_app import TASK_QUEUE, app
        from klee_web.jobs.telemetry import CeleryFleetTelemetry

        # Queue depth is read from the broker, where the queue list lives, not the store Redis.
        broker_redis = Redis.from_url(settings.celery_broker_url)
        return CeleryFleetTelemetry(
            app,
            broker_redis,
            TASK_QUEUE,
            settings.worker_concurrency_max,
        )
    from klee_web.jobs.telemetry import NullFleetTelemetry

    return NullFleetTelemetry(settings.worker_concurrency_max)


@lru_cache
def get_fleet_control() -> FleetControl:
    settings = get_settings()
    if settings.celery_broker_url:
        from klee_web.celery_app import app
        from klee_web.jobs.telemetry import CeleryFleetControl

        return CeleryFleetControl(app, settings.worker_concurrency_max)
    from klee_web.jobs.telemetry import UnavailableFleetControl

    return UnavailableFleetControl()


@lru_cache
def get_usage_stats() -> UsageStatsStore:
    settings = get_settings()
    if settings.redis_url:
        from redis.asyncio import Redis

        from klee_web.jobs.usage import RedisUsageStatsStore

        return RedisUsageStatsStore(Redis.from_url(settings.redis_url))
    return InMemoryUsageStatsStore()


def get_dispatcher(
    store: Annotated[JobStore, Depends(get_job_store)],
    runner: Annotated[KleeRunner, Depends(get_runner)],
    cache: Annotated[ResultCache, Depends(get_cache)],
    usage: Annotated[UsageStatsStore, Depends(get_usage_stats)],
) -> JobDispatcher:
    if get_settings().celery_broker_url:
        from klee_web.jobs.dispatch import CeleryDispatcher

        return CeleryDispatcher()
    return InProcessDispatcher(store, runner, cache, usage)
