# 0003. Src-layout for the backend Python package

**Status:** Accepted, 2026-05-19

## Context

The backend Python project under `klee-web/backend/` needs a directory layout. Two options:

- **Flat layout**: `backend/klee_web/` directly contains the package.
- **Src-layout**: `backend/src/klee_web/` puts the package one directory deeper, and Hatchling is told where to find it.

The choice is small but consequential. It affects how the package is imported in tests, which packaging bugs surface in CI versus in production, and the visual feel of the directory tree. It needs to be made once and held across Stage 1; changing it later requires a `git mv` plus a `pyproject.toml` edit.

## Decision

Adopt **src-layout**: the importable `klee_web` package lives at `backend/src/klee_web/`. Hatchling is told about it via:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/klee_web"]
```

The package becomes importable only after `uv sync` performs an editable install into the venv.

### Why src over flat

Python's import system implicitly adds the current working directory to `sys.path`. With flat layout, `pytest` from `backend/` finds `klee_web` by walking into the source tree on disk, not by importing from the installed (editable) wheel. Two failure modes follow:

1. Tests pass locally because they import directly from the source tree. The built wheel ships missing a file the developer forgot to declare in `[tool.hatch.build.targets.wheel.include]` or equivalent. Users (or, more relevantly, the Stage 2 Celery worker image) hit `ModuleNotFoundError` in production. The CI run that produced the wheel never caught it, because CI was also importing from source.
2. A stray top-level `klee_web.py` next to the `klee_web/` package is silently shadowed under flat layout. The mismatch is hard to debug and easy to miss. Under src-layout the source root is not on `sys.path` at all, so this collision cannot happen.

With src-layout, `backend/src/` is **not on `sys.path`** in the test process. The package is reachable only via the installed (editable) install, exactly the way a downstream user would reach it. Packaging bugs surface as test failures, not production incidents.

This matters most at the Stage 1 to Stage 2 transition. The same `klee_web` package is baked into a Celery worker Docker image at Stage 2. A missing-file packaging bug there is a worker-pod crash under real load, not a test failure on a laptop. Catching such bugs in unit tests, rather than at deploy time, is the entire reason this layout exists.

### Why this is not over-engineering

The cost is small and one-time:

- One extra directory in the tree (`backend/src/`).
- One `uv sync` step at first checkout before tests find the package.

The benefit is concrete and recurring: every packaging declaration error gets caught by unit tests. Plus the project aligns with modern PyPA defaults: `uv init --package`, Hatchling, FastAPI, Pydantic, Polars, Typer, and the entire Astral toolchain all default to src-layout. The pattern is recognised by IDE tooling (VS Code's Python extension reads `pyproject.toml` and handles `src/` automatically; PyCharm likewise).

### The old klee-web's `src/` is a different convention

The original klee-web (`https://github.com/klee/old-klee-web`) has `src/` at the **project root**, with `src/db/`, `src/e2e/`, `src/klee_web/`, `src/nginx/` as siblings. That is a "all source under src" monorepo organising rule from the Django era, not per-Python-package src-layout. Superficially the same word, different intent. Worth flagging in this ADR because the surface similarity will mislead anyone reading both codebases.

The new klee-web uses **per-Python-package src-layout**, with `src/` only under `backend/`. The frontend and runner subprojects are not Python packages and do not have a `src/` of this kind.

## Consequences

**Positive**

- Tests run against the installed package, exactly matching how a downstream user (or a Celery worker pod) would import it. Packaging bugs surface in unit tests.
- The choice matches modern PyPA tooling defaults, so new contributors do not need a special README section explaining the layout.
- IDE tooling support is good out of the box on VS Code and PyCharm with `pyproject.toml` in place.

**Negative**

- One extra directory in the tree. Visual noise.
- First-time contributors must run `uv sync` before tests can import the package. After the first run, the friction is invisible.
- Older IDE configurations or hand-rolled tooling may not auto-detect `src/` as a source root and need to be told manually.

**Load-bearing**

- Stage 2's Celery worker image installs the same wheel produced from this layout. If we switched to flat layout for perceived simplicity, packaging bugs would surface at Stage 2 worker startup instead of at Stage 1 tests, which is exactly the wrong time.
- The `[tool.hatch.build.targets.wheel] packages = ["src/klee_web"]` line is the configuration knob that makes Hatchling find the package. Removing it without restructuring breaks the wheel.

**Out of scope**

- Whether the frontend and runner subprojects should also use src-layout. They are not Python packages (frontend is TypeScript via Vite, runner is a Dockerfile plus a small Python entrypoint), so the question does not apply directly.
- The choice of Hatchling specifically (versus setuptools, PDM, Flit). Hatchling is the `uv init --package` default and a modern PyPA recommendation; switching build backends later is feasible but unnecessary now.

## References

- ADR-0001: stage-based additive architecture.
- Python Packaging User Guide, "src layout vs flat layout" discussion.
- Hatchling documentation on `[tool.hatch.build.targets.wheel] packages`.
- Original klee-web at `https://github.com/klee/old-klee-web` for the contrasting "all source under src" convention.
