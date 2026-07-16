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


def test_runner_caps_have_safe_defaults():
    settings = Settings()

    assert settings.runner_cpus == 2
    assert settings.runner_memory_mb == 3072
    assert settings.runner_swap_mb == 0
    assert settings.runner_pids_limit == 128
    assert settings.runner_storage_mb == 768


def test_runner_caps_read_environment(monkeypatch):
    monkeypatch.setenv("RUNNER_CPUS", "1.5")
    monkeypatch.setenv("RUNNER_MEMORY_MB", "4096")
    monkeypatch.setenv("RUNNER_SWAP_MB", "512")
    monkeypatch.setenv("RUNNER_PIDS_LIMIT", "64")
    monkeypatch.setenv("RUNNER_STORAGE_MB", "1024")

    settings = Settings()

    assert settings.runner_cpus == 1.5
    assert settings.runner_memory_mb == 4096
    assert settings.runner_swap_mb == 512
    assert settings.runner_pids_limit == 64
    assert settings.runner_storage_mb == 1024


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runner_cpus", 0),
        ("runner_memory_mb", 0),
        ("runner_swap_mb", -1),
        ("runner_pids_limit", 0),
        ("runner_storage_mb", 0),
    ],
)
def test_runner_caps_reject_invalid_values(field, value):
    with pytest.raises(ValidationError):
        Settings(**{field: value})


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
