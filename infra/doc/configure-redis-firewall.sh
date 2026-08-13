#!/usr/bin/env bash
set -euo pipefail

readonly WORKER_HOSTS=(
  'cloud-vm-41-158.doc.ic.ac.uk'
  'cloud-vm-44-07.doc.ic.ac.uk'
  'cloud-vm-44-08.doc.ic.ac.uk'
)
readonly NETWORK_INTERFACE='ens7'
readonly REDIS_PORT='6379'

if ((EUID != 0)); then
  printf 'configure-redis-firewall.sh must run as root\n' >&2
  exit 1
fi

if [[ ! -d /sys/class/net/$NETWORK_INTERFACE ]]; then
  printf 'Network interface is missing: %s\n' "$NETWORK_INTERFACE" >&2
  exit 1
fi

deny_rule=(
  --in-interface "$NETWORK_INTERFACE"
  --protocol tcp
  --destination-port "$REDIS_PORT"
  --match comment
  --comment klee-web-redis-deny
  --jump DROP
)

worker_ips=()
for worker_host in "${WORKER_HOSTS[@]}"; do
  worker_ip=$(
    getent ahostsv4 "$worker_host" \
      | awk '$2 == "STREAM" { print $1; exit }'
  )
  if [[ ! $worker_ip =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    printf 'Worker hostname did not resolve to one IPv4 address: %s\n' "$worker_host" >&2
    exit 1
  fi
  worker_ips+=("$worker_ip")
done

if ! iptables --wait --check DOCKER-USER "${deny_rule[@]}" 2>/dev/null; then
  iptables --wait --append DOCKER-USER "${deny_rule[@]}"
fi

for index in "${!WORKER_HOSTS[@]}"; do
  worker_host=${WORKER_HOSTS[$index]}
  worker_ip=${worker_ips[$index]}
  allow_rule=(
    --in-interface "$NETWORK_INTERFACE"
    --source "$worker_ip/32"
    --protocol tcp
    --destination-port "$REDIS_PORT"
    --match comment
    --comment klee-web-redis-worker
    --jump ACCEPT
  )
  if ! iptables --wait --check DOCKER-USER "${allow_rule[@]}" 2>/dev/null; then
    iptables --wait --insert DOCKER-USER 1 "${allow_rule[@]}"
  fi

  printf 'Redis ingress allows %s at %s\n' "$worker_host" "$worker_ip"
done

printf 'Redis ingress drops other %s sources\n' "$NETWORK_INTERFACE"
