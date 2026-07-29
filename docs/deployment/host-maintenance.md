# Host maintenance

KLEE Web disables unattended package installation so host maintenance cannot
restart services at an unpredictable time. Deployment operators remain responsible
for applying security updates regularly. A weekly window is a reasonable starting
point for a public deployment, with earlier maintenance for critical vulnerabilities.

Ordinary host maintenance updates Ubuntu packages. Docker Engine, Docker CLI,
containerd, Docker Compose, and gVisor remain pinned for separate review.

## Before maintenance

Use an announced outage for a single-VM deployment or the web/state host. Before
updating a Worker in a multi-Worker deployment, confirm that a peer is available.
The Worker's graceful stop finishes active Jobs and returns reserved Jobs to Redis
before updating the host.

## Update one host

Connect to the target host using the SSH command from its provider guide. Start the
installed maintenance script as a transient systemd service:

```bash
sudo systemd-run \
  --unit=klee-web-maintenance \
  --collect \
  /opt/klee-web/maintain-host.sh
```

The transient service continues if SSH disconnects. It stops the local KLEE Web
service, updates Ubuntu, and reboots the host. Follow it until the reboot disconnects
SSH:

```bash
sudo journalctl -fu klee-web-maintenance.service
```

`Ctrl+C` stops following the journal but does not stop maintenance. Do not start
maintenance on another host while this operation is still running.

If the host does not reboot, inspect the completed unit's journal:

```bash
sudo journalctl -u klee-web-maintenance.service
```

A failed service stop prevents package installation. A failed package operation
leaves KLEE Web stopped. Correct the reported failure, then either rerun maintenance
or explicitly restore `klee-web.service` before touching another host.

## Verify after reboot

Reconnect after SSH returns. The enabled `klee-web.service` starts automatically
after Docker and networking. Confirm the service and its Compose role are active:

```bash
sudo systemctl is-active klee-web.service
sudo /opt/klee-web/compose-deployment.sh ps
```

On a single-VM or Worker host, test the exact gVisor runtime selected during
bootstrap:

```bash
. /etc/klee-web/runtime.env
sudo docker run --rm --pull=never \
  --runtime="$KLEE_RUNTIME" \
  --network=none \
  --read-only \
  hello-world@sha256:d1a8d0a4eeb63aff09f5f34d4d80505e0ba81905f36158cc3970d8e07179e59e
```

If `runsc-kvm` fails, test the required systrap runtime:

```bash
sudo docker run --rm --pull=never \
  --runtime=runsc \
  --network=none \
  --read-only \
  hello-world@sha256:d1a8d0a4eeb63aff09f5f34d4d80505e0ba81905f36158cc3970d8e07179e59e
```

When systrap passes, select it and reconcile the service:

```bash
printf 'KLEE_RUNTIME=runsc\n' | sudo tee /etc/klee-web/runtime.env >/dev/null
sudo systemctl restart klee-web.service
```

If systrap also fails, stop the service and leave that execution host unavailable.
Do not update another host until the sandbox failure is understood:

```bash
sudo systemctl stop klee-web.service
```

For a role-separated deployment, confirm fleet membership from the admin dashboard
or run this command on the web/state host:

```bash
sudo docker exec klee-web-api-1 \
  celery -A klee_web.celery_app inspect ping --timeout=3
```

The expected stable Worker name must reply before maintenance advances.

## Role-separated order

First update Worker 1 using this host procedure. Complete every post-reboot check
and confirm Worker 1 has rejoined before updating Worker 2. Repeat for every further
Worker. Updating one Worker reduces execution capacity while its peers remain
available. A deployment with one Worker has an execution outage instead.

### Stop Workers before web/state

`maintain-host.sh` controls only the host on which it runs. Running it on web/state
does not stop remote Worker services.

Before web/state maintenance, connect to Worker 1 using the provider guide's Worker
SSH command. Run this inside the Worker:

```bash
sudo systemctl stop klee-web.service
sudo systemctl show klee-web.service --property=ActiveState --value
```

The stop command waits for active Jobs to finish. Celery returns unacknowledged
reserved Jobs to Redis when its broker connection closes. The final command must
print `inactive`.

During warm shutdown, the admin dashboard can briefly show zero waiting Jobs after a
Worker stops responding but before its reserved messages move from Redis's `unacked`
state back to the visible queue.

Repeat these commands on Worker 2 and every further Worker. The queue does not need
to be empty. New and returned Jobs remain pending in Redis while all Workers are
stopped.

### Update web/state

After every Worker reports `inactive`, connect to web/state and run the
`systemd-run` maintenance command from **Update one host**. nginx, FastAPI, and Redis
remain unavailable until that host reboots. The Redis AOF preserves queued Jobs
across its clean shutdown and reboot.

### Restore Workers

After web/state returns, confirm API readiness and Redis state. Connect to Worker 1
and run:

```bash
sudo systemctl start klee-web.service
sudo systemctl is-active klee-web.service
```

Repeat on Worker 2 and every further Worker. Run the fleet inspection from
**Verify after reboot**, confirm every stable Worker identity, then submit one
uncached Job. Pending Jobs resume when the Worker services start.

Web/state maintenance interrupts the whole application because nginx, FastAPI, and
Redis are not replicated.

For a single-VM deployment, run the same host update during an announced outage.
After reboot, verify systemd, Compose, gVisor, API readiness, Redis state, and one
uncached Job.
