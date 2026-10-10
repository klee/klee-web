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
  domain. Its webroot mode also renews and activates certificates.
- `klee-web-tls-renew.service` and its timer check for renewal twice daily after
  the webroot setup below has passed acceptance.
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
public service. Standalone TLS provisioning copies Certbot's certificate targets
to stable files. Webroot renewal uses the staged certificate directories below.

Controlled Ubuntu updates use the shared
[`host-maintenance.md`](host-maintenance.md) procedure. Application upgrades
continue to use exact frontend, backend, and Runner image digests in the host's
deployment configuration.

## Automatic TLS renewal

Certbot checks twice daily. It renews only when the certificate approaches expiry,
not after it expires. nginx keeps serving the old valid certificate while
Certbot obtains the replacement. No application or Worker restart is required
for routine renewal.

The optional `deploy/compose.acme.yml` overlay mounts two host directories into
nginx. The challenge directory is read-only in nginx and writable in Certbot.
It contains only temporary HTTP-01 proof files. The certificate directory is
also read-only in nginx. It contains staged production certificate/key pairs
selected by a `current` symlink. This directory mount avoids retaining an old
inode when a host replaces an individually bind-mounted certificate file.

The TLS helper validates the hostname, remaining validity, trust chain, and
matching key before selecting a new pair. It checks nginx's configuration,
reloads nginx, and verifies the certificate actually served on port 443. Failed
activation restores the previous selection. Successful activation retains only
the current and previous installed pairs. Certbot retains its own certificate
history separately under `/etc/letsencrypt`.

TLS operations and Compose start/stop share a host lock. An overlapping
operation fails without changing the deployment and can be retried later.
Renewal failures appear in the systemd journal and failed service state. This
does not provide an external alert or guarantee renewal through a prolonged
network outage. The timer retries at its next scheduled check.

### One-time installation on web/state

