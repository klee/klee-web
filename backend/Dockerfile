FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# docker CLI (client only; the worker shells out to it, the api carries it
# unused). Static Go binary, so copying it onto this glibc base is fine.
COPY --from=docker:29-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Deps-only layer: installs dependencies but not the project, so it stays cached
# until the lockfile changes rather than on every source edit.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Project layer: source present, so this installs klee_web itself.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Default command is the api. The worker service overrides it in compose.
CMD ["uvicorn", "klee_web.main:app", "--host", "0.0.0.0", "--port", "8000"]
