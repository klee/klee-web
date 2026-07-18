from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str
    celery_broker_url: str
    klee_fake_runner: bool = False
    klee_runtime: str | None = None
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
