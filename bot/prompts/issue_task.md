# Issue Agent Task

You are working inside the `klee-web` repository.

## Project Context

KLEE Web is a browser-accessible interface for the KLEE symbolic execution
engine. Its purpose is to remove the local setup barrier around LLVM, STP, KLEE,
and related dependencies: users write C in the browser and receive generated
test cases back from KLEE.

The project is in Stage 3, hardening and portability:

- `frontend/`: React, TypeScript, Vite, Monaco editor, and the results UI.
- `backend/`: FastAPI and Pydantic API for job submission, status, cancellation,
  and result retrieval.
- Redis: Job state, result cache, usage counters, and Celery broker.
- Celery Workers: consume Jobs and launch per-Job Runner containers.
- `runner/`: Docker image and entrypoint that invokes KLEE under gVisor.
- nginx: TLS edge, built frontend, API proxy, rate limits, and admin auth.
- `docs/adr/`: architecture decisions that should guide non-trivial changes.
- `Makefile`: dependency install, credential, deployment, logs, and teardown.

The full application has one Compose topology (ADR-0024). On a clean checkout,
`make admin-password` creates the required local credential. `make deploy`
starts the stack detached, `make logs` follows it, and `make down` stops it.
The app is at `https://localhost`. The backend OpenAPI docs are at
`https://localhost/api/docs` and directly at `http://localhost:8000/docs`.

The frontend flow is end-to-end: a Monaco editor starts with demo C code, the
top bar exposes KLEE flags such as `max_time` and `max_memory`, Run submits to
the backend, and the results panel polls job status. Important visible states
include pending, running with live stats, done with test cases, compile errors,
timeouts, and cancellation.

Backend models emit the OpenAPI contract. If a backend change alters endpoint
paths, request models, response models, or field names, regenerate and commit
the frontend API types:

```bash
cd frontend && npm run gen:types
```

That command requires the backend to be running because it reads
`http://localhost:8000/openapi.json`.

Your job is to make the smallest complete change that resolves the GitHub issue
below. Keep the implementation aligned with the existing project structure:
FastAPI backend code in `backend/`, React and Vite frontend code in `frontend/`,
the KLEE container runner in `runner/`, and architecture notes in `docs/adr/`.

Before changing code, inspect the relevant files and understand the current
patterns. Do not rewrite unrelated code. If the issue is ambiguous or unsafe to
complete, stop and explain the blocker instead of guessing.

Prefer the established stack and conventions:

- Python changes should fit the existing FastAPI/Pydantic style.
- Frontend changes should fit the existing React component and hook structure.
- Production uses Redis and Celery implementations only. Deterministic fakes
  belong under `backend/tests/` and are injected directly.
- Runner changes should preserve the Docker/KLEE boundary unless the issue
  explicitly asks for runner behavior.
- User-facing changes should keep the app usable for someone who may not know
  KLEE internals.
- Security-sensitive changes should remember that submitted C code is untrusted.

When you finish, leave the worktree with only the files needed for the issue.
The dispatcher script will run verification, commit the changes, push the branch,
and open a draft pull request.
