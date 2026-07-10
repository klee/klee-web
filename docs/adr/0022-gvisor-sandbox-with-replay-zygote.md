# 0022. Stage 3 sandbox: gVisor with a fork-per-ktest replay zygote

**Status:** Accepted, 2026-07-09

## Context

Stage 3 sandboxes the runner, which executes untrusted C. KLEE runs the code symbolically, and per-path replay (ADR-0020) runs it natively once per test case, so attacker-influenced native code runs on both paths. The sandbox has to hold. The choice is constrained by three things at once: isolation strength, performance, and how much each deployment target must provide. That last one is the portability question the thesis is trying to answer, so a sandbox that needs a lot of per-machine setup is a worse answer even when it is faster.

Two families were on the table. gVisor (`runsc`) is a userspace kernel that intercepts the container's syscalls. A microVM (Kata, with either QEMU or Firecracker) is a real lightweight VM per job.

## Decision

Use gVisor as the single runtime, plus a replay zygote, plus KLEE's deterministic allocator turned off.

- **Runtime.** `--runtime=runsc`. The `systrap` platform is the default and needs no KVM, so it runs on any Linux host. Where `/dev/kvm` exists, the `kvm` platform is a one-flag change on the same binary, chosen by probing for the device at deploy time.
- **Allocator.** `--kdalloc=false`. KLEE's default deterministic allocator aborts on a fatal `madvise` under gVisor, and under a VM guest built without transparent huge pages. Correctness is unaffected: the same tests and bugs are found. Only KLEE-internal pointer addresses stop being reproducible, which does not matter here.
- **Replay.** A fork-per-ktest zygote (`runner/replay_driver.c`) replaces the per-test `klee-replay` process. The user's program (its `main` renamed at compile time) links once with KLEE's own replay-setup objects and a shared in-order ktest reader, then forks per test case: no exec and no dynamic linking per test. Each child re-creates the recorded POSIX environment (stdin, files, argv) exactly as `klee-replay` would, redirects its stdout to that path's output file, and calls the renamed `main`. The shared reader also fixes a latent bug: programs mixing `klee_make_symbolic` with POSIX symbolic input replayed empty under `klee-replay`, whose runtime library checks object names against a counter that restarts in every process. A per-child alarm bounds a hanging path, and fork isolation contains a crashing one.

gVisor is chosen over the microVM for portability. gVisor-systrap runs where there is no KVM, which a VM cannot, and the KVM platform is one flag where the hardware allows. A microVM is marginally faster on a KVM host, but it needs the whole VM stack (a block or shared-filesystem device, a guest image, an in-guest agent) provisioned per machine, which is the larger redeploy delta the portability question is trying to shrink. Firecracker in particular was rejected: it has no shared filesystem, it dropped bulk output over its vsock in testing, and it was not faster than QEMU under Kata.

The zygote is what makes gVisor viable rather than merely possible. gVisor taxes process creation and syscalls, and the naive replay spawns a fresh dynamically-linked process per test case. On a path-heavy program that turns a few seconds of work into tens of seconds. The zygote removes the per-test process and link cost, so replay under the sandbox drops from tens of seconds to a few, and the end-to-end run sits near native.

## Consequences

**Positive**

- Runs on any modern Linux with KVM optional. The redeploy delta is a `runsc` install and one platform flag, with no VM stack to stand up.
- Near native with the zygote. On a path-explosion stress program the end-to-end run measured about 1.4x native with the KVM platform and about 2x without. Typical programs are near native on either platform, since the replay cost that separates them only shows under path explosion.
- The zygote is pure userspace code with no host dependency, so it is infrastructure-independent and improves every runtime, not only gVisor.

**Negative**

- gVisor's userspace kernel is weaker isolation than a real VM. Accepted as more than adequate for this tool, and the thing it replaces was no per-job sandbox at all.
- A residual overhead stays in the KLEE phase itself, about 1.3x with KVM to 1.75x without, because KLEE writes one file per path and each write is a trapped syscall. The zygote cannot remove this. It is inherent to KLEE's IO under a userspace kernel.
- `--kdalloc=false` gives up KDAlloc's reproducible addresses and its use-after-free quarantine. Neither is used here, and the original klee-web never ran KDAlloc, so this returns the project to where the reference ran for years.
- The zygote is our replay code to maintain: a driver whose intrinsic stubs mirror what KLEE's replay tooling provides, linked with KLEE setup sources compiled from the image. A KLEE upgrade can shift that contract, so a differential run of KLEE's own test suite against the driver is the standing regression gate.

## References

- ADR-0009: per-job containers. This specifies the sandbox that ADR assumed.
- ADR-0020: native per-path replay. This optimizes its replay mechanism, and corrects its note that Stage 3 runs it under gVisor with no change.
- ADR-0021: stream transport. Retained. Its runtime-agnostic contract is what lets the sandbox be a runtime flag rather than a code change.
