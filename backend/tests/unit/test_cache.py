import fakeredis
import pytest

from klee_web.jobs.cache import RedisResultCache, cache_key
from klee_web.models import JobRequest, JobResult, KleeFlags, QueryFormat
from tests.fakes import FakeResultCache

SOURCE = "int main() { return 0; }"


def test_cache_key_is_deterministic():
    a = JobRequest(source=SOURCE)
    b = JobRequest(source=SOURCE)
    assert cache_key(a) == cache_key(b)


def test_cache_key_differs_on_source():
    a = JobRequest(source=SOURCE)
    b = JobRequest(source=SOURCE + " // changed")
    assert cache_key(a) != cache_key(b)


def test_cache_key_differs_on_max_time():
    a = JobRequest(source=SOURCE, flags=KleeFlags(max_time=60))
    b = JobRequest(source=SOURCE, flags=KleeFlags(max_time=120))
    assert cache_key(a) != cache_key(b)


def test_cache_key_differs_on_max_memory():
    a = JobRequest(source=SOURCE, flags=KleeFlags(max_memory=512))
    b = JobRequest(source=SOURCE, flags=KleeFlags(max_memory=1024))
    assert cache_key(a) != cache_key(b)


def test_cache_key_differs_on_query_format():
    a = JobRequest(source=SOURCE, flags=KleeFlags(query_format=QueryFormat.none))
    b = JobRequest(source=SOURCE, flags=KleeFlags(query_format=QueryFormat.kquery))
    assert cache_key(a) != cache_key(b)


def test_cache_key_differs_on_replay_setting():
    a = JobRequest(source=SOURCE, flags=KleeFlags(enable_replay=True))
    b = JobRequest(source=SOURCE, flags=KleeFlags(enable_replay=False))
    assert cache_key(a) != cache_key(b)


def test_cache_key_same_for_explicit_and_default_flags():
    a = JobRequest(source=SOURCE)
    b = JobRequest(source=SOURCE, flags=KleeFlags())
    assert cache_key(a) == cache_key(b)


def test_cache_key_is_hex_sha256():
    key = cache_key(JobRequest(source=SOURCE))
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
