import asyncio
import shutil
import subprocess
from uuid import uuid4

import pytest

from klee_web.jobs.runner import IMAGE_TAG, DockerKleeRunner
from klee_web.models import HaltReason, KleeFlags
from klee_web.symbolic_input import SymStdin


def _runner_environment_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE_TAG],
        capture_output=True,
    )
    return result.returncode == 0


pytestmark = [
    pytest.mark.requires_docker,
    pytest.mark.skipif(
        not _runner_environment_ready(),
        reason=f"docker CLI or {IMAGE_TAG} image not available",
    ),
]


GET_SIGN_SOURCE = """\
#include <klee/klee.h>

int get_sign(int x) {
    if (x == 0) return 0;
    if (x < 0) return -1;
    else return 1;
}

int main() {
    int a;
    klee_make_symbolic(&a, sizeof(a), "a");
    return get_sign(a);
}
"""


SOURCE_MISSING_INCLUDE = """\
int get_sign(int x) {
    if (x == 0) return 0;
    if (x < 0) return -1;
    else return 1;
}

int main() {
    int a;
    klee_make_symbolic(&a, sizeof(a), "a");
    return get_sign(a);
}
"""


DIV_BY_ZERO_SOURCE = """\
#include <klee/klee.h>

int main() {
    int x;
    klee_make_symbolic(&x, sizeof(x), "x");
    return 10 / x;
}
"""


async def test_docker_runner_runs_get_sign_end_to_end():
    runner = DockerKleeRunner()
    result = await asyncio.wait_for(
        runner.execute(GET_SIGN_SOURCE, KleeFlags(max_time=10, max_memory=256), uuid4()),
        timeout=30,
    )
    assert len(result.test_cases) == 3
    assert {tc.inputs[0].value for tc in result.test_cases} == {
        "0",
        "16843009",
        "-2147483648",
    }
    assert result.compile_error is None
    assert all(tc.error is None for tc in result.test_cases)
    assert result.stats["Instructions"] > 0


async def test_docker_runner_runs_with_allowlisted_extra_flags():
    runner = DockerKleeRunner()
    result = await asyncio.wait_for(
        runner.execute(
            GET_SIGN_SOURCE,
            KleeFlags(max_time=10, max_memory=256, extra_flags="--optimize --search=dfs"),
            uuid4(),
        ),
        timeout=30,
    )
    assert len(result.test_cases) == 3
    assert result.compile_error is None


SYM_STDIN_SOURCE = """\
#include <unistd.h>

int main() {
    char c;
    if (read(0, &c, 1) <= 0) return 0;
    if (c == 'A') return 1;
    if (c == 'B') return 2;
    return 0;
}
"""


async def test_docker_runner_makes_stdin_symbolic_with_sym_stdin():
    runner = DockerKleeRunner()
    result = await asyncio.wait_for(
        runner.execute(
            SYM_STDIN_SOURCE,
            KleeFlags(max_time=10, max_memory=256, sym_stdin=SymStdin(size=1)),
            uuid4(),
        ),
        timeout=30,
    )
    # Without --sym-stdin the single read hits EOF and the program has one path;
    # making stdin symbolic forks it, so more than one test case proves the flag took effect.
    assert len(result.test_cases) >= 2
    assert result.compile_error is None


async def test_docker_runner_surfaces_compile_error_from_missing_include():
    runner = DockerKleeRunner()
    result = await asyncio.wait_for(
        runner.execute(SOURCE_MISSING_INCLUDE, KleeFlags(max_time=10, max_memory=256), uuid4()),
        timeout=30,
    )
    assert result.compile_error is not None
    assert "klee_make_symbolic" in result.compile_error or "undeclared" in result.compile_error
    assert result.test_cases == []
    assert result.stats == {}


MANY_PATHS_SOURCE = """\
#include <klee/klee.h>

int main() {
    int a;
    klee_make_symbolic(&a, sizeof(a), "a");
    int sum = 0;
    for (int i = 0; i < 20; i++) {
        if ((a >> i) & 1) sum += i;
        else sum -= i;
    }
    if (sum == 12345) return 1;
    return 0;
}
"""


