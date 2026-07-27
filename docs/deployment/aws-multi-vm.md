# Deploying role-separated KLEE Web to AWS EC2

`infra/aws-multi-vm/` deploys one public web/state VM and one or two private
Worker VMs in a dedicated VPC. The web VM runs nginx, FastAPI, and persistent
Redis. Each Worker VM runs one Celery Worker, its local Docker daemon, gVisor,
and transient Runner containers.

The root has independent Terraform state from `infra/aws/`. Selecting this root
does not convert or share state with the single-VM deployment.

```text
Internet
  |
  v
web Elastic IP -> nginx -> FastAPI -> Redis volume
                                  ^
                                  |
                     private Redis and Celery traffic
                                  |
                      +-----------+-----------+
                      |                       |
                 Worker VM 1             Worker VM 2
                 Docker + gVisor          Docker + gVisor
```

Only TCP 80 and 443 are public application ingress. SSH to the web host is
restricted to one operator `/32`. Workers have no public IPv4 addresses. Their
SSH ingress accepts only the web security group, and Redis accepts only the
Worker security group on the web VM's private address.

Redis uses the isolated VPC and security-group boundary without Redis
authentication or application-level TLS. Do not transfer that trust decision to
a shared network without reviewing its isolation controls.

Terraform state is local and ignored by Git. Retain it until teardown is
complete. Destroying the web VM deletes the Redis volume and all application
state.

## Prerequisites

- Terraform 1.15.x.
- AWS credentials through the standard AWS SDK credential chain.
- Permission to manage the EC2 and VPC resources in this root.
- An Ed25519 public key. The private key never enters Terraform.
- The operator's current public IPv4 address as a `/32` CIDR.
- `jq` for reading Worker maps from Terraform output.

Defaults select `eu-west-2`, `eu-west-2a`, a pinned Canonical Ubuntu 24.04 AMD64
AMI, a `t3.small` web VM with a 20 GiB encrypted gp3 root volume, and
`m7i-flex.large` Worker VMs with 32 GiB encrypted gp3 root volumes. The web VM
uses standard CPU credits. Every Worker uses the same instance type and Runner
Caps. `worker_count` is constrained to one or two.

The Worker instance type must support the requested nested-virtualization mode.
Bootstrap still proves systrap first and selects `runsc-kvm` only after a real
KVM container succeeds.

## Operator inputs

Run commands in this guide from `infra/aws-multi-vm/` unless stated otherwise.
Select the intended AWS identity and export the public half of the SSH key held
by the local agent or key store:

```bash
export AWS_PROFILE="your-profile"
export TF_VAR_ssh_public_key="ssh-ed25519 PUBLIC_KEY_MATERIAL"
public_ipv4=$(
  curl -fsS --max-time 10 https://checkip.amazonaws.com |
    tr -d '[:space:]'
)
export TF_VAR_operator_cidr="$public_ipv4/32"
```

Verify the selected key without reading private material:

```bash
printf '%s\n' "$TF_VAR_ssh_public_key" | ssh-keygen -lf /dev/stdin
```

Recheck the operator address after changing network or VPN. The SSH rule does
not follow a later address change.

## Plan the initial topology

Initialise the independent root and create a saved plan with one Worker:

```bash
terraform init
terraform plan -out=initial.tfplan
terraform show initial.tfplan
```

With default inputs, the plan is expected to propose 25 creates with no changes
or deletions. Review all of the following before apply:

- One VPC and internet gateway.
- One public and one private subnet in the selected Availability Zone.
- One web Elastic IP and one NAT Elastic IP.
- One NAT gateway and a private default route through it.
- One web security group and one Worker security group.
- Public HTTP and HTTPS only on the web security group.
- Operator `/32` SSH only on the web security group.
- Worker SSH only from the web security group.
- Redis only from the Worker security group.
- One `t3.small` web instance with an encrypted 20 GiB disk.
- One `m7i-flex.large` `klee-worker-1` with an encrypted 32 GiB disk.
- No public IPv4 assignment on the Worker.
- Nested virtualization on the Worker only.
- Exact immutable frontend, backend, and Runner image digests.

Do not apply a plan containing an unexpected public rule, address, instance, or
replacement.

## Apply and wait for preparation

Apply the exact reviewed plan:

```bash
terraform apply initial.tfplan
```

Read the generated addresses:

```bash
public_ip=$(terraform output -raw public_ip)
web_private_ip=$(terraform output -raw web_private_ip)
worker_1_ip=$(
  terraform output -json worker_private_ips |
    jq -r '.["klee-worker-1"]'
)
```

Wait for cloud-init on the web VM and private Worker:

```bash
ssh ubuntu@"$public_ip" 'cloud-init status --wait --long'
ssh -J ubuntu@"$public_ip" ubuntu@"$worker_1_ip" \
  'cloud-init status --wait --long'
```

The web role installs Docker, skips unused gVisor setup, pulls Redis, backend,
and frontend images, then provisions the short-lived public-IP certificate. It
does not start KLEE Web before an administrator password exists.

The Worker role installs Docker and gVisor, probes systrap and optional KVM,
pulls the backend and Runner images, and enables its Worker service. The Celery
process may wait for its broker until web activation starts Redis.

## Activate the web role

Create the administrator password through an interactive terminal. Do not put
the password in Terraform, shell history, or a command argument:

```bash
ssh -t ubuntu@"$public_ip" \
  'sudo /opt/klee-web/set-admin-password.sh'
```

The helper writes the bcrypt hash, enables the web service, and starts Redis,
FastAPI, and nginx. Verify the edge and API:

```bash
https_url=$(terraform output -raw https_url)
curl -fsS "$https_url/api/ready"
```

Open the HTTPS URL in a browser. Confirm the certificate is trusted, submit a
real uncached KLEE Job, and verify the authenticated `/admin` page reports
`celery@klee-worker-1` with maximum capacity one.

## Verify role ownership

Inspect the web project:

```bash
ssh ubuntu@"$public_ip" \
  'sudo /opt/klee-web/compose-deployment.sh ps'
```

Only Redis, API, and nginx should be present. The web runtime file should contain
an empty KLEE runtime because this host never launches Runners:

```bash
ssh ubuntu@"$public_ip" 'sudo cat /etc/klee-web/runtime.env'
```

Inspect Worker 1 through the bastion:

```bash
ssh -J ubuntu@"$public_ip" ubuntu@"$worker_1_ip" \
  'sudo /opt/klee-web/compose-deployment.sh ps'
ssh -J ubuntu@"$public_ip" ubuntu@"$worker_1_ip" \
  'sudo cat /etc/klee-web/runtime.env && sudo docker volume ls'
```

Only the Worker service should be present. Its runtime must be `runsc` or
`runsc-kvm`. It must not own a `klee-web_redis-data` volume.

Prove that the Worker can reach private Redis through its configured URL:

```bash
ssh -J ubuntu@"$public_ip" ubuntu@"$worker_1_ip" \
  'sudo docker compose --project-name klee-web \
    -f /opt/klee-web/docker-compose.yml \
    -f /opt/klee-web/compose.worker.yml \
    exec -T worker python -c '\''import os; from redis import Redis; print(Redis.from_url(os.environ["REDIS_URL"]).ping())'\'''
```

On the web host, Redis must listen on the declared private address rather than
all interfaces:

```bash
ssh ubuntu@"$public_ip" 'sudo ss -ltnp | grep 6379'
```

From the operator workstation, public connections to Redis and FastAPI's direct
port must fail. Public HTTPS must continue to succeed.

```bash
if timeout 5 bash -c "</dev/tcp/$public_ip/6379"; then
  printf 'Redis is unexpectedly public\n' >&2
  exit 1
fi
if timeout 5 bash -c "</dev/tcp/$public_ip/8000"; then
  printf 'FastAPI is unexpectedly public\n' >&2
  exit 1
fi
curl -fsS "$https_url/api/ready"
```

## Scale from one Worker to two

Create a saved plan that changes only the controlled Worker count:

```bash
export TF_VAR_worker_count=2
terraform plan -out=scale-out.tfplan
terraform show scale-out.tfplan
```

Keep `TF_VAR_worker_count=2` set for every later plan in this deployment. An
ordinary plan using the default value of one would correctly propose removing
Worker 2.

The plan is expected to add only `aws_instance.worker["klee-worker-2"]`.
It must not replace Worker 1 or change the web VM, network, Redis volume, routes,
or security groups. Apply the reviewed plan:

```bash
terraform apply scale-out.tfplan
```

Read the second private address and wait for preparation:

```bash
worker_2_ip=$(
  terraform output -json worker_private_ips |
    jq -r '.["klee-worker-2"]'
)
ssh -J ubuntu@"$public_ip" ubuntu@"$worker_2_ip" \
  'cloud-init status --wait --long'
```

