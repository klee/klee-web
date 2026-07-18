from klee_web.models import JobOutcome
from tests.fakes import FakeUsageStatsStore


async def test_empty_snapshot_has_all_outcomes_zero_filled() -> None:
    snap = await FakeUsageStatsStore().snapshot()
    assert set(snap.outcomes) == set(JobOutcome)
    assert all(v == 0 for v in snap.outcomes.values())
    assert snap.cache_hits == 0
    assert snap.test_cases_generated == 0
    assert snap.instructions_executed == 0


async def test_record_execution_accumulates_outcomes_and_totals() -> None:
    store = FakeUsageStatsStore()
    await store.record_execution(JobOutcome.completed, test_cases=3, instructions=100)
    await store.record_execution(JobOutcome.completed, test_cases=2, instructions=50)
    await store.record_execution(JobOutcome.failed)
    snap = await store.snapshot()
    assert snap.outcomes[JobOutcome.completed] == 2
    assert snap.outcomes[JobOutcome.failed] == 1
    assert snap.outcomes[JobOutcome.max_time] == 0
    assert snap.test_cases_generated == 5
    assert snap.instructions_executed == 150


async def test_record_cache_hit_accumulates() -> None:
    store = FakeUsageStatsStore()
    await store.record_cache_hit()
    await store.record_cache_hit()
    assert (await store.snapshot()).cache_hits == 2
