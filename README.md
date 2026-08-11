# KLEE Web

[![CI](https://github.com/FinnLeh/klee-web/actions/workflows/ci.yml/badge.svg)](https://github.com/FinnLeh/klee-web/actions/workflows/ci.yml)

Browser-accessible interface for the [KLEE](https://klee.llvm.org/) symbolic execution engine. MSc thesis project, Imperial College London, supervised by Prof. Cristian Cadar.

## Goal

KLEE today requires users to build LLVM, STP, and a chain of other dependencies before running a single test. Many give up. KLEE Web removes that barrier: write C in a browser, get test cases back.

## Current stage

**Stage 3: hardening and portability.** Stages 1 and 2 are done: the synchronous monolith (React frontend, FastAPI backend, Docker runner), then the split (Celery workers, a Redis broker and result cache, a worker pool). Stage 3 adds the production edge (nginx, TLS, rate limiting), stronger sandboxing (gVisor), observability, and an admin UI. The edge, the gVisor sandbox, fleet telemetry, usage statistics, and authenticated per-Worker capacity control are already in place. It also answers the thesis portability question: redeploy the stack across providers and count what has to change.

The whole stack runs locally through the same Compose topology used for deployment. `make deploy` starts nginx, the API, Redis, and the Celery Worker fleet. `make logs` follows them, and `make down` stops them.

## Layout

```
klee-web/
├── backend/        FastAPI + Pydantic. Job submission, status, result API.
├── frontend/       React + TypeScript + Vite. Editor and results UI.
├── runner/         Docker image and entrypoint that actually runs KLEE.
├── bot/            Label-gated issue agent automation (see below).
├── deploy/         Provider-neutral VM bootstrap and service lifecycle.
├── infra/          Provider-specific infrastructure roots.
├── docs/           architecture.md overview, and the ADRs in docs/adr/.
└── Makefile        install, credential, Runner build, deployment, logs, and teardown commands.
```

## Running locally

The full stack requires Docker with Compose, GNU Make, and a registered gVisor runtime (`runsc`, plus `runsc-kvm` where `/dev/kvm` is available). The explicit macOS runc exception described below applies only to the isolated local E2E launcher. Host-side development checks additionally use [`uv`](https://docs.astral.sh/uv/) and [`node`](https://nodejs.org/).

Install the project dependencies once after cloning:

```bash
make install
```

This runs `uv sync` for the backend and `npm install` for the frontend. It also installs the git hooks if `pre-commit` is on your PATH (see Pre-commit hooks below). Create the local admin credential once, then start the stack:

```bash
make admin-password
make deploy
```

`make deploy` builds the Runner, backend, and frontend images, starts the Compose services in detached mode, waits until every service is running and the defined Redis and API health checks pass, then returns control to the terminal. It selects `runsc-kvm` when `/dev/kvm` exists and `runsc` otherwise.

The local defaults name these images `klee-web-runner`, `klee-web-backend`, and `klee-web-frontend`. After building the Runner, `make deploy` resolves `klee-web-runner` to its content-addressed `sha256:...` image ID and supplies that value to the API and Worker, so a changed local Runner cannot reuse stale cache entries. Registry tags locate publications but are not runtime identities. Registry-backed deployment tooling supplies immutable `RUNNER_IMAGE`, `BACKEND_IMAGE`, and `FRONTEND_IMAGE` digests, pulls those references, and starts the same Compose file with `--no-build`.

`.klee-version` is the single KLEE version lever. It selects the Runner base image and is baked into the backend result metadata and frontend status bar. It is a build input, not per-host deployment configuration. Result-cache keys combine the complete submission, exact Runner image identity, and `JobResult` schema. Job records and cached results expire after 48 hours. Reads do not refresh either TTL.

After all six checks pass in a `main` CI run, CI calls the reusable `Publish images` workflow. It builds `linux/amd64` frontend, backend, and Runner images under `ghcr.io/finnleh/`. Each image receives an immutable `sha-<full-commit>` tag and a GitHub/Sigstore-signed provenance attestation. Once all three exist, the workflow updates their moving `main` tags sequentially. Publishing a stable GitHub Release first verifies all three attestations, then adds its `vMAJOR.MINOR.PATCH` tag to that commit's existing images without rebuilding them. There is no `latest` tag. The packages are public.

The self-signed local certificate produces a browser warning. App at <https://localhost>. OpenAPI surface at <https://localhost/api/docs>.

The frontend is functional end-to-end. The page loads with a demo C program in
a Monaco editor with C autocomplete for KLEE intrinsics. A collapsible left
sidebar offers bundled example programs and a per-browser run history. The top
bar carries the KLEE wordmark, inline flag inputs for time and memory, a
path-constraint selector (off or KQuery), a free-text extra-flags box validated
against an allowlist, a settings cog, and a Run button that becomes a Cancel
button while a job is in flight. A collapsible panel below the bar toggles
KLEE's POSIX-runtime symbolic input (symbolic stdin, args, and files). Run
posts to the backend and the results panel polls and renders pending, running
(with elapsed time against the submitted limit), parsing, done (test cases plus program-output, messages, and
warnings collapsibles), and compile-error states. Each test case's symbolic
inputs can be re-decoded per variable through a type dropdown. A timeout reads
as an amber `Stopped at max time` badge under the tab bar, a user cancel reads
`Cancelled by user`, and a clean run reads `Explored all paths`. The bottom
status bar shows a backend-connected indicator (5 s poll of `/health`),
the current source byte count, and the pinned KLEE version. Theme (system /
light / dark) and results-position (right / below) settings persist across
reloads via the settings popover.

The Basic Auth-protected `/admin` route shows fleet telemetry and cumulative usage, and changes each Worker's live autoscaler maximum within the deployment bound.

### Local deployment controls

The deployment starts one Worker by default. Replica count and each Worker's autoscaler ceiling are independent controls:

```bash
make deploy WORKER_REPLICAS=2 WORKER_CONCURRENCY_MAX=4
make logs
make down
```

With two replicas and a maximum of four processes per Worker, at most eight Runner containers execute concurrently. `make logs` follows all services. `Ctrl+C` stops following logs but leaves the deployment running. `make down` explicitly tears it down while preserving the Redis named volume.

`make admin-password` prompts without displaying the password. It protects the
ignored credential with a mode `0700` parent directory, while the mode `0644`
file remains readable inside nginx's isolated, read-only secret mount. The
username is `admin`. Run the target again to rotate the credential. The
`make deploy` fails if the file is absent.

nginx serves the built frontend and reverse-proxies `/api` over TLS on a single
origin, Redis persists to a named volume (AOF, bounded by `maxmemory` with `volatile-lru`
eviction), and the worker spawns each KLEE job as a sibling container under the
selected gVisor runtime (`runsc` or `runsc-kvm`). See
[`docs/architecture.md`](docs/architecture.md) for the deployment shape.

## Deploying to a VM

`deploy/` defines the provider-neutral host lifecycle. A provider root renders
the shared Compose files, exact image references, bootstrap scripts, and
systemd unit into cloud-init. A missing `DEPLOYMENT_ROLE` retains the complete
single-VM topology. The `web` role owns nginx, FastAPI, Redis, TLS, and the
administrator credential. The `worker` role owns one Celery Worker, its local
Docker daemon, gVisor, and transient Runner containers. Every host installs
Docker. Only execution hosts install and probe gVisor.

`infra/aws/` and `infra/azure/` are independent single-VM provider roots. Each
provisions one provider network and VM around the shared lifecycle while
retaining its own TLS adapter. The independent `infra/aws-multi-vm/` root
provisions one public web/state VM and one or two private Worker VMs. See the
[single-VM AWS guide](docs/deployment/aws.md),
[role-separated AWS guide](docs/deployment/aws-multi-vm.md), and
[Azure deployment guide](docs/deployment/azure.md) for planning, activation,
operation, rollback, and teardown. Use the shared
[host-maintenance procedure](docs/deployment/host-maintenance.md) for controlled
Ubuntu security updates.

## Regenerating the API contract

The backend emits its OpenAPI spec from the Pydantic models. The frontend's
TypeScript types live in `frontend/src/types/api.ts`, generated from that spec
and committed to the repo. They do not regenerate on their own.

After any backend change that alters the contract (a renamed field, a new
endpoint, a changed shape), regenerate the types:

```bash
cd frontend && npm run gen:types
```

The script reads the live `/openapi.json`, so the Compose backend must already be running through `make deploy`. Commit the updated
`api.ts` alongside the backend change. A stale `api.ts` surfaces as a frontend
type error against the new contract, which is the point: drift fails at compile
time instead of silently.

## Pre-commit hooks

`pre-commit` is a global tool. Install it once on your machine:

```bash
uv tool install pre-commit
```

`make install` then wires the git hooks for you, both the commit-stage and the
pre-push hook. If you installed `pre-commit` after running `make install`, wire
them yourself:

```bash
pre-commit install --hook-type pre-commit --hook-type pre-push
```

On `git commit`, the commit-stage hooks run ruff (backend), eslint (frontend), actionlint (GitHub Actions), and whitespace / end-of-file checks. The eslint hook needs `frontend/node_modules`, so run `npm install` in `frontend/` once before the first commit. CI runs the pre-commit hooks across all files and runs mypy separately in the backend job, so the same checks are enforced on every pull request even if you never install the local hooks.

On `git push`, the pre-push hook runs Playwright through an isolated Compose stack and a real KLEE container under gVisor, but only when the push touches `frontend/`, `backend/`, or `runner/`. It needs Docker, a registered gVisor runtime, and free ports 80 and 443. The hook builds its images, creates a temporary admin credential, and tears the stack down afterward. To skip it in a pinch, push with `--no-verify`.

gVisor does not support macOS. A macOS contributor can explicitly allow Docker's default `runc` runtime for the local E2E launcher:

```bash
KLEE_E2E_ALLOW_RUNC=1 npm run test:e2e
KLEE_E2E_ALLOW_RUNC=1 git push
```

Without that opt-in, the launcher stops before starting containers. It prints a warning when runc is enabled because this mode lacks gVisor's additional isolation. Use it only with trusted checked-out code and test inputs. Linux hosts, including CI, reject this exception and continue to require `runsc` or `runsc-kvm`.

The pre-push hook is local and optional. Without it, or with `--no-verify`, the push still succeeds. The same test runs as a required CI check on the pull request, so a broken contract cannot be merged either way. The hook just gives faster, real-KLEE feedback before you push.

## Issue agent automation

The repository includes a label-gated issue agent workflow. After configuring
the repository variables and secrets described in `bot/README.md`, add
`agent:ready` to a reviewed issue to let the workflow create an agent branch,
run the configured coding agent, verify the result, and open a draft pull
request. Use the `Agent task` issue template for issues intended for automation.

## Design

[`docs/architecture.md`](docs/architecture.md) is the overview: how the frontend, backend, runner, broker, and store fit together. The ADRs in `docs/adr/` record why each decision was made, one per major choice.
