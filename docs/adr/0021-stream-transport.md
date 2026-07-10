# 0021. Stream transport: source on stdin, output as a tar on stdout

**Status:** Accepted, 2026-07-08

## Context

The runner moved the job in and out through a bind mount. `docker run -v <tmpdir>:/work` wrote `input.c` into a shared host directory, and the host read `/work/output` back after the container exited. That works under runc, but it is the single thing tying the runner to the runc family. A runtime with no shared host directory cannot use it: a microVM without virtio-fs, or a serverless task with no host filesystem at all. Keeping the runner independent of the runtime means dropping the mount.

## Decision

Drop the bind mount. The source enters on the container's stdin, and the whole `/work/output` tree leaves as a tar on stdout. `docker run -i` replaces `-v <tmpdir>:/work`. `--user` goes with it. That flag existed only to make the bind mount writable by the host uid, and with no mount the container runs as the image's own `klee` user. The host extracts the tar into a throwaway directory with tar's `data` filter and parses it as before.

Flags still ride on `-e` environment variables. Every container runtime honours them, so the sandbox axis is covered. A serverless runner is a separate implementation that can pass flags its own way over the same stdin and stdout core.

## Consequences

**Positive**

- The runner image runs unchanged under any runtime without a shared filesystem: runc, gVisor, Kata with Firecracker, or a serverless handler. The stream is the portable contract.
- Removes the bind-mount-under-a-foreign-uid coupling, a standing source of permission friction on CI.

**Negative**

- No mid-run progress. The bind mount let the host poll `/work/output` and stream partial test cases as KLEE found them. With no shared directory there is nothing to poll, so a job shows running, then the whole result at once. ADR-0008 already scoped streaming out, so this realigns the contract rather than regressing it.
- The output tar is buffered whole in memory before extraction. Fine for KLEE's KB-to-low-MB output. A pathological run would need stdout spooled to disk.
- Transport correctness now depends on the container's stdout carrying nothing but the tar. A stray write corrupts the stream. It fails safe, a bad stream raises `KleeRunnerError` and never a wrong result, and every subprocess that could write to stdout is redirected away from it.

## References

- ADR-0009: per-job containers. This supersedes its bind-mount transport. The per-job lifetime stands.
- ADR-0008: KleeRunner protocol surface. Scoped streaming out, which this realigns with.
