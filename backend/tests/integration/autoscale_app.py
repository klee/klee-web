import os
import time

import redis
from celery import Celery
from celery.worker.autoscale import Autoscaler


class FastAutoscaler(Autoscaler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, keepalive=0.1, **kwargs)


app = Celery(
    "autoscale_test",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1"),
)
app.conf.worker_autoscaler = FastAutoscaler
RELEASE_KEY = "autoscale-probe:release"


@app.task(name="autoscale_probe")
def autoscale_probe() -> None:
    client = redis.Redis.from_url(os.environ["CELERY_BROKER_URL"])
    try:
        while not client.exists(RELEASE_KEY):
            time.sleep(0.05)
    finally:
        client.close()
