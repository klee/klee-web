.PHONY: up up-celery up-pool install runner admin-password deploy deploy-gvisor deploy-kvm

WORKERS ?= 2
WORKER_CONCURRENCY_MAX ?= 4
ADMIN_HTPASSWD_FILE ?= $(CURDIR)/.secrets/admin.htpasswd
export WORKER_CONCURRENCY_MAX ADMIN_HTPASSWD_FILE

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
	(cd backend && exec uv run celery -A klee_web.celery_app worker -Q klee-jobs --autoscale=$(WORKER_CONCURRENCY_MAX),1 --loglevel=info) & \
	(cd frontend && exec npm run dev) & \
	wait

up-pool: runner
	docker compose up -d --wait redis
	@trap 'trap - EXIT INT TERM; docker compose down; kill 0' EXIT INT TERM; \
	export REDIS_URL=redis://localhost:6379/0 CELERY_BROKER_URL=redis://localhost:6379/1; \
	(cd backend && exec uv run uvicorn klee_web.main:app --port 8000 --reload) & \
	for i in $$(seq 1 $(WORKERS)); do \
		(cd backend && exec uv run celery -A klee_web.celery_app worker -Q klee-jobs --autoscale=$(WORKER_CONCURRENCY_MAX),1 --hostname=worker$$i@%h --loglevel=info) & \
	done; \
	(cd frontend && exec npm run dev) & \
	wait

deploy deploy-gvisor deploy-kvm: runner
	@trap 'trap - EXIT INT TERM; docker compose down' EXIT INT TERM; \
	docker compose up --build

deploy-gvisor: KLEE_RUNTIME := runsc
deploy-kvm:    KLEE_RUNTIME := runsc-kvm
export KLEE_RUNTIME

admin-password:
	@mkdir -p "$(dir $(ADMIN_HTPASSWD_FILE))"
	@chmod 700 "$(dir $(ADMIN_HTPASSWD_FILE))"
	@docker run --rm -it \
		--user "$$(id -u):$$(id -g)" \
		--mount "type=bind,source=$(dir $(ADMIN_HTPASSWD_FILE)),target=/secrets" \
		--env "OUTPUT_FILE=/secrets/$(notdir $(ADMIN_HTPASSWD_FILE))" \
		httpd:2.4.68-alpine \
		sh -c 'umask 077 && htpasswd -cB "$$OUTPUT_FILE" admin && chmod 644 "$$OUTPUT_FILE"'

runner:
	docker build -t klee-web-runner ./runner
