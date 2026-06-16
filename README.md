# KLEE Web

[![CI](https://github.com/FinnLeh/klee-web/actions/workflows/ci.yml/badge.svg)](https://github.com/FinnLeh/klee-web/actions/workflows/ci.yml)

Browser-accessible interface for the [KLEE](https://klee.llvm.org/) symbolic execution engine. MSc thesis project, Imperial College London, supervised by Prof. Cristian Cadar.

## Goal

KLEE today requires users to build LLVM, STP, and a chain of other dependencies before running a single test. Many give up. KLEE Web removes that barrier: write C in a browser, get test cases back.

## Current stage

**Stage 1: synchronous monolith.** React frontend, FastAPI backend, Docker runner. No queue, no cache. Runs locally via the steps below. Target: end of May 2026.

Stages 2 (Celery + Redis + cache) and 3 (nginx + gVisor + admin UI) follow over the summer.

## Layout

```
klee-web/
├── backend/        FastAPI + Pydantic. Job submission, status, result API.
├── frontend/       React + TypeScript + Vite. Editor and results UI.
├── runner/         Docker image and entrypoint that actually runs KLEE.
├── docs/adr/       Architecture Decision Records.
└── Makefile        `make up` builds the runner image and runs backend + frontend dev servers.
```

## Running locally

Requires [`uv`](https://docs.astral.sh/uv/) and [`node`](https://nodejs.org/)
on the host. `uv` runs and provisions the Python backend; `node` (with its
bundled `npm`) provides the frontend toolchain, Vite included.

Install the project dependencies once after cloning:

```bash
make install
```

This runs `uv sync` for the backend and `npm install` for the frontend (the
latter is what puts Vite in `frontend/node_modules`). It also installs the git
hooks if `pre-commit` is on your PATH (see Pre-commit hooks below). Then start
both dev servers:

```bash
make up
```

`make up` builds the `klee-web-runner` Docker image (idempotent), then starts
uvicorn (`localhost:8000`, `--reload`) and the Vite dev server
(`localhost:5173`) as background processes. Both hot-reload on file changes.
Ctrl+C stops both.

OpenAPI surface at <http://localhost:8000/docs>. App at <http://localhost:5173>.

The frontend is functional end-to-end. The page loads with a demo C program in
a Monaco editor; the top bar carries the KLEE wordmark, inline flag inputs for
`max_time` and `max_memory`, a Run button, and a settings cog. Run posts to the
backend and the results panel polls and renders pending, running (with a
curated live-stats grid: instructions, active states, full branches, wall
time), done (test cases plus a KLEE messages and warnings collapsible), and
compile-error states. A timeout reads as an amber `Stopped at max time` badge
under the tab bar; a clean run reads `Explored all paths`. The bottom status
bar shows a backend-connected indicator (5 s poll of `/openapi.json`), the
current source byte count, and the pinned KLEE version. Theme (system / light /
dark) and results-position (right / below) settings persist across reloads via
the settings popover.

## Regenerating the API contract

The backend emits its OpenAPI spec from the Pydantic models. The frontend's
TypeScript types live in `frontend/src/types/api.ts`, generated from that spec
and committed to the repo. They do not regenerate on their own.

After any backend change that alters the contract (a renamed field, a new
endpoint, a changed shape), regenerate the types:

```bash
cd frontend && npm run gen:types
```

The script reads the live `/openapi.json`, so the backend must already be
running (`make up`, or uvicorn on `localhost:8000`). Commit the updated
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

On `git commit`, the commit-stage hooks run ruff (backend), eslint (frontend), and whitespace / end-of-file checks. The eslint hook needs `frontend/node_modules`, so run `npm install` in `frontend/` once before the first commit. CI runs these same hooks (`pre-commit run --all-files`), so they are enforced on every pull request even if you never install the local hooks.

On `git push`, the pre-push hook runs the Playwright e2e against the real KLEE container, but only when the push touches `frontend/`, `backend/`, or `runner/`. It needs Docker and the `klee-web-runner` image (`make runner` builds it). To skip it in a pinch, push with `--no-verify`.

The pre-push hook is local and optional. Without it, or with `--no-verify`, the push still succeeds. The same test runs as a required CI check on the pull request, so a broken contract cannot be merged either way. The hook just gives faster, real-KLEE feedback before you push.

## Design

Architecture is documented in `docs/adr/`, one ADR per major decision.
