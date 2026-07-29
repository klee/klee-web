#!/usr/bin/env bash
set -euo pipefail

if ((EUID != 0)); then
  printf 'maintain-host.sh must run as root\n' >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=l

systemctl stop klee-web.service
apt-get update
apt-get dist-upgrade -y
systemctl reboot
