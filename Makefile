.PHONY: install runner admin-password deploy logs down

KLEE_VERSION := $(shell cat .klee-version)
RUNNER_IMAGE ?= klee-web-runner
WORKER_CONCURRENCY_MAX ?= 4
WORKER_REPLICAS ?= 1
KLEE_RUNTIME ?= $(if $(wildcard /dev/kvm),runsc-kvm,runsc)
ADMIN_HTPASSWD_FILE ?= $(CURDIR)/.secrets/admin.htpasswd
export WORKER_CONCURRENCY_MAX WORKER_REPLICAS KLEE_RUNTIME ADMIN_HTPASSWD_FILE KLEE_VERSION RUNNER_IMAGE

install:
	cd backend && uv sync
	cd frontend && npm install
	command -v pre-commit >/dev/null 2>&1 && pre-commit install --hook-type pre-commit --hook-type pre-push || echo "pre-commit not on PATH; see README 'Pre-commit hooks', then run: pre-commit install --hook-type pre-commit --hook-type pre-push"

deploy: runner
	RUNNER_IMAGE="$$(docker image inspect --format '{{.Id}}' klee-web-runner)" \
		docker compose up -d --build --wait

logs:
	docker compose logs -f

down:
	docker compose down

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
	docker build --build-arg KLEE_VERSION=$(KLEE_VERSION) -t klee-web-runner ./runner
