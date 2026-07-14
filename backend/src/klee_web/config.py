from functools import lru_cache
from typing import Annotated, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str | None = None
    celery_broker_url: str | None = None
    klee_fake_runner: bool = False
    klee_runtime: str | None = None
    worker_concurrency_max: Annotated[int, Field(ge=1)] = 4

    @model_validator(mode="after")
    def _broker_requires_redis(self) -> Self:
        if self.celery_broker_url and self.redis_url is None:
            raise ValueError(
                "CELERY_BROKER_URL requires REDIS_URL: a Celery worker and the in-memory "
                "store cannot share job state across processes."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