Use a checkout of the reviewed revision on the web/state host. First verify the
new frontend image's signed immutable digest using the
[application upgrade procedure](aws-multi-vm.md#promote-and-roll-back-images).
The image must include the HTTP challenge route. Do not change backend or
Runner digests solely for this TLS update.

Back up `/etc/klee-web/deployment.env` with its existing permissions. Keep the
previous frontend image cached. Add these two settings to that file and replace
only `FRONTEND_IMAGE` with the verified new digest:

```text
ACME_WEBROOT_DIRECTORY=/var/lib/klee-web/acme
TLS_CERTIFICATE_DIRECTORY=/etc/klee-web/tls/nginx
```

Keep the existing `TLS_CERTIFICATE_FILE` and `TLS_PRIVATE_KEY_FILE` settings.
They are still needed by the base production overlay and by rollback.

Install the files from the reviewed checkout:

```bash
sudo install -m 0755 deploy/compose-deployment.sh /opt/klee-web/compose-deployment.sh
sudo install -m 0644 deploy/compose.acme.yml /opt/klee-web/compose.acme.yml
sudo install -m 0755 infra/doc/provision-tls.sh /opt/klee-web/provision-tls.sh
sudo install -m 0644 infra/doc/klee-web-tls-renew.service /etc/systemd/system/
sudo install -m 0644 infra/doc/klee-web-tls-renew.timer /etc/systemd/system/

sudo env ACME_WEBROOT_DIRECTORY=/var/lib/klee-web/acme \
  TLS_CERTIFICATE_DIRECTORY=/etc/klee-web/tls/nginx \
  /opt/klee-web/provision-tls.sh prepare-webroot

sudo /opt/klee-web/compose-deployment.sh config
sudo /opt/klee-web/compose-deployment.sh pull
sudo systemctl reload klee-web.service
```

`prepare-webroot` stages the existing production certificate and pulls the
existing pinned Certbot image. It does not issue a certificate. The initial
Compose reload recreates nginx to add the mounts, so expect a brief interruption
while nginx starts. Redis and FastAPI keep their existing configuration. Later
certificate renewal uses an nginx reload without container recreation.

Check the challenge route before changing Certbot's saved renewal settings:

```bash
printf 'klee-web-acme-check\n' | sudo tee \
  /var/lib/klee-web/acme/.well-known/acme-challenge/klee-web-check >/dev/null
curl -fsS http://klee.doc.ic.ac.uk/.well-known/acme-challenge/klee-web-check
curl -sSI http://klee.doc.ic.ac.uk/
sudo rm /var/lib/klee-web/acme/.well-known/acme-challenge/klee-web-check
```

The first request must return `klee-web-acme-check` without a redirect. The
second must redirect to HTTPS. Repeat the challenge request from outside the
institutional network to check the public port-80 path.

Switch the existing standalone renewal configuration to webroot, then test it:

```bash
sudo env ACME_WEBROOT_DIRECTORY=/var/lib/klee-web/acme \
  TLS_CERTIFICATE_DIRECTORY=/etc/klee-web/tls/nginx \
  /opt/klee-web/provision-tls.sh reconfigure

sudo env ACME_WEBROOT_DIRECTORY=/var/lib/klee-web/acme \
  TLS_CERTIFICATE_DIRECTORY=/etc/klee-web/tls/nginx \
  /opt/klee-web/provision-tls.sh dry-run
```

`reconfigure` tests against Let's Encrypt staging and saves the new method only
on success. Neither command activates a staging certificate. If either fails,
leave the timer disabled and fix validation before continuing.

After both staging checks succeed, enable the timer without starting the renewal
service manually. Its first scheduled run tests the complete automated path:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now klee-web-tls-renew.timer
systemctl list-timers --all klee-web-tls-renew.timer
```

The timer schedules checks around midnight and noon with up to one hour of
random delay. `Persistent=true` catches a missed scheduled check after reboot.
It uses calendar times, not an interval starting from activation. A catch-up
check may run shortly after installation. Until a timer-triggered check passes,
renewal is installed but not verified end-to-end.

After the timer fires, inspect the service result. The oneshot service returns
to inactive after success. Use its exit status and journal, not an `active`
state, to judge success:

```bash
sudo journalctl -u klee-web-tls-renew.service --no-pager -n 60
systemctl show klee-web-tls-renew.service -p Result -p ExecMainStatus
```

Expect `Result=success` and `ExecMainStatus=0`. Then verify the publicly served
expiry and inspect the website manually:

```bash
openssl s_client -connect klee.doc.ic.ac.uk:443 -servername klee.doc.ic.ac.uk \
  </dev/null 2>/dev/null | openssl x509 -noout -dates -fingerprint -sha256
```

An already-due certificate should now have a later expiry. A certificate not
yet due should remain unchanged. Check the app and authenticated admin page.

### Failure and rollback

If a production check fails, inspect
`journalctl -u klee-web-tls-renew.service`. Failed renewal leaves the installed
certificate unchanged. Failed activation restores the previous installed pair
and attempts to reload it. A reload failure is reported, not treated as success.

For rollout rollback, disable and stop `klee-web-tls-renew.timer`, then wait for
any running renewal service to finish. Validate the currently selected certificate
and copy its pair to the legacy paths before restoring the old mounts:

```bash
sudo openssl x509 -in /etc/klee-web/tls/nginx/current/fullchain.pem \
  -noout -checkhost klee.doc.ic.ac.uk -checkend 86400 &&
sudo install -m 0644 /etc/klee-web/tls/nginx/current/fullchain.pem \
  /etc/klee-web/tls/fullchain.pem &&
sudo install -m 0600 /etc/klee-web/tls/nginx/current/privkey.pem \
  /etc/klee-web/tls/privkey.pem
```

Stop if validation fails. Do not restore an expired certificate. Restore the
backed-up deployment configuration and reload `klee-web.service`. This removes
the optional mounts and returns to the previous frontend image with the current
certificate pair. It also returns renewal responsibility to the operator.

### Local regression checks

```bash
make test-tls
make test-tls-nginx TLS_NGINX_IMAGE=klee-web-frontend
```

The first uses temporary trusted certificates and a simulated Certbot/Docker
boundary. It covers no-op checks, dry runs, invalid candidates, activation
failure, rollback, and installed-pair retention. The second needs an existing
frontend image and tests real nginx routing and certificate rotation through a
directory mount without recreating the container. Neither contacts Let's
Encrypt. CI runs both. A successful live staging test and manual website check
remain installation acceptance requirements.
