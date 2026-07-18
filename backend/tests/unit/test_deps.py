from klee_web.deps import (
    get_cache,
    get_dispatcher,
    get_fleet_control,
    get_job_store,
    get_readiness,
    get_telemetry,
    get_usage_stats,
)
from klee_web.health import RedisReadiness
from klee_web.jobs.cache import RedisResultCache
from klee_web.jobs.dispatch import CeleryDispatcher
from klee_web.jobs.store import RedisJobStore
from klee_web.jobs.telemetry import CeleryFleetControl, CeleryFleetTelemetry
from klee_web.jobs.usage import RedisUsageStatsStore


def test_get_job_store_uses_redis():
    get_job_store.cache_clear()
    assert isinstance(get_job_store(), RedisJobStore)


def test_get_cache_uses_redis():
    get_cache.cache_clear()
    assert isinstance(get_cache(), RedisResultCache)


def test_get_dispatcher_uses_celery():
    assert isinstance(get_dispatcher(), CeleryDispatcher)


def test_get_readiness_uses_redis():
    get_readiness.cache_clear()
    assert isinstance(get_readiness(), RedisReadiness)


def test_get_telemetry_uses_celery():
    get_telemetry.cache_clear()
    assert isinstance(get_telemetry(), CeleryFleetTelemetry)


def test_get_fleet_control_uses_celery():
    get_fleet_control.cache_clear()
    assert isinstance(get_fleet_control(), CeleryFleetControl)


def test_get_usage_stats_uses_redis():
    get_usage_stats.cache_clear()
    assert isinstance(get_usage_stats(), RedisUsageStatsStore)
