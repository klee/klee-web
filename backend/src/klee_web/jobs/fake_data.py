from klee_web.models import HaltReason, JobResult, SymbolicInput, TestCase


def get_sign_result() -> JobResult:
    """Canned result mirroring a real get_sign KLEE run.

    Used by the fake runner so the e2e test asserts the same values against the
    real (local) and fake (CI) backends. Kept in sync with the happy_path fixture.
    """
    return JobResult(
        test_cases=[
            TestCase(
                name="test000001", inputs=[SymbolicInput(name="a", value="0", bytes_hex="00000000")]
            ),
            TestCase(
                name="test000002",
                inputs=[SymbolicInput(name="a", value="16843009", bytes_hex="01010101")],
            ),
            TestCase(
                name="test000003",
                inputs=[SymbolicInput(name="a", value="-2147483648", bytes_hex="00000080")],
            ),
        ],
        messages="KLEE: done: completed paths = 3\nKLEE: done: generated tests = 3",
        warnings="",
        stats={"Instructions": 100, "NumStates": 1, "FullBranches": 2, "WallTime": 0},
        halt_reason=HaltReason.completed,
    )
