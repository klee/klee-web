#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST_OS="$(uname -s)"

if [[ "$HOST_OS" == "Darwin" ]]; then
    if [[ "${KLEE_E2E_ALLOW_RUNC:-}" != "1" ]]; then
        printf '%s\n' \
            'gVisor is unavailable on macOS.' \
            'Run local E2E with reduced isolation using:' \
            'KLEE_E2E_ALLOW_RUNC=1 npm run test:e2e' >&2
        exit 1
    fi
    export KLEE_RUNTIME=runc
    printf '%s\n' \
        'WARNING: macOS E2E is using runc without gVisor isolation.' \
        'Run only trusted checked-out code and test inputs in this mode.' >&2
elif [[ -n "${KLEE_E2E_ALLOW_RUNC:-}" ]]; then
    printf 'KLEE_E2E_ALLOW_RUNC is supported only on macOS\n' >&2
    exit 1
fi

ADMIN_HTPASSWD_FILE="$(mktemp)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml:$ROOT_DIR/docker-compose.override.yml:$ROOT_DIR/frontend/e2e/docker-compose.yml"
COMPOSE_PROJECT_NAME="klee-web-e2e"
export ADMIN_HTPASSWD_FILE COMPOSE_FILE COMPOSE_PROJECT_NAME

cleanup() {
    status=$?
    trap - EXIT
    set +e
    make -C "$ROOT_DIR" down
    down_status=$?
    rm -f "$ADMIN_HTPASSWD_FILE"
    if (( status != 0 )); then
        exit "$status"
    fi
    exit "$down_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

docker run --rm httpd:2.4.68-alpine \
    htpasswd -nbB admin test-password > "$ADMIN_HTPASSWD_FILE"
chmod 644 "$ADMIN_HTPASSWD_FILE"

make -C "$ROOT_DIR" deploy
runtime="$(docker compose exec -T worker printenv KLEE_RUNTIME)"
if [[ "$HOST_OS" == "Darwin" ]]; then
    if [[ "$runtime" != "runc" ]]; then
        echo "macOS e2e Worker must use runc, got: $runtime" >&2
        exit 1
    fi
elif [[ "$runtime" != "runsc" && "$runtime" != "runsc-kvm" ]]; then
    echo "e2e Worker must use gVisor, got: $runtime" >&2
    exit 1
fi
make -C "$ROOT_DIR" logs
