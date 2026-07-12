from klee_web.jobs.telemetry import build_worker_telemetry


def test_none_inputs_produce_no_workers() -> None:
    assert build_worker_telemetry(None, None, None) == []


def test_worker_fields_are_shaped_from_inspect_dicts() -> None:
    stats = {
        "worker1@host": {"pool": {"max-concurrency": 4}},
        "worker2@host": {"pool": {"max-concurrency": 2}},
    }
    active = {
        "worker1@host": [{"id": "a"}, {"id": "b"}],
        "worker2@host": [],
    }
    reserved = {
        "worker1@host": [{"id": "c"}],
        "worker2@host": [],
    }
    by_name = {w.name: w for w in build_worker_telemetry(stats, active, reserved)}
    assert by_name["worker1@host"].concurrency == 4
    assert by_name["worker1@host"].active == 2
    assert by_name["worker1@host"].reserved == 1
    assert by_name["worker2@host"].concurrency == 2
    assert by_name["worker2@host"].active == 0
    assert by_name["worker2@host"].reserved == 0


def test_worker_absent_from_active_counts_zero() -> None:
    stats = {"worker1@host": {"pool": {"max-concurrency": 1}}}
    workers = build_worker_telemetry(stats, active=None, reserved=None)
    assert len(workers) == 1
    assert workers[0].concurrency == 1
    assert workers[0].active == 0
    assert workers[0].reserved == 0
