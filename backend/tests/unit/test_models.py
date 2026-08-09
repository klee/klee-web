from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from klee_web.models import (
    MAX_TIME_CEILING,
    HaltReason,
    Job,
    JobRequest,
    JobResult,
    JobStatus,
    KleeFlags,
    SymbolicInput,
    TestCase,
)


def test_klee_flags_defaults():
    flags = KleeFlags()
    assert flags.max_time == 60
    assert flags.max_memory == 512


def test_klee_flags_max_time_below_min_rejected():
    with pytest.raises(ValidationError):
        KleeFlags(max_time=0)


def test_klee_flags_max_time_above_max_rejected():
    with pytest.raises(ValidationError):
        KleeFlags(max_time=601)


def test_max_time_ceiling_is_600():
    assert MAX_TIME_CEILING == 600


def test_klee_flags_max_time_at_ceiling_accepted():
    assert KleeFlags(max_time=MAX_TIME_CEILING).max_time == MAX_TIME_CEILING


def test_klee_flags_max_memory_below_min_rejected():
    with pytest.raises(ValidationError):
        KleeFlags(max_memory=32)


def test_klee_flags_max_memory_above_max_rejected():
    with pytest.raises(ValidationError):
        KleeFlags(max_memory=4096)


def test_klee_flags_extra_flags_defaults_empty():
    assert KleeFlags().extra_flags == ""


def test_klee_flags_accepts_allowed_extra_flags():
    flags = KleeFlags(extra_flags="--optimize --search=dfs")
    assert flags.extra_flags == "--optimize --search=dfs"


def test_klee_flags_rejects_disallowed_extra_flag():
    with pytest.raises(ValidationError):
        KleeFlags(extra_flags="--output-dir=/etc")


def test_klee_flags_rejects_oversized_extra_flags():
    with pytest.raises(ValidationError):
        KleeFlags(extra_flags="--optimize " * 50)


def test_klee_flags_symbolic_input_defaults_none():
    flags = KleeFlags()
    assert flags.sym_stdin is None
    assert flags.sym_files is None
    assert flags.sym_args is None


def test_klee_flags_accepts_symbolic_input_from_dicts():
    flags = KleeFlags(
        sym_stdin={"size": 8},
        sym_files={"count": 2, "size": 8},
        sym_args={"count_min": 1, "count_max": 3, "length": 4},
    )
    assert flags.sym_stdin is not None and flags.sym_stdin.size == 8
    assert flags.sym_files is not None and flags.sym_files.count == 2
    assert flags.sym_args is not None and flags.sym_args.count_max == 3


def test_klee_flags_rejects_bad_symbolic_input():
    with pytest.raises(ValidationError):
        KleeFlags(sym_args={"count_min": 3, "count_max": 1, "length": 4})


def test_job_request_minimal_valid():
    req = JobRequest(source="int main() { return 0; }")
    assert req.source == "int main() { return 0; }"
    assert req.flags.max_time == 60
    assert req.flags.enable_replay is True


def test_job_request_can_disable_replay():
    req = JobRequest(source="int main() {}", flags=KleeFlags(enable_replay=False))
    assert req.flags.enable_replay is False


def test_job_request_empty_source_rejected():
    with pytest.raises(ValidationError):
        JobRequest(source="")


def test_job_request_oversized_source_rejected():
    with pytest.raises(ValidationError):
        JobRequest(source="a" * 64_001)


def test_job_request_accepts_custom_flags():
    req = JobRequest(source="int main() {}", flags=KleeFlags(max_time=120, max_memory=1024))
    assert req.flags.max_time == 120
    assert req.flags.max_memory == 1024


def test_job_defaults():
    job = Job()
    assert job.status == JobStatus.pending
    assert job.result is None


def test_job_instances_have_unique_ids():
    a, b = Job(), Job()
    assert a.id != b.id


def test_job_created_at_is_timezone_aware_and_recent():
    job = Job()
    assert job.created_at.tzinfo is not None
    assert (datetime.now(UTC) - job.created_at).total_seconds() < 1.0


def test_job_status_serialises_as_plain_string():
    job = Job(status=JobStatus.running)
    dumped = job.model_dump(mode="json")
    assert dumped["status"] == "running"


def test_job_cancel_requested_defaults_false():
    assert Job().cancel_requested is False


def test_job_cancel_requested_is_excluded_from_serialisation():
    job = Job()
    job.cancel_requested = True
    assert "cancel_requested" not in job.model_dump(mode="json")


def test_halt_reason_cancelled_serialises_as_plain_string():
    result = JobResult(
        test_cases=[], messages="", warnings="", stats={}, halt_reason=HaltReason.cancelled
    )
    assert result.model_dump(mode="json")["halt_reason"] == "cancelled"


def test_job_result_compile_error_defaults_to_none():
    result = JobResult(test_cases=[], messages="", warnings="", stats={})
    assert result.compile_error is None


def test_job_result_rejects_negative_memory_cull_count():
    with pytest.raises(ValidationError):
        JobResult(
            test_cases=[],
            messages="",
            warnings="",
            stats={},
            states_culled_for_memory=-1,
        )


def test_job_result_with_compile_error_set():
    result = JobResult(
        test_cases=[],
        messages="",
        warnings="",
        stats={},
        compile_error="input.c:3:5: error: expected ';' after expression",
    )
    assert result.compile_error == "input.c:3:5: error: expected ';' after expression"
    assert result.test_cases == []


def test_test_case_error_defaults_to_none():
    tc = TestCase(
        name="test000001", inputs=[SymbolicInput(name="a", value="0", bytes_hex="00000000")]
    )
    assert tc.error is None


def test_test_case_with_error_set():
    tc = TestCase(
        name="test000001",
        inputs=[SymbolicInput(name="a", value="0", bytes_hex="00000000")],
        error="divide by zero at input.c:11",
    )
    assert tc.error == "divide by zero at input.c:11"