The admin page should show both stable Worker names without restarting or
changing the web VM. Submit two cache-distinct, replay-heavy Jobs concurrently.
Observe one active Runner on each Worker. A third unique Job must remain queued
until a slot becomes free.

## Failure and recovery checks

Each Worker service has its own systemd and Docker restart boundary. Reboot one
idle Worker and verify that it rejoins without changing Redis state or the web
VM.

An active Job is acknowledged when a Worker receives it. Destroying that Worker
does not automatically redeliver the Job. The expected recovery is:

1. Confirm the peer Worker still accepts new Jobs.
2. Cancel the stranded Job through the public UI or API.
3. Confirm its terminal state is `cancelled`.
4. Resubmit it to the surviving fleet.
5. Reapply Terraform and verify only the missing Worker is replaced.

This is user recovery from accepted at-most-once delivery, not automatic
failover. The web VM and Redis also remain single points of failure.

## Operate each role

Inspect the web service directly:

```bash
ssh ubuntu@"$public_ip" 'sudo systemctl status klee-web.service'
ssh ubuntu@"$public_ip" 'sudo journalctl -u klee-web.service'
```

Inspect a Worker through the bastion:

```bash
ssh -J ubuntu@"$public_ip" ubuntu@"$worker_1_ip" \
  'sudo systemctl status klee-web.service'
ssh -J ubuntu@"$public_ip" ubuntu@"$worker_1_ip" \
  'sudo journalctl -u klee-web.service'
```

Restarting or rebooting a Worker affects only that execution host. Restarting
the web service recreates Redis, API, and nginx while preserving the named Redis
volume. Rebooting the web VM restores those services because the administrator
helper enabled the unit.

## Promote and roll back images

Verify one complete signed frontend, backend, and Runner image set before
changing any host. Preserve `/etc/klee-web/deployment.env` as
`deployment.env.rollback` on the web VM and every Worker.

Update Worker 1 first. On the local workstation, open an interactive session
through the web bastion:

```bash
ssh -t -J ubuntu@"$public_ip" ubuntu@"$worker_1_ip"
```

The following commands run inside Worker 1. Preserve the current environment,
edit its three image assignments, pull only the images owned by that role, then
reload and exit:

```bash
sudo install -m 0644 \
  /etc/klee-web/deployment.env \
  /etc/klee-web/deployment.env.rollback
sudoedit /etc/klee-web/deployment.env
sudo /opt/klee-web/pull-images.sh
sudo systemctl reload klee-web.service
exit
```

Verify Worker 1 rejoins, then repeat the same remote commands on Worker 2 by
connecting to `"$worker_2_ip"`. After both Workers are available, connect to the
web host and run the same remote commands there:

```bash
ssh -t ubuntu@"$public_ip"
```

The web role pulls only its frontend and backend images. Confirm API readiness,
both Worker identities, Redis state, and one real uncached Job after exiting. Do
not prune the previous images during this check.

Rollback uses the same Worker 1, Worker 2, then web order. Open an interactive
session to each host as above, then run these commands inside that host:

```bash
sudo install -m 0644 \
  /etc/klee-web/deployment.env.rollback \
  /etc/klee-web/deployment.env
sudo systemctl reload klee-web.service
exit
```

This remains offline-capable while the old images are present.

Editing host environments performs an in-place operational promotion. Changing
Terraform image variables changes first-boot user data and proposes instance
replacement, so reserve that path for deliberate replacement.

## Destroy

Capture required operational and cost evidence first. Create and inspect a saved
destroy plan:

```bash
terraform plan -destroy -out=destroy.tfplan
terraform show destroy.tfplan
```

The default one-Worker topology should contain 25 deletions. The scaled topology
should contain 26. Apply only the reviewed plan:

```bash
terraform apply destroy.tfplan
terraform state list
```

`terraform state list` must return no resources. Independently verify that no
EC2 instance, EBS volume, Elastic IP, NAT gateway, network interface, route,
security group, subnet, internet gateway, snapshot, load balancer, or experiment
VPC remains. NAT gateways and unattached Elastic IPs are billable, so do not rely
on empty Terraform state as the only teardown check.

The default TLS certificate is short-lived and has no renewal mechanism. Destroy
the experiment or replace its TLS procedure before the certificate expires.
