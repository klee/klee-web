import pytest

from klee_web.flag_allowlist import FlagError, validate_extra_flags


def test_empty_string_is_valid():
    assert validate_extra_flags("") == ""


def test_bare_boolean_flag_accepted():
    assert validate_extra_flags("--optimize") == "--optimize"


def test_boolean_flag_with_false_value_accepted():
    assert validate_extra_flags("--use-cex-cache=false") == "--use-cex-cache=false"


def test_boolean_flag_rejects_non_bool_value():
    with pytest.raises(FlagError):
        validate_extra_flags("--optimize=maybe")


def test_int_flag_in_range_accepted():
    assert validate_extra_flags("--max-forks=1000") == "--max-forks=1000"


def test_int_flag_out_of_range_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags("--max-forks=0")


def test_int_flag_non_numeric_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags("--max-depth=lots")


def test_enum_flag_valid_value_accepted():
    assert validate_extra_flags("--search=dfs") == "--search=dfs"


def test_enum_flag_preserves_colon_value():
    assert validate_extra_flags("--search=nurs:covnew") == "--search=nurs:covnew"


def test_enum_flag_invalid_value_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags("--search=magic")


def test_unknown_flag_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags("--load-plugin=evil.so")


def test_managed_flag_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags("--output-dir=/etc")


def test_external_calls_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags("--external-calls=all")


def test_space_separated_value_rejected():
    # value flags must use --flag=value, a space-separated value is two tokens
    with pytest.raises(FlagError):
        validate_extra_flags("--search dfs")


def test_bare_value_token_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags("dfs")


def test_multiple_valid_flags_accepted():
    raw = "--optimize --search=bfs --max-forks=50"
    assert validate_extra_flags(raw) == raw


def test_malformed_quotes_rejected():
    with pytest.raises(FlagError):
        validate_extra_flags('--search="dfs')
