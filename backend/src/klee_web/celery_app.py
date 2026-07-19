import asyncio
from uuid import UUID

from celery import Celery

from klee_web.config import Settings, get_settings
from klee_web.jobs.cache import ResultCache
from klee_web.jobs.run import run_job
from klee_web.jobs.runner import DockerKleeRunner, KleeRunner, RunnerCaps, resolve_runtime
from klee_web.jobs.store import JobStore
from klee_web.jobs.usage import UsageStatsStore
from klee_web.models import JobRequest

TASK_QUEUE = "klee-jobs"

app = Celery("klee_web", broker=get_settings().celery_broker_url)
app.conf.update(
    task_default_queue=TASK_QUEUE,
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    worker_prefetch_multiplier=1,
)


def _build_store(settings: Settings) -> JobStore:
    from redis.asyncio import Redis

    from klee_web.jobs.store import RedisJobStore

    return RedisJobStore(Redis.from_url(settings.redis_url))


def _build_runner(settings: Settings) -> KleeRunner:
    return DockerKleeRunner(
        caps=RunnerCaps(
            cpus=settings.runner_cpus,
            memory_mb=settings.runner_memory_mb,
            swap_mb=settings.runner_swap_mb,
            pids_limit=settings.runner_pids_limit,
            storage_mb=settings.runner_storage_mb,
        ),
        runtime=resolve_runtime(settings.klee_runtime),
        image=settings.runner_image,
    )


def _build_cache(settings: Settings) -> ResultCache:
    from redis.asyncio import Redis

    from klee_web.jobs.cache import RedisResultCache

    return RedisResultCache(Redis.from_url(settings.redis_url))


def _build_usage(settings: Settings) -> UsageStatsStore:
    from redis.asyncio import Redis

    from klee_web.jobs.usage import RedisUsageStatsStore

    return RedisUsageStatsStore(Redis.from_url(settings.redis_url))


@app.task(name="run_klee_job")
def run_klee_job(job_id: str, request_data: dict[str, object]) -> None:
    settings = get_settings()

    async def _run() -> None:
        store = _build_store(settings)
        runner = _build_runner(settings)
        cache = _build_cache(settings)
        usage = _build_usage(settings)
        await run_job(
            UUID(job_id), JobRequest.model_validate(request_data), store, runner, cache, usage
        )

    asyncio.run(_run())