async def _container_running(name: str) -> bool:
    proc = await asyncio.create_subprocess_exec(
        "docker",
        "ps",
        "--filter",
        f"name={name}",
        "--format",
        "{{.Names}}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    return name in out.decode()


async def test_docker_runner_cancel_halts_with_partial_results():
    runner = DockerKleeRunner()
    job_id = uuid4()
    name = f"klee-job-{job_id}"
    task = asyncio.create_task(
        runner.execute(MANY_PATHS_SOURCE, KleeFlags(max_time=60, max_memory=256), job_id)
    )
    try:
        for _ in range(50):
            if await _container_running(name):
                break
            await asyncio.sleep(0.3)
        else:
            pytest.fail("container never started")

        await asyncio.sleep(2)  # let KLEE explore so the halt has states to dump

        assert await runner.cancel(job_id) is True
        # If the entrypoint did not forward the halt, this would run until max_time
        # and the wait_for would expire instead.
        result = await asyncio.wait_for(task, timeout=30)
    finally:
        if not task.done():
            task.cancel()
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)

    assert len(result.test_cases) >= 1
    assert not await _container_running(name)


async def test_docker_runner_pairs_div_err_with_failing_test_case():
    runner = DockerKleeRunner()
    result = await asyncio.wait_for(
        runner.execute(DIV_BY_ZERO_SOURCE, KleeFlags(max_time=10, max_memory=256), uuid4()),
        timeout=30,
    )
    assert len(result.test_cases) == 2
    assert sum(tc.error is not None for tc in result.test_cases) == 1
    failing = next(tc for tc in result.test_cases if tc.error is not None)
    assert failing.error is not None
    assert {i.name: i.value for i in failing.inputs} == {"x": "0"}
    assert "divide by zero" in failing.error
    assert result.compile_error is None


WEDGING_SOURCE = """\
#include <klee/klee.h>

int main() {
    unsigned int a, b;
    klee_make_symbolic(&a, sizeof(a), "a");
    klee_make_symbolic(&b, sizeof(b), "b");
    klee_assume(a > 1);
    klee_assume(b > 1);
    // A 62-bit semiprime: a*b == C with a,b > 1 is a factoring query KLEE wedges on,
    // ignoring its own --max-time. The entrypoint's bound is what must stop it.
    if ((unsigned long)a * (unsigned long)b == 4611768348991799089UL) return 1;
    return 0;
}
"""


async def test_docker_runner_bounds_a_klee_that_overruns_its_own_max_time():
    runner = DockerKleeRunner()
    job_id = uuid4()
    name = f"klee-job-{job_id}"
    try:
        # KLEE should self-halt at max_time=5, but it wedges in the solver and ignores
        # its own timer. The entrypoint bound (max_time + 15) plus the grace must stop
        # it well under this wait_for; without the bound the run never returns.
        result = await asyncio.wait_for(
            runner.execute(WEDGING_SOURCE, KleeFlags(max_time=5, max_memory=512), job_id),
            timeout=45,
        )
        assert result.halt_reason == HaltReason.max_time
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


PER_PATH_POSIX_SOURCE = """\
#include <stdio.h>
#include <unistd.h>

int main() {
    char c;
    read(0, &c, 1);
    if (c == 'a') printf("Hello World!");
    else printf("Goodbye World!");
    return 0;
}
"""


async def test_docker_runner_captures_per_path_output_for_posix_input():
    runner = DockerKleeRunner()
    result = await asyncio.wait_for(
        runner.execute(
            PER_PATH_POSIX_SOURCE,
            KleeFlags(max_time=10, max_memory=256, sym_stdin=SymStdin(size=1)),
            uuid4(),
        ),
        timeout=30,
    )
    # Replay re-runs each ktest natively, so each path shows what it printed. The
    # symbolic byte arrives through POSIX stdin, which the replay driver's setup
    # (klee_init_env + replay_create_files) reconstructs per fork. Membership, not
    # equality, so an extra or an unreplayed path does not make this brittle.
    outputs = {tc.program_output for tc in result.test_cases}
    assert "Hello World!" in outputs
    assert "Goodbye World!" in outputs


PER_PATH_MAKE_SYMBOLIC_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>

int main() {
    int x;
    klee_make_symbolic(&x, sizeof(x), "x");
    if (x == 0) printf("ZERO");
    else if (x < 0) printf("NEG");
    else printf("POS");
    return 0;
}
"""


async def test_docker_runner_captures_per_path_output_for_make_symbolic():
    runner = DockerKleeRunner()
    result = await asyncio.wait_for(
        runner.execute(
            PER_PATH_MAKE_SYMBOLIC_SOURCE,
            KleeFlags(max_time=10, max_memory=256),
            uuid4(),
        ),
        timeout=30,
    )
    # The make_symbolic value is consumed from the ktest by the replay driver's
    # in-order reader; with the POSIX test above this covers both input channels.
    assert len(result.test_cases) == 3
    outputs = {tc.program_output for tc in result.test_cases}
    assert outputs == {"ZERO", "NEG", "POS"}
