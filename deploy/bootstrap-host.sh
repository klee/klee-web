#!/usr/bin/env bash
set -euo pipefail

readonly DOCKER_VERSION='5:29.6.2-1~ubuntu.24.04~noble'
readonly CONTAINERD_VERSION='2.2.6-1~ubuntu.24.04~noble'
readonly COMPOSE_VERSION='5.3.1-1~ubuntu.24.04~noble'
readonly GVISOR_RELEASE='20260714'
readonly PROBE_IMAGE='hello-world@sha256:d1a8d0a4eeb63aff09f5f34d4d80505e0ba81905f36158cc3970d8e07179e59e'
readonly DEPLOYMENT_ENV=/etc/klee-web/deployment.env

if ((EUID != 0)); then
  printf 'bootstrap-host.sh must run as root\n' >&2
  exit 1
fi

if [[ ! -f $DEPLOYMENT_ENV ]]; then
  printf 'Deployment environment is missing: %s\n' "$DEPLOYMENT_ENV" >&2
  exit 1
fi

# This cloud-init file is unavailable during static analysis.
# shellcheck disable=SC1090
. "$DEPLOYMENT_ENV"
readonly deployment_role=${DEPLOYMENT_ROLE:-single}
case "$deployment_role" in
  single | web | worker) ;;
  *)
    printf 'Unsupported DEPLOYMENT_ROLE: %s\n' "$deployment_role" >&2
    exit 1
    ;;
esac

if [[ ! -r /etc/os-release ]]; then
  printf 'bootstrap-host.sh requires Ubuntu 24.04 on AMD64\n' >&2
  exit 1
fi

# This standard host file is outside the repository seen by ShellCheck.
# shellcheck disable=SC1091
. /etc/os-release
os_id=${ID:-}
os_codename=${VERSION_CODENAME:-}
architecture=$(dpkg --print-architecture)

if [[ $os_id != ubuntu || $os_codename != noble || $architecture != amd64 ]]; then
  printf 'bootstrap-host.sh requires Ubuntu 24.04 Noble on AMD64\n' >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=l

printf '%s\n' \
  'APT::Periodic::Update-Package-Lists "1";' \
  'APT::Periodic::Unattended-Upgrade "0";' \
  > /etc/apt/apt.conf.d/99-klee-web-maintenance

apt-get update
apt-get dist-upgrade -y
apt-get install -y --no-install-recommends apache2-utils ca-certificates curl

install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod 0644 /etc/apt/keyrings/docker.asc
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$architecture" "$os_codename" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y --no-install-recommends \
  "docker-ce=$DOCKER_VERSION" \
  "docker-ce-cli=$DOCKER_VERSION" \
  "containerd.io=$CONTAINERD_VERSION" \
  "docker-compose-plugin=$COMPOSE_VERSION"
apt-mark hold docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

if [[ $deployment_role != web ]]; then
  temporary_directory=$(mktemp -d)
  trap 'rm -rf "$temporary_directory"' EXIT
  gvisor_url="https://storage.googleapis.com/gvisor/releases/release/$GVISOR_RELEASE/x86_64"

  for asset in runsc runsc.sha512 containerd-shim-runsc-v1 containerd-shim-runsc-v1.sha512; do
    curl -fsSL "$gvisor_url/$asset" -o "$temporary_directory/$asset"
  done

  (
    cd "$temporary_directory"
    sha512sum -c runsc.sha512
    sha512sum -c containerd-shim-runsc-v1.sha512
  )
  install -m 0755 "$temporary_directory/runsc" /usr/local/bin/runsc
  install -m 0755 "$temporary_directory/containerd-shim-runsc-v1" \
    /usr/local/bin/containerd-shim-runsc-v1
  # Register one binary twice. Arguments after -- make only runsc-kvm use KVM.
  runsc install
  runsc install --runtime=runsc-kvm -- --platform=kvm
  systemctl restart docker
fi

install -d -m 0755 /opt/klee-web
install -d -m 0700 /etc/klee-web

selected_runtime=
if [[ $deployment_role != web ]]; then
  # Systrap must work on every execution host before KVM is considered.
  docker run --rm --runtime=runsc --network=none --read-only \
    "$PROBE_IMAGE"

  selected_runtime=runsc
  # A device node alone does not prove nested KVM, so run a real container.
  if [[ -c /dev/kvm ]]; then
    if docker run --rm --runtime=runsc-kvm --network=none --read-only \
      "$PROBE_IMAGE"; then
      selected_runtime=runsc-kvm
    else
      printf '/dev/kvm exists but the runsc-kvm probe failed, selecting runsc\n' >&2
    fi
  else
    printf '/dev/kvm is absent, selecting runsc\n'
  fi
else
  printf 'Web role does not execute Jobs, skipping gVisor installation\n'
fi

# Keep observed host capability separate from Terraform's desired values.
printf 'KLEE_RUNTIME=%s\n' "$selected_runtime" > /etc/klee-web/runtime.env
chmod 0644 /etc/klee-web/runtime.env

docker version --format 'Docker Engine {{.Server.Version}}'
docker compose version
if [[ -n $selected_runtime ]]; then
  runsc --version
  printf 'Selected KLEE runtime: %s\n' "$selected_runtime"
fi
