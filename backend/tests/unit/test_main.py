import pytest
from pydantic import ValidationError

from klee_web.config import get_settings
from klee_web.main import app


async def test_startup_rejects_missing_required_settings(monkeypatch):
    monkeypatch.delenv("REDIS_URL")
    monkeypatch.delenv("CELERY_BROKER_URL")
    get_settings.cache_clear()

    try:
        with pytest.raises(ValidationError):
            async with app.router.lifespan_context(app):
                pass
    finally:
        get_settings.cache_clear()
