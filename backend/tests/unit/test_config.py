from typing import Any

import pytest
from pydantic import ValidationError

from klee_web.config import Settings

REDIS_URL = "redis://localhost:6379/0"
BROKER_URL = "redis://localhost:6379/1"
RUNNER_IMAGE = "ghcr.io/finnleh/klee-web-runner@sha256:" + "a" * 64
LOCAL_RUNNER_IMAGE = "sha256:" + "b" * 64


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "redis_url": REDIS_URL,
        "celery_broker_url": BROKER_URL,
    }
    values.update(overrides)
    return Settings(**values)


def test_worker_concurrency_max_defaults_to_four():
    assert make_settings().worker_concurrency_max == 4


def test_worker_concurrency_max_reads_environment(monkeypatch):
    monkeypatch.setenv("WORKER_CONCURRENCY_MAX", "8")
    assert make_settings().worker_concurrency_max == 8


def test_worker_concurrency_max_must_be_positive():
    with pytest.raises(ValidationError):
        make_settings(worker_concurrency_max=0)


def test_runner_caps_have_safe_defaults():
    settings = make_settings()

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

    settings = make_settings()

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
        make_settings(**{field: value})


def test_runner_image_accepts_local_image_id():
    assert make_settings(runner_image=LOCAL_RUNNER_IMAGE).runner_image == LOCAL_RUNNER_IMAGE


def test_runner_image_reads_environment(monkeypatch):
    monkeypatch.setenv("RUNNER_IMAGE", RUNNER_IMAGE)

    assert make_settings().runner_image == RUNNER_IMAGE


def test_runner_image_is_required(monkeypatch):
    monkeypatch.delenv("RUNNER_IMAGE")
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            redis_url=REDIS_URL,
            celery_broker_url=BROKER_URL,
            klee_version="v3.2-test",
            _env_file=None,
        )

    assert exc_info.value.errors()[0]["loc"] == ("runner_image",)


@pytest.mark.parametrize(
    "runner_image",
    [
        "",
        "klee-web-runner",
        "ghcr.io/finnleh/klee-web-runner:main",
        "ghcr.io/finnleh/klee-web-runner@sha256:not-a-digest",
    ],
)
def test_runner_image_must_be_immutable(runner_image):
    with pytest.raises(ValidationError):
        make_settings(runner_image=runner_image)


def test_klee_version_reads_environment(monkeypatch):
    monkeypatch.setenv("KLEE_VERSION", "v3.2-test")

    assert make_settings().klee_version == "v3.2-test"


def test_klee_version_is_required(monkeypatch):
    monkeypatch.delenv("KLEE_VERSION")
    with pytest.raises(ValidationError) as exc_info:
        Settings(redis_url=REDIS_URL, celery_broker_url=BROKER_URL, _env_file=None)

    assert exc_info.value.errors()[0]["loc"] == ("klee_version",)


def test_klee_version_must_not_be_empty():
    with pytest.raises(ValidationError):
        make_settings(klee_version="")


def test_redis_url_is_required(monkeypatch):
    monkeypatch.delenv("REDIS_URL")
    with pytest.raises(ValidationError) as exc_info:
        Settings(celery_broker_url=BROKER_URL, _env_file=None)  # type: ignore[call-arg]

    assert exc_info.value.errors()[0]["loc"] == ("redis_url",)


def test_celery_broker_url_is_required(monkeypatch):
    monkeypatch.delenv("CELERY_BROKER_URL")
    with pytest.raises(ValidationError) as exc_info:
        Settings(redis_url=REDIS_URL, _env_file=None)  # type: ignore[call-arg]

    assert exc_info.value.errors()[0]["loc"] == ("celery_broker_url",)


def test_redis_and_celery_urls_are_allowed():
    settings = make_settings()

    assert settings.redis_url == REDIS_URL
    assert settings.celery_broker_url == BROKER_URL
