from pathlib import Path

from klee_web.models import HaltReason
from klee_web.parsing.klee_output import parse_output_dir

FIXTURES = Path(__file__).parent.parent / "fixtures" / "klee_output_sample"


def test_parse_compile_error_returns_only_compile_error_field():
    result = parse_output_dir(FIXTURES / "compile_error" / "output")
    assert result.compile_error is not None
    assert "undeclared function" in result.compile_error
    assert result.test_cases == []
    assert result.messages == ""
    assert result.warnings == ""
    assert result.stats == {}
    assert result.halt_reason is None


def test_parse_happy_path_returns_three_test_cases_with_decoded_inputs():
    result = parse_output_dir(FIXTURES / "happy_path" / "output")
    assert [tc.name for tc in result.test_cases] == [
        "test000001",
        "test000002",
        "test000003",
    ]
    assert result.test_cases[0].inputs == {"a": "0"}
    assert result.test_cases[1].inputs == {"a": "16843009"}
    assert result.test_cases[2].inputs == {"a": "-2147483648"}
    assert result.compile_error is None


def test_parse_happy_path_reads_messages_and_warnings():
    result = parse_output_dir(FIXTURES / "happy_path" / "output")
    assert "STP solver backend" in result.messages
    assert "MiniSat" in result.messages
    assert "WARNING ONCE" in result.warnings


def test_parse_happy_path_reads_run_stats_final_row():
    result = parse_output_dir(FIXTURES / "happy_path" / "output")
    assert result.stats["Instructions"] == 13358
    assert result.stats["NumBranches"] == 535
    assert result.stats["TerminationExit"] == 3
    assert result.stats["WallTime"] > 0
    assert isinstance(result.stats["WallTime"], int)


def test_parse_progress_skips_test_cases_but_keeps_stats_and_messages():
    result = parse_output_dir(FIXTURES / "happy_path" / "output", include_test_cases=False)
    assert result.test_cases == []
    assert result.stats["Instructions"] == 13358
    assert "STP solver backend" in result.messages
    assert "WARNING ONCE" in result.warnings
    assert result.halt_reason == HaltReason.completed
    assert result.compile_error is None


def test_parse_runtime_error_attaches_err_to_matching_test_case():
    result = parse_output_dir(FIXTURES / "runtime_error" / "output")
    assert [tc.name for tc in result.test_cases] == ["test000001", "test000002"]
    assert result.test_cases[0].inputs == {"x": "0"}
    assert result.test_cases[1].inputs == {"x": "16843009"}
    assert result.test_cases[0].error is not None
    assert "divide by zero" in result.test_cases[0].error
    assert "input.c" in result.test_cases[0].error
    assert result.test_cases[1].error is None
    assert result.compile_error is None


def test_parse_happy_path_halt_reason_is_completed():
    result = parse_output_dir(FIXTURES / "happy_path" / "output")
    assert result.halt_reason == HaltReason.completed


def test_parse_runtime_error_halt_reason_is_completed():
    result = parse_output_dir(FIXTURES / "runtime_error" / "output")
    assert result.halt_reason == HaltReason.completed


def test_parse_max_time_halt_reason_is_max_time():
    result = parse_output_dir(FIXTURES / "max_time" / "output")
    assert result.halt_reason == HaltReason.max_time


def test_parse_program_output_defaults_to_empty_when_absent():
    result = parse_output_dir(FIXTURES / "happy_path" / "output")
    assert result.program_output == ""


def test_parse_program_output_reads_captured_program_stdout():
    result = parse_output_dir(FIXTURES / "program_output" / "output")
    assert "hello from klee web" in result.program_output
    assert "x is positive" in result.program_output
    assert "x is not positive" in result.program_output


def test_parse_path_constraint_is_none_when_no_kquery_files():
    result = parse_output_dir(FIXTURES / "happy_path" / "output")
    assert all(tc.path_constraint is None for tc in result.test_cases)


def test_parse_path_constraint_reads_kquery_per_test_case():
    result = parse_output_dir(FIXTURES / "kquery" / "output")
    assert len(result.test_cases) == 3
    for tc in result.test_cases:
        assert tc.path_constraint is not None
        assert "query" in tc.path_constraint
    assert "ReadLSB w32 0 x" in result.test_cases[0].path_constraint


def test_parse_host_timeout_sentinel_is_max_time(tmp_path):
    # The entrypoint drops this file when it force-stops a KLEE that overran its own
    # --max-time, so a wedged job reads as a time-limit stop, not a clean empty run.
    output = tmp_path / "output"
    output.mkdir()
    (output / "host_timeout").touch()

    result = parse_output_dir(output)

    assert result.halt_reason == HaltReason.max_time
