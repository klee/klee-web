.PHONY: up install runner

install:
	cd backend && uv sync
	cd frontend && npm install
	command -v pre-commit >/dev/null 2>&1 && pre-commit install --hook-type pre-commit --hook-type pre-push || echo "pre-commit not on PATH; see README 'Pre-commit hooks', then run: pre-commit install --hook-type pre-commit --hook-type pre-push"

up: runner
	@trap 'kill 0' EXIT INT TERM; \
	(cd backend && exec uv run uvicorn klee_web.main:app --port 8000 --reload) & \
	(cd frontend && exec npm run dev) & \
	wait

runner:
	docker build -t klee-web-runner ./runner
