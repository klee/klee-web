# 0011. Frontend layered architecture

**Status:** Accepted, 2026-05-27

> **Amendment, 2026-08-27:** The workspace still uses the layers below. The later administration page is a separate route and calls `api/admin.ts` through React Query directly at page level.

## Context

ADR-0010 chose the three dependencies that form the frontend data stack: `openapi-typescript`, `openapi-fetch`, and `@tanstack/react-query`. This ADR records how the code that uses them is organised across `src/api/`, `src/hooks/`, `src/context/`, and `src/components/`.

Without a fixed convention, components end up calling `fetch` directly inside `onClick` handlers. The contract enforcement from the generated types gets bypassed, and rendering code gets tangled with network code.

Stage 1's visual layer is now in place. The components that consume the data layer (`Editor`, `Results`, `StatusBar`, `SettingsPopover`, `TopBar`, `FlagBar`) all follow a consistent stacking pattern: each only depends on the layer immediately below it. Recording that convention now keeps Stage 2's additions (worker progress, queue position, a possible job history view) on the same layout.

## Decision

Four layers, stacked bottom-up. Each layer depends only on the layer directly below it. A component reaching past hooks into `api/jobs.ts`, or a hook importing a component, are both signs that something is in the wrong place.

1. **Types.** `src/types/api.ts`, generated from the backend's OpenAPI spec via `openapi-typescript` (ADR-0010). Committed. Every downstream consumer reads from this file, directly or transitively. The shape of a `JobResult` or `JobCreated` never gets hand-typed.
2. **API client.** `src/api/client.ts` holds one typed `apiClient` over `openapi-fetch` plus an exported `BASE_URL`. `src/api/jobs.ts` holds the route wrappers (`submitJob`, `getJob`) and schema-alias re-exports (`Job`, `JobResult`, `KleeFlags`, `HaltReason`, and similar). Components never import `apiClient` directly. They import the wrappers and the re-exports.
3. **Hooks.** `src/hooks/useSubmitJob.ts` and `src/hooks/useJob.ts` wrap the route functions with React Query. These hooks are the only consumers of `src/api/jobs.ts`. New routes get one wrapper function in `jobs.ts` and one hook here, not a component rewrite.
4. **Components.** `src/components/*` consume hooks. No `fetch`, no URLs, no headers, no React Query primitives are visible from this layer. State that must span components (`source`, `flags`, `jobId`) lives in the page component (`src/pages/HomePage.tsx`). Cross-cutting client state (theme, layout) lives in `src/context/SettingsContext.tsx`.

## Consequences

**Positive**

- Components are network-free. `Results.tsx` calls `useJob(jobId)` and dispatches on `job.status`. It has no idea that polling exists or what URL serves the job. Swapping in a fake hook for a component smoke is a one-line change.
- Type-binding propagates upward without manual restating. `submitJob` returns `JobCreated` because the OpenAPI schema says so. `useSubmitJob`'s mutate callback is inferred from `submitJob`'s signature. The `onSuccess` callback in `HomePage` knows `data.job_id` is a string because the chain is intact end to end.
- New API additions are a single function in `jobs.ts` plus one hook, never a deeper change. The recent `halt_reason` field needed only a re-export in `api/jobs.ts` and consumption in `Results.tsx`. The client and hook layers were untouched.
- Stage 2's Celery swap stays below the API client layer. The endpoints and JSON shapes do not change, so hooks, components, and pages keep working.

**Negative**

- A Run click traverses five files before hitting `fetch`: `TopBar` (onRun prop), `HomePage` (handleRun calls `submitMutation.mutate`), `useSubmitJob` (React Query), `submitJob` in `api/jobs.ts`, `apiClient.POST` in `api/client.ts`, then `openapi-fetch` to `fetch`. New contributors have to learn the traversal once. The layered shape is more files than a hand-rolled implementation would need for the same endpoint count. The cost is consistency and traceability, not complexity, but the indirection is real.
- Page-level state lifting threads props down to slot components. `flags` lives on `HomePage` but is read by `FlagBar` (rendered inside `TopBar`). `jobId` lives on `HomePage` but is read by `Results`. Three pieces of state on the page is comfortable. A dozen would be the point to reach for a reducer or a per-page context, and that refactor is a real future cost.
- Schema-alias re-exports in `api/jobs.ts` are a small redundancy: components could import directly from `types/api.ts`. Routing them through `jobs.ts` keeps the import surface narrow (components touch one file in `api/`, not two), but a future reader has to learn the convention to know where types come from.

## References

- ADR-0006: Frontend tooling stack.
- ADR-0010: Frontend data layer (this ADR builds on it).
- `frontend/src/types/api.ts` (Types).
- `frontend/src/api/client.ts`, `frontend/src/api/jobs.ts` (API client).
- `frontend/src/hooks/useSubmitJob.ts`, `frontend/src/hooks/useJob.ts` (Hooks).
- `frontend/src/components/Editor.tsx`, `frontend/src/components/Results.tsx`, `frontend/src/components/TopBar.tsx`, `frontend/src/components/SettingsPopover.tsx`, `frontend/src/components/StatusBar.tsx` (Components).
- `frontend/src/pages/HomePage.tsx`, `frontend/src/context/SettingsContext.tsx` (page-level and cross-cutting state).
