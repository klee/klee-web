import hashlib
import json

import fakeredis
import pytest

import klee_web.jobs.cache as cache_module
from klee_web.jobs.cache import RedisResultCache, cache_key
from klee_web.models import JobRequest, JobResult, KleeFlags, QueryFormat
from tests.fakes import FakeResultCache

SOURCE = "int main() { return 0; }"
RUNNER_ID = "klee-web-runner@sha256:runner-test"


def test_cache_key_is_deterministic():
    a = JobRequest(source=SOURCE)
    b = JobRequest(source=SOURCE)
    assert cache_key(a, RUNNER_ID) == cache_key(b, RUNNER_ID)


def test_cache_key_differs_on_source():
    a = JobRequest(source=SOURCE)
    b = JobRequest(source=SOURCE + " // changed")
    assert cache_key(a, RUNNER_ID) != cache_key(b, RUNNER_ID)


def test_cache_key_differs_on_max_time():
    a = JobRequest(source=SOURCE, flags=KleeFlags(max_time=60))
    b = JobRequest(source=SOURCE, flags=KleeFlags(max_time=120))
    assert cache_key(a, RUNNER_ID) != cache_key(b, RUNNER_ID)


def test_cache_key_differs_on_max_memory():
    a = JobRequest(source=SOURCE, flags=KleeFlags(max_memory=512))
    b = JobRequest(source=SOURCE, flags=KleeFlags(max_memory=1024))
    assert cache_key(a, RUNNER_ID) != cache_key(b, RUNNER_ID)


def test_cache_key_differs_on_query_format():
    a = JobRequest(source=SOURCE, flags=KleeFlags(query_format=QueryFormat.none))
    b = JobRequest(source=SOURCE, flags=KleeFlags(query_format=QueryFormat.kquery))
    assert cache_key(a, RUNNER_ID) != cache_key(b, RUNNER_ID)


def test_cache_key_differs_on_runner_image():
    a = JobRequest(source=SOURCE)
    assert cache_key(a, RUNNER_ID) != cache_key(a, "klee-web-runner@sha256:runner-test-b")


def test_cache_key_differs_on_job_result_schema(monkeypatch):
    request = JobRequest(source=SOURCE)
    original_key = cache_key(request, RUNNER_ID)

    changed_schema = JobResult.model_json_schema()
    changed_schema["properties"]["new_result_field"] = {"type": "string"}
    changed_schema_json = json.dumps(
        changed_schema,
        sort_keys=True,
        separators=(",", ":"),
    )
    changed_schema_hash = hashlib.sha256(changed_schema_json.encode()).hexdigest()

    monkeypatch.setattr(cache_module, "_JOB_RESULT_SCHEMA_HASH", changed_schema_hash)

    assert cache_key(request, RUNNER_ID) != original_key


def test_cache_key_differs_on_replay_setting():
    a = JobRequest(source=SOURCE, flags=KleeFlags(enable_replay=True))
    b = JobRequest(source=SOURCE, flags=KleeFlags(enable_replay=False))
    assert cache_key(a, RUNNER_ID) != cache_key(b, RUNNER_ID)


def test_cache_key_same_for_explicit_and_default_flags():
    a = JobRequest(source=SOURCE)
    b = JobRequest(source=SOURCE, flags=KleeFlags())
    assert cache_key(a, RUNNER_ID) == cache_key(b, RUNNER_ID)


def test_cache_key_is_hex_sha256():
    key = cache_key(JobRequest(source=SOURCE), RUNNER_ID)
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


@pytest.fixture(params=["fake", "redis"])
async def cache(request):
    if request.param == "fake":
        yield FakeResultCache()
        return
    client = fakeredis.FakeAsyncRedis(server=fakeredis.FakeServer())
    yield RedisResultCache(client)
    await client.aclose()


async def test_get_miss_returns_none(cache):
    assert await cache.get("absent") is None


async def test_set_then_get_round_trips(cache, sample_result):
    await cache.set("k", sample_result)
    assert await cache.get("k") == sample_result


async def test_set_overwrites_existing(cache, sample_result):
    other = JobResult(test_cases=[], messages="changed", warnings="", stats={})
    await cache.set("k", sample_result)
    await cache.set("k", other)
    assert await cache.get("k") == other


async def test_distinct_keys_coexist(cache, sample_result):
    other = JobResult(test_cases=[], messages="other", warnings="", stats={})
    await cache.set("k1", sample_result)
    await cache.set("k2", other)
    assert await cache.get("k1") == sample_result
    assert await cache.get("k2") == other
