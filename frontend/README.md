# frontend/

React + TypeScript single-page app. Editor for C source, an examples/history sidebar, a results pane, and an authenticated fleet-administration route.

## Contents

- `package.json`: React 19, TypeScript, Vite, Tailwind v4, React Query, React Router, Monaco editor, openapi-fetch, openapi-typescript
- `.npmrc`: `legacy-peer-deps=true` so clones do not trip on openapi-typescript's stale `typescript: ^5.x` peer-dep range while we are on TS 6
- `vite.config.ts`: build / dev server config, required KLEE version injection, plus the Vitest `test` block scoped to `src/**/*.test.ts`
- `Dockerfile`: Node 24 build stage requiring the KLEE version build argument sourced from the repository's `.klee-version`, followed by the nginx image that serves the compiled SPA
- `nginx.conf`: HTTPS edge, static assets, `/api` proxy, rate limits, and Basic Auth for `/admin` and `/api/admin/*`
- `playwright.config.ts` and `e2e/`: browser tests against an isolated Compose stack, using the real gVisor Runner path on Linux and Docker's default `runc` runtime on macOS
- `tsconfig.json`: strict TypeScript
- `index.html`: entry HTML
- `src/main.tsx`: React mount point, wraps `<App />` in `QueryClientProvider`
- `src/App.tsx`: route index inside `SettingsProvider` and `BrowserRouter`, with the workspace at `/` and fleet administration at `/admin`
- `src/api/client.ts`: typed `apiClient` over openapi-fetch. Also exports `BASE_URL` for callers that need the backend origin outside the typed routes (e.g., the status bar pinging `/health`)
- `src/api/jobs.ts`: `submitJob`, `getJob`, `cancelJob`, the `JobNotFoundError` and `RequestFailedError` error types, and re-exported schema aliases
- `src/api/admin.ts`: typed fleet telemetry, usage-statistics, and Worker-capacity calls used by the admin route
- `src/types/api.ts`: types generated from the backend OpenAPI spec, committed
- `src/hooks/useSubmitJob.ts`: React Query mutation over `submitJob`
- `src/hooks/useJob.ts`: React Query polling query over `getJob`, 1000 ms cadence, stops on terminal status and treats a 404 as terminal with no retry
- `src/hooks/useCancelJob.ts`: React Query mutation over `cancelJob`, resolves true only when the cancel landed (202)
- `src/hooks/useHistory.ts`: React state over the `history.ts` store, exposes `entries` plus `addRun` / `setStatus` / `removeEntry` / `clear`
- `src/context/SettingsContext.tsx`: theme (system/dark/light, default system), results-position (right/below), accent colour, and editor font size, all localStorage-backed
- `src/context/SymbolicTypeContext.tsx`: `SymbolicTypeProvider` and `useSymbolicTypes`, holds each symbolic variable's chosen decode type by name so the choice persists across reruns
- `src/lib/decodeSymbolic.ts`: pure client-side re-interpreter of a symbolic value's raw ktest bytes as int / uint / float / double / hex / ascii (`decode`, `availableTypes`, `defaultType`), little-endian, matching ktest-tool
- `src/lib/resultsError.ts`: `classifyResultsError`, maps a submit or poll error to `expired` / `submit-rejected` / `unreachable`
- `src/lib/pagination.ts`: `clampPage`, parses a typed page number and clamps it into range
- `src/lib/history.ts`: localStorage run-history store. `readHistory`, `addRun` (move-to-front dedup, capped at `MAX_ENTRIES = 50`), `setStatus`, `removeEntry`, `clearHistory`, plus the `HistoryEntry` and `HistoryStatus` types
- `src/lib/historyView.ts`: pure view helpers for the history list. `historyLabel` (the `// title:` comment or first real code line), `relativeTime`, and `statusGlyph`. The terminal status a history entry shows now comes from `Job.outcome` (the backend's single classifier), not a client-side derivation
- `src/lib/kleeCompletions.ts`: static C and KLEE-intrinsic completion data (`COMPLETIONS`) plus the Monaco `CompletionItemProvider` registration (`registerCCompletions`) behind the editor autocomplete
- `src/lib/editorThemes.ts`: `defineKleeDarkTheme`, the `klee-dark` Monaco theme matching the app's slate surfaces
- `src/data/examples.ts`: the bundled example programs (`EXAMPLES`, `DEFAULT_EXAMPLE`), each C source imported `?raw` from `data/examples/*.c` and labelled by its `// title:` comment
- `src/components/Workspace.tsx`: layout chassis with five slot props (`topBar`, `sidebar?`, `main`, `results`, `statusBar`). `resultsPosition` flips main/results between row and column
- `src/components/TopBar.tsx`: KLEE wordmark, inline `FlagBar`, Run button, settings cog, and the collapsible `SymbolicInputPanel` mounted below the bar. Owns the local `settingsOpen` state and the document `pointerdown` / `keydown` listeners that dismiss the popover
- `src/components/FlagBar.tsx`: inline `max_time` and `max_memory` number inputs (valid / empty / invalid discriminated-union validation, snap-back on blur), the path-constraint (`query_format`) select, and the free-text extra-flags box (validated server-side against an allowlist, a rejection's reason renders in Results)
- `src/components/SymbolicInputPanel.tsx`: collapsible panel below the top bar. Per-spec toggles for symbolic stdin / files / args with bounded numeric fields, editing the nested `sym_stdin` / `sym_files` / `sym_args` objects on `KleeFlags`
- `src/components/Editor.tsx`: `@monaco-editor/react` wrapper. C language, controlled `value` / `onChange`, `resolvedTheme` mapped to `klee-dark` / `vs-light`, and registers the `kleeCompletions` provider on mount
- `src/components/Sidebar.tsx`: left panel with Examples and History tabs. Examples opens a bundled program, History lists per-browser runs with restore / delete / clear and a status glyph. Collapsible
- `src/components/Results.tsx`: dispatches first on submit or poll error kind (expired / submit-rejected / unreachable), then on job status (pending / running / parsing / done / compile-error / failed). Running shows elapsed time against the submitted limit. DoneView holds tab state (Test cases / Stats), a `HaltBadge`, per-variable type dropdowns, and page navigation over the test cases
- `src/components/SettingsPopover.tsx`: panel of segmented controls over `useSettings()` (theme, accent colour, font size, results position). Pure presentational
- `src/components/StatusBar.tsx`: bottom strip with backend-connected indicator (polls `/health` every 5 s via React Query, two-state connected/disconnected derived from `data` + `isError`), source byte count, and the KLEE version injected from the repository's `.klee-version` build input
- `src/pages/HomePage.tsx`: composes Workspace at route `/`. Owns `source`, `flags`, `jobId`, and the errors-first toggle. Wires the sidebar via `useHistory` (load example, restore run, delete / clear), `handleRun` posts via `useSubmitJob` and adds a history entry, and `handleCancel` goes via `useCancelJob`. `HomePage` and `Results` subscribe to the same `useJob(jobId)` query for controls, history, and rendering
- `src/pages/AdminPage.tsx`: polls fleet telemetry and cumulative usage every five seconds, shows queue and Worker state, and changes a Worker's live autoscaler maximum within the deployment limit. nginx protects the route and its API calls with Basic Auth

## Editor

Monaco, the editor that powers VS Code. CodeMirror 6 was the alternative considered. See `../docs/adr/0004-monaco-editor.md`.

## Why types are generated, not hand-written

The backend emits an OpenAPI spec from Pydantic models. `openapi-typescript` consumes that spec and emits TypeScript types. A rename on the backend, after regenerating, fails the frontend at compile time. Contract drift becomes impossible.

Regenerate when the backend schema changes:

```bash
npm run gen:types
```

The script expects the backend running on `http://localhost:8000`.

## Formatting and pre-commit

Prettier owns formatting, eslint owns correctness. Format with `npm run format`, or check without writing via `npm run format:check`. The pre-commit hook runs the formatter on commit.

The prettier and eslint hooks both run the frontend's own tooling from `node_modules`, so run `npm install` before committing. Without it they fail with a "command not found", the same way the eslint hook already would. CI runs both regardless, so unformatted or unlinted code cannot merge.
