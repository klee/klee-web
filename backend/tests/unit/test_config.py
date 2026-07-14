import pytest
from pydantic import ValidationError

from klee_web.config import Settings


def test_worker_concurrency_max_defaults_to_four():
    assert Settings().worker_concurrency_max == 4


def test_worker_concurrency_max_reads_environment(monkeypatch):
    monkeypatch.setenv("WORKER_CONCURRENCY_MAX", "8")
    assert Settings().worker_concurrency_max == 8


def test_worker_concurrency_max_must_be_positive():
    with pytest.raises(ValidationError):
        Settings(worker_concurrency_max=0)


def test_celery_broker_without_redis_is_rejected():
    with pytest.raises(ValidationError):
        Settings(celery_broker_url="redis://localhost:6379/1", redis_url=None)


def test_celery_broker_with_redis_is_allowed():
    settings = Settings(
        celery_broker_url="redis://localhost:6379/1",
        redis_url="redis://localhost:6379/0",
    )
    assert settings.celery_broker_url == "redis://localhost:6379/1"


def test_no_celery_broker_is_allowed():
    settings = Settings(celery_broker_url=None, redis_url=None)
    assert settings.celery_broker_url is None
