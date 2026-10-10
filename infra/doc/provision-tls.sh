#!/usr/bin/env bash
set -euo pipefail

readonly DOMAIN='klee.doc.ic.ac.uk'
readonly CERTBOT_IMAGE='docker.io/certbot/certbot@sha256:34ee91d2f43008eb78a007d22f23ed4b2eaa9a454cb27ca2c042b49527a695b4'
readonly CERTIFICATE_NAME='klee-doc'
readonly LETSENCRYPT_DIRECTORY='/etc/letsencrypt'
readonly TLS_DIRECTORY='/etc/klee-web/tls'
readonly action=${1:-provision}
readonly ACME_WEBROOT_DIRECTORY=${ACME_WEBROOT_DIRECTORY:-}
readonly TLS_CERTIFICATE_DIRECTORY=${TLS_CERTIFICATE_DIRECTORY:-}
nginx_container=''
candidate_directory=''
previous_generation=''
activation_pending=false

if ((EUID != 0)); then
  printf 'provision-tls.sh must run as root\n' >&2
  exit 1
fi

if (($# > 1)); then
  printf 'Usage: provision-tls.sh [provision|prepare-webroot|reconfigure|dry-run|renew]\n' >&2
  exit 1
fi

exec 9>/run/lock/klee-web-deployment.lock
flock -n 9 || { printf 'Another deployment or TLS operation is already running\n' >&2; exit 1; }

install_certificate() {
  local source_directory="$LETSENCRYPT_DIRECTORY/live/$CERTIFICATE_NAME"

  # Certbot rotates symlinks. Compose receives stable files with nginx-safe modes.
  install -d -m 0700 "$TLS_DIRECTORY"
  install -m 0644 "$source_directory/fullchain.pem" "$TLS_DIRECTORY/fullchain.pem"
  install -m 0600 "$source_directory/privkey.pem" "$TLS_DIRECTORY/privkey.pem"
}

select_generation() {
  ln -sfn "$1" "$TLS_CERTIFICATE_DIRECTORY/.current-next"
  mv -Tf "$TLS_CERTIFICATE_DIRECTORY/.current-next" "$TLS_CERTIFICATE_DIRECTORY/current"
}

rollback_activation() {
  local status=$?
  trap - EXIT
  if [[ $activation_pending == true ]]; then
    printf 'TLS activation failed. Restoring the previous certificate selection\n' >&2
    if [[ -n $previous_generation ]]; then
      select_generation "$previous_generation"
      if [[ -n $nginx_container ]]; then
        docker exec "$nginx_container" nginx -t &&
          docker exec "$nginx_container" nginx -s reload ||
          printf 'The previous certificate is restored on disk, but nginx reload failed\n' >&2
      fi
    else
      rm -f "$TLS_CERTIFICATE_DIRECTORY/current"
    fi
  fi
  if [[ -n $candidate_directory &&
    $(readlink "$TLS_CERTIFICATE_DIRECTORY/current" || true) != "${candidate_directory##*/}" ]]; then
    rm -rf -- "$candidate_directory"
  fi
  exit "$status"
}
trap rollback_activation EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

require_webroot() {
  : "${ACME_WEBROOT_DIRECTORY:?Set ACME_WEBROOT_DIRECTORY for webroot renewal}"
  : "${TLS_CERTIFICATE_DIRECTORY:?Set TLS_CERTIFICATE_DIRECTORY for webroot renewal}"
  if [[ $ACME_WEBROOT_DIRECTORY != /* || $TLS_CERTIFICATE_DIRECTORY != /* ]]; then
    printf 'Webroot and certificate directory paths must be absolute\n' >&2
    exit 1
  fi
}

require_nginx() {
  local containers=() mounted_directory
  mapfile -t containers < <(
    docker ps --filter label=com.docker.compose.project=klee-web \
      --filter label=com.docker.compose.service=nginx --format '{{.ID}}'
  )
  if ((${#containers[@]} != 1)); then
    printf 'Expected one running KLEE Web nginx container\n' >&2
    exit 1
  fi
  nginx_container=${containers[0]}
  mounted_directory=$(docker inspect --format \
    '{{range .Mounts}}{{if eq .Destination "/etc/nginx/certs"}}{{.Source}}{{end}}{{end}}' \
    "$nginx_container")
  if [[ $mounted_directory != "$TLS_CERTIFICATE_DIRECTORY" ]]; then
    printf 'nginx must mount the configured certificate directory before renewal\n' >&2
    exit 1
  fi
}

webroot_certbot() {
  docker run --rm --pull=never \
    --log-driver=json-file --log-opt max-size=10m --log-opt max-file=3 \
    --mount "type=bind,source=$LETSENCRYPT_DIRECTORY,target=/etc/letsencrypt" \
    --mount "type=bind,source=$ACME_WEBROOT_DIRECTORY,target=/var/www/certbot" \
    "$CERTBOT_IMAGE" "$@" \
    --non-interactive --cert-name "$CERTIFICATE_NAME" \
    --webroot --webroot-path /var/www/certbot --no-directory-hooks
}

certificate_fingerprint() {
  openssl x509 -in "$1" -noout -fingerprint -sha256
}

served_fingerprint() {
  timeout 5 openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" \
    </dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256 2>/dev/null
}

activate_certificate() {
  local source_directory="$LETSENCRYPT_DIRECTORY/live/$CERTIFICATE_NAME"
  local certificate_public_key private_public_key expected generation current attempt

  openssl x509 -in "$source_directory/fullchain.pem" -noout \
    -checkhost "$DOMAIN" -checkend 86400
  openssl verify -purpose sslserver -verify_hostname "$DOMAIN" \
    -untrusted "$source_directory/fullchain.pem" "$source_directory/fullchain.pem"
  certificate_public_key=$(openssl x509 -in "$source_directory/fullchain.pem" -pubkey -noout |
    openssl pkey -pubin -outform DER | sha256sum)
  private_public_key=$(openssl pkey -in "$source_directory/privkey.pem" -pubout -outform DER |
    sha256sum)
  if [[ $certificate_public_key != "$private_public_key" ]]; then
    printf 'Certificate and private key do not match\n' >&2
    exit 1
  fi

  expected=$(certificate_fingerprint "$source_directory/fullchain.pem")
  if ! cmp -s "$source_directory/fullchain.pem" "$TLS_CERTIFICATE_DIRECTORY/current/fullchain.pem" ||
    ! cmp -s "$source_directory/privkey.pem" "$TLS_CERTIFICATE_DIRECTORY/current/privkey.pem"; then
    candidate_directory=$(mktemp -d "$TLS_CERTIFICATE_DIRECTORY/generation.XXXXXXXX")
    install -m 0644 "$source_directory/fullchain.pem" "$candidate_directory/fullchain.pem"
    install -m 0600 "$source_directory/privkey.pem" "$candidate_directory/privkey.pem"
    previous_generation=$(readlink "$TLS_CERTIFICATE_DIRECTORY/current" || true)
    generation=${candidate_directory##*/}
    ln -sfn current/fullchain.pem "$TLS_CERTIFICATE_DIRECTORY/selfsigned.crt"
    ln -sfn current/privkey.pem "$TLS_CERTIFICATE_DIRECTORY/selfsigned.key"
    activation_pending=true
    select_generation "$generation"
  fi

  if [[ -n $nginx_container ]]; then
    if [[ $(served_fingerprint || true) != "$expected" ]]; then
      docker exec "$nginx_container" nginx -t
      docker exec "$nginx_container" nginx -s reload
      for attempt in {1..10}; do
        if [[ $(served_fingerprint || true) == "$expected" ]]; then
          break
        fi
        sleep 1
      done
      if [[ $attempt == 10 && $(served_fingerprint || true) != "$expected" ]]; then
        printf 'nginx did not serve the selected certificate after reload\n' >&2
        exit 1
      fi
      printf 'nginx serves the selected certificate for %s\n' "$DOMAIN"
    else
      printf 'nginx already serves the current certificate. No reload needed\n'
    fi
  fi

  activation_pending=false
  candidate_directory=''
  current=$(readlink "$TLS_CERTIFICATE_DIRECTORY/current")
  for generation in "$TLS_CERTIFICATE_DIRECTORY"/generation.*; do
    if [[ -d $generation && ${generation##*/} != "$current" &&
      ${generation##*/} != "$previous_generation" ]]; then
      # Keep the previous pair even after a later no-op renewal check.
      if [[ -z $previous_generation ]]; then
        continue
      fi
      rm -rf -- "$generation"
    fi
  done
}

case "$action" in
  prepare-webroot)
    require_webroot
    docker image pull "$CERTBOT_IMAGE"
    install -d -m 0755 "$ACME_WEBROOT_DIRECTORY/.well-known/acme-challenge"
    install -d -m 0700 "$TLS_CERTIFICATE_DIRECTORY"
    activate_certificate
    printf 'Prepared the webroot and production certificate directory\n'
    exit 0
    ;;
  reconfigure|dry-run|renew)
    require_webroot
    require_nginx
    case "$action" in
      reconfigure) webroot_certbot reconfigure ;;
      dry-run) webroot_certbot renew --dry-run ;;
      renew)
        webroot_certbot renew
        activate_certificate
        ;;
    esac
    exit 0
    ;;
  provision)
    ;;
  *)
    printf 'Unsupported TLS action: %s\n' "$action" >&2
    exit 1
    ;;
esac

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
