#!/usr/bin/env bash
set -euo pipefail

readonly DEPLOYMENT_ENV=/etc/klee-web/deployment.env
readonly RUNTIME_ENV=/etc/klee-web/runtime.env
readonly DEPLOYMENT_DIRECTORY=/opt/klee-web

if ((EUID != 0)); then
  printf 'compose-deployment.sh must run as root\n' >&2
  exit 1
fi

if (($# != 1)); then
  printf 'Usage: compose-deployment.sh {config|images|pull|prepare|ps|up|down}\n' >&2
  exit 1
fi
readonly action=$1

for required_file in \
  "$DEPLOYMENT_ENV" \
  "$RUNTIME_ENV" \
  "$DEPLOYMENT_DIRECTORY/docker-compose.yml"; do
  if [[ ! -f $required_file ]]; then
    printf 'Required deployment file is missing: %s\n' "$required_file" >&2
    exit 1
  fi
done

set -a
# These cloud-init files are unavailable during static analysis.
# shellcheck disable=SC1090
. "$DEPLOYMENT_ENV"
# shellcheck disable=SC1090
. "$RUNTIME_ENV"
set +a

readonly deployment_role=${DEPLOYMENT_ROLE:-single}
compose_options=(
  --project-name klee-web
  -f "$DEPLOYMENT_DIRECTORY/docker-compose.yml"
)
services=()

case "$deployment_role" in
  single)
    compose_options+=(-f "$DEPLOYMENT_DIRECTORY/compose.production.yml")
    ;;
  web)
    compose_options+=(-f "$DEPLOYMENT_DIRECTORY/compose.production.yml")
    services=(redis api nginx)
    ;;
  worker)
    compose_options+=(-f "$DEPLOYMENT_DIRECTORY/compose.worker.yml")
    services=(worker)
    ;;
  *)
    printf 'Unsupported DEPLOYMENT_ROLE: %s\n' "$deployment_role" >&2
    exit 1
    ;;
esac

for compose_file in "${compose_options[@]}"; do
  if [[ $compose_file == /* && ! -f $compose_file ]]; then
    printf 'Required Compose file is missing: %s\n' "$compose_file" >&2
    exit 1
  fi
done

case "$action" in
  config)
    docker compose "${compose_options[@]}" config --quiet
    ;;
  images)
    docker compose "${compose_options[@]}" config --images "${services[@]}"
    ;;
  pull)
    docker compose "${compose_options[@]}" pull "${services[@]}"
    ;;
  prepare)
    if [[ $deployment_role != worker ]]; then
      provision_tls="$DEPLOYMENT_DIRECTORY/provision-tls.sh"
      if [[ ! -x $provision_tls ]]; then
        printf 'TLS provisioner is missing or not executable: %s\n' "$provision_tls" >&2
        exit 1
      fi
      "$provision_tls"
    fi
    systemctl daemon-reload
    if [[ $deployment_role == worker ]]; then
      if [[ -f /var/run/reboot-required ]]; then
        systemctl enable klee-web.service
      else
        systemctl enable --now klee-web.service
      fi
    fi
    ;;
  ps)
    docker compose "${compose_options[@]}" ps "${services[@]}"
    ;;
  up)
    docker compose "${compose_options[@]}" up -d --no-build --wait \
      --wait-timeout 600 "${services[@]}"
    ;;
  down)
    docker compose "${compose_options[@]}" down --timeout 675
    ;;
  *)
    printf 'Unsupported action: %s\n' "$action" >&2
    exit 1
    ;;
esac
