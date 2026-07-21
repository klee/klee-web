#!/usr/bin/env bash
set -euo pipefail

readonly DEPLOYMENT_ENV=/etc/klee-web/deployment.env
readonly RUNTIME_ENV=/etc/klee-web/runtime.env
readonly DEPLOYMENT_DIRECTORY=/opt/klee-web
readonly -a COMPOSE_OPTIONS=(
  --project-name klee-web
  -f "$DEPLOYMENT_DIRECTORY/docker-compose.yml"
  -f "$DEPLOYMENT_DIRECTORY/compose.production.yml"
)

if ((EUID != 0)); then
  printf 'pull-images.sh must run as root\n' >&2
  exit 1
fi

for required_file in \
  "$DEPLOYMENT_ENV" \
  "$RUNTIME_ENV" \
  "$DEPLOYMENT_DIRECTORY/docker-compose.yml" \
  "$DEPLOYMENT_DIRECTORY/compose.production.yml"; do
  if [[ ! -f $required_file ]]; then
    printf 'Required deployment file is missing: %s\n' "$required_file" >&2
    exit 1
  fi
done

# Export deployment values for Compose interpolation and the Runner pull.
set -a
. "$DEPLOYMENT_ENV"
. "$RUNTIME_ENV"
set +a

: "${BACKEND_IMAGE:?BACKEND_IMAGE must be set}"
: "${FRONTEND_IMAGE:?FRONTEND_IMAGE must be set}"
: "${RUNNER_IMAGE:?RUNNER_IMAGE must be set}"

# ${!image_variable} reads the variable whose name is held in image_variable.
for image_variable in BACKEND_IMAGE FRONTEND_IMAGE RUNNER_IMAGE; do
  if [[ ! ${!image_variable} =~ @sha256:[0-9a-f]{64}$ ]]; then
    printf '%s must use an immutable SHA-256 digest\n' "$image_variable" >&2
    exit 1
  fi
done

# Catch interpolation or merge errors before downloading large layers.
docker compose "${COMPOSE_OPTIONS[@]}" config --quiet
printf 'Compose service images:\n'
docker compose "${COMPOSE_OPTIONS[@]}" config --images

started_at=$(date +%s)
printf 'Image pull started at %s\n' "$(date --iso-8601=seconds)"
# Compose pulls service images. Runner is dynamic and must be pulled separately.
docker compose "${COMPOSE_OPTIONS[@]}" pull
docker image pull "$RUNNER_IMAGE"
finished_at=$(date +%s)
printf 'Image pull completed in %s seconds\n' "$((finished_at - started_at))"
