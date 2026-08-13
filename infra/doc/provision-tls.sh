#!/usr/bin/env bash
set -euo pipefail

readonly DOMAIN='klee.doc.ic.ac.uk'
readonly CERTBOT_IMAGE='docker.io/certbot/certbot@sha256:34ee91d2f43008eb78a007d22f23ed4b2eaa9a454cb27ca2c042b49527a695b4'
readonly CERTIFICATE_NAME='klee-doc'
readonly LETSENCRYPT_DIRECTORY='/etc/letsencrypt'
readonly TLS_DIRECTORY='/etc/klee-web/tls'

if ((EUID != 0)); then
  printf 'provision-tls.sh must run as root\n' >&2
  exit 1
fi

install_certificate() {
  local source_directory="$LETSENCRYPT_DIRECTORY/live/$CERTIFICATE_NAME"

  # Certbot rotates symlinks. Compose receives stable files with nginx-safe modes.
  install -d -m 0700 "$TLS_DIRECTORY"
  install -m 0644 "$source_directory/fullchain.pem" "$TLS_DIRECTORY/fullchain.pem"
  install -m 0600 "$source_directory/privkey.pem" "$TLS_DIRECTORY/privkey.pem"
}

# Resolve one immutable image, then forbid the challenge container from pulling a tag.
docker image pull "$CERTBOT_IMAGE"

certificate_directory="$LETSENCRYPT_DIRECTORY/live/$CERTIFICATE_NAME"
if [[ -f $certificate_directory/fullchain.pem && -f $certificate_directory/privkey.pem ]]; then
  install_certificate
  printf 'Reused the existing certificate for %s\n' "$DOMAIN"
  exit 0
fi

install -d -m 0700 "$LETSENCRYPT_DIRECTORY"
# KLEE Web is still stopped, so Certbot can own port 80 for this HTTP-01 challenge.
docker run --rm --pull=never \
  --publish 80:80 \
  --volume "$LETSENCRYPT_DIRECTORY:/etc/letsencrypt" \
  "$CERTBOT_IMAGE" \
  certonly \
  --non-interactive \
  --agree-tos \
  --register-unsafely-without-email \
  --standalone \
  --domain "$DOMAIN" \
  --cert-name "$CERTIFICATE_NAME"

install_certificate
# Certbot needs a writable config directory for its lock while printing identity and expiry.
docker run --rm --pull=never \
  --volume "$LETSENCRYPT_DIRECTORY:/etc/letsencrypt" \
  "$CERTBOT_IMAGE" certificates
