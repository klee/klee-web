import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/14")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/15")
