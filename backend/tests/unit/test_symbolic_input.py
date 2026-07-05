import pytest
from pydantic import ValidationError

from klee_web.symbolic_input import SymArgs, SymFiles, SymStdin, render_posix_args


def test_render_empty_when_all_none():
    assert render_posix_args() == ""


def test_render_sym_stdin_only():
    assert render_posix_args(sym_stdin=SymStdin(size=8)) == "--sym-stdin 8"


def test_render_sym_files_only():
    assert render_posix_args(sym_files=SymFiles(count=2, size=8)) == "--sym-files 2 8"


def test_render_sym_args_only():
    got = render_posix_args(sym_args=SymArgs(count_min=1, count_max=3, length=4))
    assert got == "--sym-args 1 3 4"


def test_render_all_three_files_args_stdin_order():
    got = render_posix_args(
        sym_files=SymFiles(count=2, size=8),
        sym_args=SymArgs(count_min=1, count_max=3, length=4),
        sym_stdin=SymStdin(size=8),
    )
    assert got == "--sym-files 2 8 --sym-args 1 3 4 --sym-stdin 8"


def test_sym_stdin_size_below_min_rejected():
    with pytest.raises(ValidationError):
        SymStdin(size=0)


def test_sym_stdin_size_above_max_rejected():
    with pytest.raises(ValidationError):
        SymStdin(size=257)


def test_sym_files_count_below_min_rejected():
    with pytest.raises(ValidationError):
        SymFiles(count=0, size=8)


def test_sym_files_size_above_max_rejected():
    with pytest.raises(ValidationError):
        SymFiles(count=1, size=257)


def test_sym_args_count_min_zero_allowed():
    assert SymArgs(count_min=0, count_max=1, length=4).count_min == 0


def test_sym_args_count_max_below_min_rejected():
    with pytest.raises(ValidationError):
        SymArgs(count_min=3, count_max=1, length=4)


def test_sym_args_length_above_max_rejected():
    with pytest.raises(ValidationError):
        SymArgs(count_min=1, count_max=3, length=101)
