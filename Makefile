.PHONY: up up-celery install runner

install:
	cd backend && uv sync
	cd frontend && npm install
	command -v pre-commit >/dev/null 2>&1 && pre-commit install --hook-type pre-commit --hook-type pre-push || echo "pre-commit not on PATH; see README 'Pre-commit hooks', then run: pre-commit install --hook-type pre-commit --hook-type pre-push"

up: runner
	@trap 'kill 0' EXIT INT TERM; \
	(cd backend && exec uv run uvicorn klee_web.main:app --port 8000 --reload) & \
	(cd frontend && exec npm run dev) & \
	wait

up-celery: runner
	docker compose up -d --wait redis
	@trap 'trap - EXIT INT TERM; docker compose down; kill 0' EXIT INT TERM; \
	export REDIS_URL=redis://localhost:6379/0 CELERY_BROKER_URL=redis://localhost:6379/1; \
	(cd backend && exec uv run uvicorn klee_web.main:app --port 8000 --reload) & \
	(cd backend && exec uv run celery -A klee_web.celery_app worker -Q klee-jobs --concurrency=2 --loglevel=info) & \
	(cd frontend && exec npm run dev) & \
	wait

runner:
	docker build -t klee-web-runner ./runner
