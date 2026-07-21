#!/usr/bin/env bash
set -euo pipefail

readonly DEPLOYMENT_ENV=/etc/klee-web/deployment.env
readonly ADMIN_HTPASSWD=/etc/klee-web/admin.htpasswd

if ((EUID != 0)); then
  printf 'set-admin-password.sh must run as root\n' >&2
  exit 1
fi

if [[ ! -f $DEPLOYMENT_ENV ]]; then
  printf 'Deployment environment is missing: %s\n' "$DEPLOYMENT_ENV" >&2
  exit 1
fi

# This script reads TLS paths itself. systemd loads the same file independently.
# shellcheck disable=SC1090
. "$DEPLOYMENT_ENV"
: "${TLS_CERTIFICATE_FILE:?TLS_CERTIFICATE_FILE must be set}"
: "${TLS_PRIVATE_KEY_FILE:?TLS_PRIVATE_KEY_FILE must be set}"

for certificate_file in "$TLS_CERTIFICATE_FILE" "$TLS_PRIVATE_KEY_FILE"; do
  if [[ ! -f $certificate_file ]]; then
    printf 'TLS file is missing: %s\n' "$certificate_file" >&2
    exit 1
  fi
done

# -c intentionally replaces the file. Omit it only if multiple usernames are supported.
htpasswd -cB "$ADMIN_HTPASSWD" admin
# The private parent protects the host file. nginx workers need read access after mounting.
chmod 0644 "$ADMIN_HTPASSWD"

# enable configures future boots. --now also performs the first start.
systemctl enable --now klee-web.service
printf 'KLEE Web is enabled and running\n'
