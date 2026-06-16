from klee_web.models import HaltReason, JobResult, TestCase


def get_sign_result() -> JobResult:
    """Canned result mirroring a real get_sign KLEE run.

    Used by the fake runner so the e2e test asserts the same values against the
    real (local) and fake (CI) backends. Kept in sync with the happy_path fixture.
    """
    return JobResult(
        test_cases=[
            TestCase(name="test000001", inputs={"a": "0"}),
            TestCase(name="test000002", inputs={"a": "16843009"}),
            TestCase(name="test000003", inputs={"a": "-2147483648"}),
        ],
        messages="KLEE: done: completed paths = 3\nKLEE: done: generated tests = 3",
        warnings="",
        stats={"Instructions": 100, "NumStates": 1, "FullBranches": 2, "WallTime": 0},
        halt_reason=HaltReason.completed,
    )
