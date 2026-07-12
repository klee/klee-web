from klee_web.config import Settings
from klee_web.deps import get_cache, get_dispatcher
from klee_web.jobs.cache import InMemoryResultCache, RedisResultCache
from klee_web.jobs.dispatch import CeleryDispatcher, InProcessDispatcher


def test_get_dispatcher_defaults_to_in_process(monkeypatch, store, runner, cache, usage):
    monkeypatch.setattr(
        "klee_web.deps.get_settings",
        lambda: Settings(redis_url=None, celery_broker_url=None),
    )
    assert isinstance(get_dispatcher(store, runner, cache, usage), InProcessDispatcher)


def test_get_dispatcher_selects_celery_when_broker_set(monkeypatch, store, runner, cache, usage):
    monkeypatch.setattr(
        "klee_web.deps.get_settings",
        lambda: Settings(
            redis_url="redis://localhost:6379/0",
            celery_broker_url="redis://localhost:6379/1",
        ),
    )
    assert isinstance(get_dispatcher(store, runner, cache, usage), CeleryDispatcher)


def test_get_cache_defaults_to_in_memory(monkeypatch):
    monkeypatch.setattr("klee_web.deps.get_settings", lambda: Settings(redis_url=None))
    get_cache.cache_clear()
    assert isinstance(get_cache(), InMemoryResultCache)


def test_get_cache_selects_redis_when_redis_url_set(monkeypatch):
    monkeypatch.setattr(
        "klee_web.deps.get_settings",
        lambda: Settings(redis_url="redis://localhost:6379/0"),
    )
    get_cache.cache_clear()
    assert isinstance(get_cache(), RedisResultCache)
