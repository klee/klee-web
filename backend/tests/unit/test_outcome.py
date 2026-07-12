import pytest

from klee_web.models import (
    HaltReason,
    Job,
    JobOutcome,
    JobResult,
    JobStatus,
    outcome_of_job,
    outcome_of_result,
)


def _result(**kwargs: object) -> JobResult:
    base: dict[str, object] = {"test_cases": [], "messages": "", "warnings": "", "stats": {}}
    base.update(kwargs)
    return JobResult(**base)  # type: ignore[arg-type]


def _done(result: JobResult) -> Job:
    return Job(status=JobStatus.done, result=result)


def test_pending_and_running_have_no_outcome() -> None:
    assert outcome_of_job(Job(status=JobStatus.pending)) is None
    assert outcome_of_job(Job(status=JobStatus.running)) is None


def test_failed_status_maps_to_failed() -> None:
    assert outcome_of_job(Job(status=JobStatus.failed)) is JobOutcome.failed


def test_compile_error_maps_to_compile_error() -> None:
    assert outcome_of_job(_done(_result(compile_error="boom"))) is JobOutcome.compile_error


@pytest.mark.parametrize(
    ("halt", "expected"),
    [
        (HaltReason.completed, JobOutcome.completed),
        (HaltReason.max_time, JobOutcome.max_time),
        (HaltReason.cancelled, JobOutcome.cancelled),
    ],
)
def test_halt_reason_maps_through(halt: HaltReason, expected: JobOutcome) -> None:
    assert outcome_of_job(_done(_result(halt_reason=halt))) is expected


def test_done_without_halt_reason_defaults_to_completed() -> None:
    assert outcome_of_job(_done(_result())) is JobOutcome.completed


def test_outcome_of_result_classifies_a_result_directly() -> None:
    assert outcome_of_result(_result(compile_error="boom")) is JobOutcome.compile_error
    assert outcome_of_result(_result(halt_reason=HaltReason.max_time)) is JobOutcome.max_time
    assert outcome_of_result(_result()) is JobOutcome.completed


def test_outcome_is_exposed_on_the_job_model() -> None:
    job = _done(_result(halt_reason=HaltReason.max_time))
    assert job.outcome is JobOutcome.max_time
    assert job.model_dump()["outcome"] == "max_time"
    assert Job(status=JobStatus.running).model_dump()["outcome"] is None
