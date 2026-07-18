from functools import lru_cache

from redis.asyncio import Redis

from klee_web.config import get_settings
from klee_web.health import Readiness, RedisReadiness
from klee_web.jobs.cache import RedisResultCache, ResultCache
from klee_web.jobs.dispatch import CeleryDispatcher, JobDispatcher
from klee_web.jobs.store import JobStore, RedisJobStore
from klee_web.jobs.telemetry import FleetControl, FleetTelemetry
from klee_web.jobs.usage import RedisUsageStatsStore, UsageStatsStore


@lru_cache
def get_job_store() -> JobStore:
    settings = get_settings()
    return RedisJobStore(Redis.from_url(settings.redis_url))


@lru_cache
def get_readiness() -> Readiness:
    settings = get_settings()
    return RedisReadiness(Redis.from_url(settings.redis_url))


@lru_cache
def get_cache() -> ResultCache:
    settings = get_settings()
    return RedisResultCache(Redis.from_url(settings.redis_url))


@lru_cache
def get_telemetry() -> FleetTelemetry:
    settings = get_settings()
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


@lru_cache
def get_fleet_control() -> FleetControl:
    settings = get_settings()
    from klee_web.celery_app import app
    from klee_web.jobs.telemetry import CeleryFleetControl

    return CeleryFleetControl(app, settings.worker_concurrency_max)


@lru_cache
def get_usage_stats() -> UsageStatsStore:
    settings = get_settings()
    return RedisUsageStatsStore(Redis.from_url(settings.redis_url))


def get_dispatcher() -> JobDispatcher:
    return CeleryDispatcher()
