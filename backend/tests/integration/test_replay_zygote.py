"""Per-path replay through the zygote driver (ADR-0022), one test per proven
failure dimension. These assert on behavior the pre-zygote replay could not
produce (mixed symbolic input, klee_int, libm) or must not lose (atexit,
crash isolation, hang bounding), so they are the standing regression guard
for runner/replay_driver.c."""

import asyncio
import shutil
import subprocess
from uuid import uuid4

import pytest

from klee_web.jobs.runner import DEFAULT_RUNNER_IMAGE, DockerKleeRunner, RunnerCaps
from klee_web.models import KleeFlags
from klee_web.symbolic_input import SymArgs, SymFiles, SymStdin

TEST_CAPS = RunnerCaps(
    cpus=2,
    memory_mb=3072,
    swap_mb=0,
    pids_limit=128,
    storage_mb=768,
)


def _runner_environment_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", DEFAULT_RUNNER_IMAGE],
        capture_output=True,
    )
    return result.returncode == 0


pytestmark = [
    pytest.mark.requires_docker,
    pytest.mark.skipif(
        not _runner_environment_ready(),
        reason=f"docker CLI or {DEFAULT_RUNNER_IMAGE} image not available",
    ),
]


async def _run(source: str, flags: KleeFlags, timeout: int = 45):
    runner = DockerKleeRunner(TEST_CAPS)
    return await asyncio.wait_for(runner.execute(source, flags, uuid4()), timeout=timeout)


MIXED_STDIN_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>
#include <unistd.h>

int main() {
    char s;
    klee_make_symbolic(&s, sizeof(s), "s");
    char c = 0;
    read(0, &c, 1);
    if (s == 'K' && c == 'K') printf("BOTH");
    else if (s == 'K') printf("S_ONLY");
    else if (c == 'K') printf("C_ONLY");
    else printf("NEITHER");
    return 0;
}
"""


async def test_mixed_make_symbolic_and_sym_stdin_replays_every_path():
    # The pre-zygote replay aborted on ANY program mixing klee_make_symbolic with
    # POSIX symbolic input (libkleeRuntest name/position mismatch), so every path
    # showed empty output. Set equality proves all four paths now replay.
    result = await _run(
        MIXED_STDIN_SOURCE,
        KleeFlags(max_time=10, max_memory=256, sym_stdin=SymStdin(size=1)),
    )
    outputs = {tc.program_output for tc in result.test_cases}
    assert outputs == {"BOTH", "S_ONLY", "C_ONLY", "NEITHER"}
    # Oracle cross-check: the BOTH path's recorded inputs must be the values the
    # branch demands ('K' = 75), for both the direct object and the stdin object.
    both = next(tc for tc in result.test_cases if tc.program_output == "BOTH")
    values = {i.name: i.value for i in both.inputs}
    assert values["s"] == "75"
    assert values["stdin"] == "75"


MIXED_FILES_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>

int main() {
    char s;
    klee_make_symbolic(&s, sizeof(s), "s");
    FILE *f = fopen("A", "r");
    int c = f ? fgetc(f) : -1;
    if (s == 'y' && c == 'y') printf("YY");
    else printf("OTHER");
    return 0;
}
"""


async def test_mixed_make_symbolic_and_sym_files_replays_every_path():
    # Same mixed-input bug class through the symbolic-file channel: the replay
    # setup must materialise file "A" in the replay dir or fopen fails and no
    # path can print YY.
    result = await _run(
        MIXED_FILES_SOURCE,
        KleeFlags(max_time=10, max_memory=256, sym_files=SymFiles(count=1, size=1)),
    )
    outputs = {tc.program_output for tc in result.test_cases}
    assert "YY" in outputs
    assert "OTHER" in outputs


SYM_ARGS_SOURCE = """\
#include <stdio.h>

int main(int argc, char **argv) {
    if (argc > 1 && argv[1][0] == 'A') printf("ARG_A");
    else printf("ARG_OTHER");
    return 0;
}
"""


async def test_sym_args_argv_is_reconstructed_at_replay():
    result = await _run(
        SYM_ARGS_SOURCE,
        KleeFlags(
            max_time=10,
            max_memory=256,
            sym_args=SymArgs(count_min=0, count_max=1, length=1),
        ),
    )
    outputs = {tc.program_output for tc in result.test_cases}
    assert "ARG_A" in outputs
    assert "ARG_OTHER" in outputs


ENVP_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>

int main(int argc, char **argv, char **envp) {
    int x;
    klee_make_symbolic(&x, sizeof(x), "x");
    int n = 0;
    while (envp && envp[n]) n++;
    if (x == 0) printf(n > 0 ? "ZERO_ENV" : "ZERO_NOENV");
    else printf(n > 0 ? "OTHER_ENV" : "OTHER_NOENV");
    return 0;
}
"""


async def test_three_argument_main_gets_a_real_envp():
    # The driver must pass environ as main's third argument; a garbage envp
    # crashes the walk (empty output) or walks nonsense (NOENV variants).
    result = await _run(ENVP_SOURCE, KleeFlags(max_time=10, max_memory=256))
    outputs = {tc.program_output for tc in result.test_cases}
    assert outputs == {"ZERO_ENV", "OTHER_ENV"}


INTRINSICS_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>

int main() {
    int r = klee_range(0, 3, "r");
    int i = klee_int("i");
    /* Real if/else, not ternaries: a constant-only ternary compiles to a
       select instruction, which KLEE does not fork on, and the symbolic
       pointer then kills the path at printf under --external-calls=concrete. */
    if (r == 0) {
        if (i > 0) printf("R0_POS");
        else printf("R0_NONPOS");
    } else if (r == 1) {
        if (i > 0) printf("R1_POS");
        else printf("R1_NONPOS");
    } else {
        if (i > 0) printf("R2_POS");
        else printf("R2_NONPOS");
    }
    return 0;
}
"""


