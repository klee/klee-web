import os
from urllib.parse import urlparse


def test_integration_redis_databases_do_not_overlap_application_databases() -> None:
    store_db = int(urlparse(os.environ["REDIS_URL"]).path.removeprefix("/"))
    broker_db = int(urlparse(os.environ["CELERY_BROKER_URL"]).path.removeprefix("/"))

    assert {store_db, broker_db}.isdisjoint({0, 1})
