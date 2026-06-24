import pytest
from pydantic import ValidationError

from klee_web.config import Settings


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