async def test_object_consuming_intrinsics_replay_in_order():
    # klee_range and klee_int each consume one ktest object at replay, in
    # creation order; a shifted counter would scramble every value. klee_int is
    # also new capability: the pre-zygote replay could not even link it.
    result = await _run(INTRINSICS_SOURCE, KleeFlags(max_time=10, max_memory=256))
    outputs = {tc.program_output for tc in result.test_cases}
    assert outputs == {
        "R0_POS",
        "R0_NONPOS",
        "R1_POS",
        "R1_NONPOS",
        "R2_POS",
        "R2_NONPOS",
    }


ATEXIT_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>
#include <stdlib.h>

static void bye(void) { printf("|BYE"); }

int main() {
    int x;
    klee_make_symbolic(&x, sizeof(x), "x");
    atexit(bye);
    if (x == 7) printf("SEVEN");
    else printf("OTHER");
    return 0;
}
"""


async def test_atexit_handlers_run_when_main_returns():
    # A returning main must run atexit handlers before the stdio flush (the
    # driver ends the child with exit(), not _exit()). No KLEE suite program
    # exercises this dimension, hence a dedicated guard.
    result = await _run(ATEXIT_SOURCE, KleeFlags(max_time=10, max_memory=256))
    outputs = {tc.program_output for tc in result.test_cases}
    assert outputs == {"SEVEN|BYE", "OTHER|BYE"}


LIBM_SOURCE = """\
#include <klee/klee.h>
#include <math.h>
#include <stdio.h>

int main() {
    int x;
    klee_make_symbolic(&x, sizeof(x), "x");
    /* Fork FIRST with a real branch, then call pow with concrete arguments
       per path; a ternary inside the pow call would hand it a symbolic
       double and kill the path under --external-calls=concrete. */
    if (x == 3) {
        double d = pow(2.0, 3.0);
        if (d > 7.0) printf("CUBE");
        else printf("SMALL");
    } else {
        double d = pow(2.0, 2.0);
        if (d > 3.0) printf("SQUARE");
        else printf("TINY");
    }
    return 0;
}
"""


async def test_libm_programs_get_replay_output():
    # The replay link includes -lm; without it the replay binary fails to build
    # and every path silently loses its output (the pre-zygote behavior).
    result = await _run(LIBM_SOURCE, KleeFlags(max_time=10, max_memory=256))
    outputs = {tc.program_output for tc in result.test_cases}
    assert outputs == {"CUBE", "SQUARE"}


CRASH_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>

int main() {
    char s;
    klee_make_symbolic(&s, sizeof(s), "s");
    if (s == 'X') {
        printf("PRECRASH");
        fflush(stdout);
        volatile int *p = 0;
        *p = 1;
    }
    printf("SAFE");
    return 0;
}
"""


async def test_crashing_path_keeps_its_output_and_batch_survives():
    # Fork isolation: the segfaulting replay dies alone, its flushed output is
    # promoted (a crashed path's prints are that path's real output), and the
    # other paths replay normally.
    result = await _run(CRASH_SOURCE, KleeFlags(max_time=10, max_memory=256))
    outputs = {tc.program_output for tc in result.test_cases}
    assert "PRECRASH" in outputs
    assert "SAFE" in outputs
    crashing = next(tc for tc in result.test_cases if tc.program_output == "PRECRASH")
    assert crashing.error is not None  # KLEE flagged the null write symbolically too


HANG_SOURCE = """\
#include <klee/klee.h>
#include <stdio.h>

int main() {
    char s;
    klee_make_symbolic(&s, sizeof(s), "s");
    if (s == 'H') {
        printf("HUNG");
        fflush(stdout);
        // klee_is_replay() is 0 under KLEE (loop skipped, path completes fast)
        // and 1 in the replay driver (native spin): the hang exists only where
        // the per-child alarm must kill it.
        while (klee_is_replay()) { }
    }
    printf("FINE");
    return 0;
}
"""


async def test_hanging_path_is_killed_by_the_per_test_alarm():
    # The spinning replay burns the 10s KLEE_REPLAY_TIMEOUT alarm and dies; its
    # pre-flush output is promoted, the batch completes, other paths unaffected.
    # max_time=30 so the leftover budget (~28s) outlives the 10s alarm: with a
    # smaller budget the outer timeout group-kills the batch before the alarm
    # fires and the hung path's output is (correctly) never promoted.
    result = await _run(HANG_SOURCE, KleeFlags(max_time=30, max_memory=256), timeout=60)
    outputs = {tc.program_output for tc in result.test_cases}
    assert "HUNG" in outputs  # flushed before the spin, kept despite the kill
    assert "FINE" in outputs
