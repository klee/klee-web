# Institutional deployment adapter

`infra/doc/` contains the host-specific additions for the maintained Department
of Computing deployment. It does not provision machines. The VMs and network
access are allocated by the institution before the shared deployment lifecycle
is installed.

## Placement

The deployment uses one web/state VM for nginx, FastAPI, and persistent Redis.
Three Worker VMs connect to Redis over the private institutional network. Each
Worker keeps its Docker daemon, gVisor runtime, and transient Runner containers
local. The placement matches the role-separated topology in
[`architecture.md`](../architecture.md).

The common files under `deploy/` still own image pulls, Compose rendering,
systemd lifecycle, and host maintenance. `infra/doc/` adds only the parts that
cannot be derived from a provider API:

- `provision-tls.sh` obtains and installs the certificate for the maintained
  domain.
- `configure-redis-firewall.sh` resolves the known Worker hostnames and permits
  their Redis traffic on the institutional network interface.
- `klee-web-redis-firewall.service` restores that firewall policy after Docker
  starts and before KLEE Web starts.
- `klee-web-redis-firewall.conf` makes the main service depend on the firewall
  unit.

## Fixed assumptions

The domain, Worker hostnames, and network interface in `infra/doc/` belong to
this deployment. They are source values because the institution allocates the
hosts outside Terraform. A different allocation requires those values to be
reviewed and changed before installation.

The Redis firewall inserts Worker allow rules before a deny rule in Docker's
`DOCKER-USER` chain. Redis remains on the web/state VM and is not exposed as a
public service. The TLS helper copies Certbot's rotating certificate targets to
stable files with modes suitable for the nginx container.

Controlled Ubuntu updates use the shared
[`host-maintenance.md`](host-maintenance.md) procedure. Application upgrades
continue to use exact frontend, backend, and Runner image digests in the host's
deployment configuration.
