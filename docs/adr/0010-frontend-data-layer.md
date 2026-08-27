# 0010. Frontend data layer

**Status:** Accepted, 2026-05-22

> **Amendment, 2026-08-27:** The client now uses the relative `/api` path so the same build works through the Vite proxy and nginx. CI exports the OpenAPI schema from the FastAPI application and compares the committed TypeScript types with newly generated types.

## Context

Stage 1 frontend has to call the backend's `POST /jobs` and `GET /jobs/{id}` endpoints and poll the second until a job reaches a terminal status. The decisions made when wiring that up have downstream cost for the rest of Stage 1 and for Stage 2.

Three risks to avoid:

- **Contract drift.** If the frontend hand-types `JobRequest`, `Job`, `JobResult`, etc., then a backend Pydantic rename can land silently and the frontend keeps compiling against the stale shape.
- **Request boilerplate.** A naive `fetch(...)` + `JSON.stringify(body)` + `res.json() as JobCreated` per route accumulates duplicated infrastructure (base URL, headers, error mapping) and unsafe casts that bypass the type system.
- **Polling logic.** Hand-rolling `setInterval` / `clearInterval` inside `useEffect` for the job-status loop is the kind of code that almost works until tab visibility, race conditions, or React StrictMode double-mounts surface a leak.

Whatever we pick must also be additive into Stage 2. Stage 2 hoists the runner onto Celery workers behind a Redis-backed `JobStore`, but the frontend-facing URLs and JSON shapes do not change. The data layer should not notice the swap.

## Decision

Three tools chosen together as the Stage 1 frontend data stack:

- **`openapi-typescript`** as a dev dependency. Generates `frontend/src/types/api.ts` from the backend's live `/openapi.json`. Regenerated via `npm run gen:types`. The generated file is committed, so editors, PR reviewers, and CI all see the contract.
- **`openapi-fetch`** as the HTTP client. Created once in `src/api/client.ts` as `createClient<paths>({ baseUrl: "http://localhost:8000" })`, where `paths` is the generated type. Routes, methods, request bodies, and responses are type-checked against the OpenAPI schema at compile time. Route-specific wrappers (`submitJob`, `getJob`) live in `src/api/jobs.ts`.
- **`@tanstack/react-query`** for data-fetching state. `useMutation` wraps `submitJob` (job submission, no caching wanted). `useQuery` wraps `getJob` with `refetchInterval` that inspects the latest `data.status` and stops returning a ms value when it sees `done` or `failed`. The hooks live in `src/hooks/`.

Base URL is hardcoded to `http://localhost:8000`. Env-var indirection is deferred; single-constant configurability is a one-line change later, not a rewrite.

## Consequences

**Positive**

- Compile-time contract enforcement against the backend. Renaming a field on a Pydantic model, regenerating, and rebuilding the frontend surfaces every disagreeing consumer as a TS error. Silent contract drift becomes impossible.
- `src/api/client.ts` is one significant line of code; `src/api/jobs.ts` is two thin function wrappers. The verbose request-building and response-typing boilerplate lives inside `openapi-fetch`, not in our codebase.
- Polling is declarative. `refetchInterval` accepts a function of the latest query state and returns a ms number or `false`. No manual `setInterval` / `clearInterval` / `useEffect` cleanup; React Query also pauses polling automatically when the tab is hidden.
- Stage 2's Celery transition does not touch this layer. The endpoints and JSON shapes are unchanged, so `client.ts`, `jobs.ts`, and the hooks survive verbatim.

**Negative**

- Three deps to track (`openapi-fetch`, `@tanstack/react-query`, `openapi-typescript`). All small and active, but each is a future maintenance surface.
- `openapi-typescript@7.13` declares `typescript: ^5.x` as a peer dep, which conflicts with our TS 6. Resolved with `frontend/.npmrc` setting `legacy-peer-deps=true`. Peer dep is advisory and the tool only emits `.d.ts` text, so the workaround is safe, but it is a contributor-facing wart that lasts until `openapi-typescript` ships a release with an updated peer range.
- `npm run gen:types` is build-time tooling only: the committed `api.ts` ships in the Vite bundle, so production never depends on `/openapi.json` and the endpoint can stay closed there. The constraint only bites at type-regeneration time, when the script needs the backend reachable on `localhost:8000`. CI can keep the committed file in sync either by consuming a static `openapi.json` artefact emitted by backend CI, or by spinning up a backend container for the duration of the check; neither blocks deployment.
- The `openapi-fetch` discriminated-union return shape (`{ data, error }`) is converted to "return data, throw on error" inside `jobs.ts` so React Query consumes it as a standard throwing function. This is a small idiom translation that future readers need to recognise.

## References

- ADR-0006: Frontend tooling stack (Vite + React + TS + Tailwind; this ADR builds on it).
- ADR-0007: POST /jobs returns JobCreated, not full Job (the contract this layer consumes).
- `frontend/src/types/api.ts` (generated).
- `frontend/src/api/client.ts`, `frontend/src/api/jobs.ts`.
- `frontend/src/hooks/useSubmitJob.ts`, `frontend/src/hooks/useJob.ts`.
- `frontend/src/main.tsx` (the `QueryClientProvider` wrapping `<App />`).
