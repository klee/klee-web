# runner/

Docker image and entrypoint that actually runs KLEE on user-submitted C code. Top-level sibling of `backend/` deliberately: in Stage 2 this is what lives on separate worker VMs, and the separation stops backend code from accidentally reaching into runner internals.

## Contents

- `Dockerfile`: pinned `klee/klee:v3.2` base, builds the sleep-neutralising preload and the prebuilt replay objects, copies in the entrypoint, sets the working user
- `entrypoint.py`: reads C source from stdin, compiles it to LLVM bitcode with clang, runs KLEE with bounded flags (including `--kdalloc=false`, ADR-0022), replays each test case through the zygote driver for per-path output, and streams the output directory back as a tar on stdout (ADR-0021; no shared filesystem with the host)
- `replay_driver.c`: fork-per-ktest replay zygote (ADR-0022). Linked once per job with the user's program and KLEE's own replay-setup objects, then forked per test case, so replay pays no per-test process creation or dynamic linking
- `replay_nosleep.c`: `LD_PRELOAD` stub that no-ops sleeps during replay (ADR-0020)

The Worker selects this image through `RUNNER_IMAGE`, which defaults to the locally built `klee-web-runner` name and also accepts a registry tag or digest. Docker caches one image on each Worker host and creates a fresh container from it for every Job.

## Why a separate container per job, not a long-lived process

Per-job containers give cgroup isolation, fixed CPU, memory, swap, and PID Caps, a read-only root, bounded temporary storage on `/work`, and automatic cleanup through Docker's `--rm` flag. A long-lived KLEE process accumulates state: leaked fds, fragmented memory, half-cleaned tmp dirs. Per-job means every run starts from a known clean state. See `../docs/adr/0008-kleerunner-protocol-surface.md` and `../docs/adr/0009-per-job-containers.md`.

## Known working invocation (reference)

- `clang -I /home/klee/klee_src/include -emit-llvm -c -g -O0 input.c -o code.bc`
- `klee --libc=uclibc --posix-runtime --external-calls=concrete --kdalloc=false --max-time=60 --max-memory=512 --output-dir=/tmp/klee-out code.bc`

The backend may add `--write-kqueries`, allowlisted extra flags, and structured POSIX arguments. The output directory contains KLEE's `messages.txt`, `warnings.txt`, `info`, `*.ktest`, optional `*.err`, and `run.stats` (SQLite3 in KLEE 3.x). The entrypoint adds whole-run `program_output.txt`, an optional `host_timeout` marker, and optional per-path `*.stdout` files from replay. KQuery output adds `*.kquery` path constraints. On compile failure the entrypoint writes `compile_error.txt` instead and exits 0. The backend distinguishes a user compile failure from a Runner crash through that file.
