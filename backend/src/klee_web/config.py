from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str
    celery_broker_url: str
    klee_runtime: str | None = None
    klee_version: str = ""

    @field_validator("klee_version")
    @classmethod
    def _klee_version_required(cls, v: str) -> str:
        if not v:
            raise ValueError("KLEE_VERSION is required")
        return v

    runner_image: Annotated[
        str,
        Field(pattern=r"^(?:sha256:[0-9a-f]{64}|.+@sha256:[0-9a-f]{64})$"),
    ]
    worker_concurrency_max: Annotated[int, Field(ge=1)] = 4
    runner_cpus: Annotated[float, Field(gt=0)] = 2
    runner_memory_mb: Annotated[int, Field(gt=0)] = 3072
    runner_swap_mb: Annotated[int, Field(ge=0)] = 0
    runner_pids_limit: Annotated[int, Field(gt=0)] = 128
    runner_storage_mb: Annotated[int, Field(gt=0)] = 768


@lru_cache
def get_settings() -> Settings:
    # BaseSettings supplies these required fields from the environment at runtime.
    return Settings()  # type: ignore[call-arg]
