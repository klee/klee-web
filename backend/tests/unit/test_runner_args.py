from uuid import uuid4

from klee_web.jobs.runner import build_run_args, resolve_runtime
from klee_web.models import KleeFlags


def _value_after(args: list[str], flag: str) -> str | None:
    if flag not in args:
        return None
    return args[args.index(flag) + 1]


def test_build_run_args_always_disables_network() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime=None)
    assert _value_after(args, "--network") == "none"


def test_build_run_args_omits_runtime_when_none() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime=None)
    assert "--runtime" not in args


def test_build_run_args_includes_runtime_when_set() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime="runsc-kvm")
    assert _value_after(args, "--runtime") == "runsc-kvm"


def test_build_run_args_is_a_docker_run_for_the_image() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime="runsc")
    assert args[:2] == ["docker", "run"]
    assert args[-1] == "klee-web-runner"


def test_resolve_runtime_unset_is_runc() -> None:
    assert resolve_runtime(None) is None
    assert resolve_runtime("") is None
    assert resolve_runtime("runc") is None


def test_resolve_runtime_auto_picks_kvm_when_present() -> None:
    assert resolve_runtime("auto", kvm_present=True) == "runsc-kvm"


def test_resolve_runtime_auto_falls_back_to_systrap() -> None:
    assert resolve_runtime("auto", kvm_present=False) == "runsc"


def test_resolve_runtime_explicit_passes_through() -> None:
    assert resolve_runtime("runsc") == "runsc"
    assert resolve_runtime("runsc-kvm") == "runsc-kvm"
