# 0023. Bounded tmpfs for Runner storage

**Status:** Accepted, 2026-07-16

## Context

Each Runner writes source, bitcode, KLEE output, replay binaries, and replay output. Leaving the container layer writable lets one Job consume unbounded Worker disk. Docker writable-layer quotas depend on the host storage driver, while a quota-backed bind mount would restore the host-path coupling removed by ADR-0021.

The shipped examples use less than 30 MiB of tar output. A 65,536-path KQuery stress run creates about 196,000 files and needs more than 512 MiB of tmpfs once filesystem metadata is counted.

## Decision

Run each container with a read-only root and one executable tmpfs at `/work`. The deployment-owned `RUNNER_STORAGE_MB` setting controls its size and defaults to 768 MiB. The mount is owned by the image's `klee` user. Compiler temporaries and the replay helper's per-test directories also live under `/work`.

Do not claim a separate inode Cap. The tested runc path honors the tmpfs inode option, but runsc does not.

This is the storage mechanism for VM-based `DockerKleeRunner` deployments. The planned serverless trial keeps the Worker and Runner on a VM. A future task-per-Job implementation must map the same bounded-storage requirement onto provider storage because AWS Fargate does not support tmpfs mounts.

## Consequences

**Positive**

- One Docker mount works under runc and gVisor without host filesystem setup.
- A Job cannot consume unbounded Worker disk, and removing the container removes its writable data.
- The default supports every shipped example and the 65,536-path stress run.

**Negative**

- Tmpfs usage counts toward the Runner's hard-memory Cap. A Job can reach OOM before `ENOSPC` when memory and storage pressure coincide.
- Filling `/work` can fail the Job abruptly. Results are not guaranteed after `ENOSPC`.
- `/work` must allow execution because the per-Job replay binary is linked and run there.

## References

- ADR-0009: per-job containers. The storage boundary shares their lifetime and cleanup.
- ADR-0021: stream transport. No host bind mount is reintroduced.
- ADR-0022: gVisor sandbox. The same mount works under the selected runtime.
