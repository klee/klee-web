from uuid import uuid4

from klee_web.jobs.runner import RunnerCaps, build_run_args, resolve_runtime
from klee_web.models import KleeFlags

CAPS = RunnerCaps(cpus=2, memory_mb=3072, swap_mb=0, pids_limit=128, storage_mb=768)


def _value_after(args: list[str], flag: str) -> str | None:
    if flag not in args:
        return None
    return args[args.index(flag) + 1]


def test_build_run_args_always_disables_network() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime=None, caps=CAPS)
    assert _value_after(args, "--network") == "none"


def test_build_run_args_omits_runtime_when_none() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime=None, caps=CAPS)
    assert "--runtime" not in args


def test_build_run_args_includes_runtime_when_set() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime="runsc-kvm", caps=CAPS)
    assert _value_after(args, "--runtime") == "runsc-kvm"


def test_build_run_args_is_a_docker_run_for_the_image() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime="runsc", caps=CAPS)
    assert args[:2] == ["docker", "run"]
    assert args[-1] == "klee-web-runner"


def test_build_run_args_uses_configured_image() -> None:
    image = "ghcr.io/finnleh/klee-web-runner@sha256:" + "a" * 64

    args = build_run_args(uuid4(), KleeFlags(), "", runtime="runsc", caps=CAPS, image=image)

    assert args[-1] == image


def test_build_run_args_applies_runner_caps() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime=None, caps=CAPS)

    assert _value_after(args, "--cpus") == "2"
    assert _value_after(args, "--memory") == "3072m"
    assert _value_after(args, "--memory-swap") == "3072m"
    assert _value_after(args, "--pids-limit") == "128"


def test_build_run_args_limits_writable_storage() -> None:
    args = build_run_args(uuid4(), KleeFlags(), "", runtime=None, caps=CAPS)

    assert "--read-only" in args
    assert _value_after(args, "--tmpfs") == ("/work:rw,exec,size=768m,uid=1000,gid=1000,mode=0700")
    assert "TMPDIR=/work" in args


def test_build_run_args_adds_swap_allowance_to_docker_total() -> None:
    caps = RunnerCaps(
        cpus=1.5,
        memory_mb=3072,
        swap_mb=512,
        pids_limit=64,
        storage_mb=1024,
    )

    args = build_run_args(uuid4(), KleeFlags(), "", runtime=None, caps=caps)

    assert _value_after(args, "--memory-swap") == "3584m"
    assert _value_after(args, "--tmpfs") == ("/work:rw,exec,size=1024m,uid=1000,gid=1000,mode=0700")


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
