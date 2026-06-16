import os
from functools import lru_cache

from klee_web.jobs.runner import DockerKleeRunner, KleeRunner
from klee_web.jobs.store import InMemoryJobStore, JobStore


@lru_cache
def get_job_store() -> JobStore:
    return InMemoryJobStore()


@lru_cache
def get_runner() -> KleeRunner:
    if os.environ.get("KLEE_FAKE_RUNNER") == "1":
        from klee_web.jobs.fake_data import get_sign_result
        from klee_web.jobs.runner import FakeKleeRunner

        return FakeKleeRunner(canned_result=get_sign_result())
    return DockerKleeRunner()
