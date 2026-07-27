#!/usr/bin/env bash
set -euo pipefail

readonly DEPLOYMENT_ENV=/etc/klee-web/deployment.env
readonly RUNTIME_ENV=/etc/klee-web/runtime.env
readonly DEPLOYMENT_DIRECTORY=/opt/klee-web
readonly COMPOSE_DEPLOYMENT="$DEPLOYMENT_DIRECTORY/compose-deployment.sh"

if ((EUID != 0)); then
  printf 'pull-images.sh must run as root\n' >&2
  exit 1
fi

for required_file in \
  "$DEPLOYMENT_ENV" \
  "$RUNTIME_ENV" \
  "$COMPOSE_DEPLOYMENT"; do
  if [[ ! -f $required_file ]]; then
    printf 'Required deployment file is missing: %s\n' "$required_file" >&2
    exit 1
  fi
done

# Export deployment values for Compose interpolation and the Runner pull.
set -a
# These cloud-init files are unavailable during static analysis.
# shellcheck disable=SC1090
. "$DEPLOYMENT_ENV"
# shellcheck disable=SC1090
. "$RUNTIME_ENV"
set +a

readonly deployment_role=${DEPLOYMENT_ROLE:-single}
case "$deployment_role" in
  single)
    image_variables=(BACKEND_IMAGE FRONTEND_IMAGE RUNNER_IMAGE)
    ;;
  web)
    image_variables=(BACKEND_IMAGE FRONTEND_IMAGE)
    ;;
  worker)
    image_variables=(BACKEND_IMAGE RUNNER_IMAGE)
    ;;
  *)
    printf 'Unsupported DEPLOYMENT_ROLE: %s\n' "$deployment_role" >&2
    exit 1
    ;;
esac

# ${!image_variable} reads the variable whose name is held in image_variable.
for image_variable in "${image_variables[@]}"; do
  : "${!image_variable:?$image_variable must be set}"
  if [[ ! ${!image_variable} =~ @sha256:[0-9a-f]{64}$ ]]; then
    printf '%s must use an immutable SHA-256 digest\n' "$image_variable" >&2
    exit 1
  fi
done

# Catch interpolation or merge errors before downloading large layers.
"$COMPOSE_DEPLOYMENT" config
printf 'Compose service images:\n'
"$COMPOSE_DEPLOYMENT" images

started_at=$(date +%s)
printf 'Image pull started at %s\n' "$(date --iso-8601=seconds)"
# Compose pulls service images. Runner is dynamic and must be pulled separately.
"$COMPOSE_DEPLOYMENT" pull
if [[ $deployment_role != web ]]; then
  docker image pull "$RUNNER_IMAGE"
fi
finished_at=$(date +%s)
printf 'Image pull completed in %s seconds\n' "$((finished_at - started_at))"
