from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str | None = None
    klee_fake_runner: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
