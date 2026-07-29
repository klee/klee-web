# Deploying to AWS EC2

`infra/aws/` deploys the complete Compose topology on one public EC2 host. It
creates a VPC, subnet, internet route, security rules, key pair, Elastic IP,
network interface, and an EC2 instance with an encrypted root volume. HTTP and
HTTPS are public. SSH is restricted to one operator IPv4 address.

The deployment stores Redis data on the instance's root volume. Destroying the
infrastructure deletes that data. Terraform state is local and ignored by Git,
so retain `terraform.tfstate` until teardown is complete.

The default TLS adapter obtains a short-lived Let's Encrypt certificate for the
Elastic IP. It has no renewal mechanism. Destroy the deployment or replace the
TLS adapter before the certificate's 160-hour lifetime ends.

## Command contexts

Run commands on the local operator workstation unless a section explicitly says
that they run inside the EC2 host. A local command such as
`ssh ubuntu@"$public_ip" 'command'` opens SSH, runs the quoted command on EC2,
and returns to the local shell. `ssh -t ubuntu@"$public_ip"` instead opens an
interactive EC2 shell. Commands entered there remain remote until `exit`.

## Prerequisites

- Terraform 1.15.x.
- AWS credentials available through the standard AWS SDK credential chain.
- Permission to manage the EC2 and VPC resources in this root.
- An Ed25519 SSH public key. The private key never enters Terraform.
- The operator's current public IPv4 address as a `/32` CIDR.
- Docker Buildx and the GitHub CLI when promoting application images.

The defaults target `eu-west-2`, Availability Zone `eu-west-2a`, and a pinned
Canonical Ubuntu 24.04 AMD64 AMI. When changing Region, set `aws_region`,
`availability_zone`, and `ubuntu_ami_id` together. The selected instance type
must support the requested nested virtualization mode.

### SSH public key

Terraform needs one complete Ed25519 public key, not its SHA-256 fingerprint.
Run these key-selection commands on the local workstation. If the key has a
standard public-key file, export that single line:

```bash
export TF_VAR_ssh_public_key="$(<"$HOME/.ssh/id_ed25519.pub")"
```

If an SSH agent manages the key, list the full public keys exposed by the
currently configured agent:

```bash
ssh-add -L
```

Use `ssh-add -l` to list their SHA-256 fingerprints. If several keys are
available, identify the intended key and export exactly its corresponding
`ssh-ed25519` line. Do not export the complete multi-key output.

Verify the selected public key without reading private material:

```bash
printf '%s\n' "$TF_VAR_ssh_public_key" | ssh-keygen -lf /dev/stdin
```

The fingerprint printed here identifies the operator key registered by
Terraform. It is different from the new EC2 host-key fingerprint shown during
the first SSH connection. The private key remains in its file, hardware token,
or agent and never enters Terraform.

## Plan and apply

On the local workstation, select the intended AWS identity. Obtain the public
IPv4 address that AWS sees for the current connection, then set the remaining
required Terraform input:

```bash
cd infra/aws
export AWS_PROFILE="your-profile"
public_ipv4=$(
  curl -fsS --max-time 10 https://checkip.amazonaws.com |
    tr -d '[:space:]'
)
export TF_VAR_operator_cidr="$public_ipv4/32"
```

The `/32` allows SSH from that address only. Recheck it after changing network
or VPN because the security rule does not follow a later address change.

Initialise Terraform and create a saved plan:

```bash
terraform init
terraform plan -out=aws.tfplan
terraform show aws.tfplan
```

The default root should propose 15 creates with no changes or deletions. Review
the AMI, instance type, encrypted 60 GiB volume, SSH CIDR, public web rules,
Elastic IP, image digests, and nested-virtualization setting before applying it.

Apply the exact reviewed plan:

```bash
terraform apply aws.tfplan
```

Do not recreate a plan between review and apply. Keep the resulting local state
file. Terraform needs it to inspect and destroy the same resources later.

## Prepare and activate

Cloud-init installs Docker, Compose, and gVisor. It proves systrap with a real
container, then selects `runsc-kvm` only if a separate KVM container succeeds.
It pulls the exact application images and provisions TLS, but deliberately does
not start KLEE Web before an administrator password exists.

On the local workstation, read the address and use SSH to run the cloud-init
wait on EC2:

```bash
public_ip=$(terraform output -raw public_ip)
ssh ubuntu@"$public_ip" 'cloud-init status --wait --long'
```

Ubuntu package updates may reboot the host after cloud-init finishes. If SSH
disconnects, wait for it to return and rerun the same cloud-init status command.

Still on the local workstation, create the password through an interactive SSH
terminal. Do not put it on the command line or in Terraform:

```bash
ssh -t ubuntu@"$public_ip" 'sudo /opt/klee-web/set-admin-password.sh'
```

If the helper reports `Host reboot pending`, wait for SSH to return after reboot,
then rerun the same `set-admin-password.sh` command.

The helper stores a bcrypt hash, enables `klee-web.service`, starts Compose, and
waits for service health. Verify the public edge:

```bash
https_url=$(terraform output -raw https_url)
curl -fsS "$https_url/api/ready"
```

Open the HTTPS URL in a browser. Confirm that the certificate is trusted, run a
real KLEE Job, and verify `/admin` with the administrator credentials.

## Operate the host

Enter these commands on the local workstation. SSH runs the quoted systemd and
journal commands on EC2:

```bash
ssh ubuntu@"$public_ip" 'sudo systemctl status klee-web.service'
ssh ubuntu@"$public_ip" 'sudo journalctl -u klee-web.service'
```

Restarting through SSH recreates the full Compose project while preserving the
Redis named volume:

```bash
ssh ubuntu@"$public_ip" 'sudo systemctl restart klee-web.service'
```

Rebooting EC2 restores the service because the administrator helper enabled it.
Use the [shared host-maintenance procedure](host-maintenance.md) for controlled
Ubuntu security updates and post-reboot verification.

Inspect the certificate deadline with:

```bash
ssh ubuntu@"$public_ip" \
  'sudo openssl x509 -in /etc/klee-web/tls/fullchain.pem -noout -dates'
```

## Upgrade and roll back

Application promotion changes only `FRONTEND_IMAGE`, `BACKEND_IMAGE`, and
`RUNNER_IMAGE` in `/etc/klee-web/deployment.env`. Use immutable signed digests.
Resolve one complete three-image publication and verify all three attestations
before editing the host.

### Resolve and verify locally

On the operator workstation, resolve the indexes from one full commit tag:

```bash
commit="FULL_COMMIT_SHA"
frontend_digest=$(
  docker buildx imagetools inspect \
    "ghcr.io/finnleh/klee-web-frontend:sha-$commit" \
    --format '{{.Manifest.Digest}}'
)
backend_digest=$(
  docker buildx imagetools inspect \
    "ghcr.io/finnleh/klee-web-backend:sha-$commit" \
    --format '{{.Manifest.Digest}}'
)
runner_digest=$(
  docker buildx imagetools inspect \
    "ghcr.io/finnleh/klee-web-runner:sha-$commit" \
    --format '{{.Manifest.Digest}}'
)

frontend_image="ghcr.io/finnleh/klee-web-frontend@$frontend_digest"
backend_image="ghcr.io/finnleh/klee-web-backend@$backend_digest"
runner_image="ghcr.io/finnleh/klee-web-runner@$runner_digest"
```

Verify each exact index against this repository's GitHub attestation identity:

```bash
gh attestation verify "oci://$frontend_image" --repo FinnLeh/klee-web
gh attestation verify "oci://$backend_image" --repo FinnLeh/klee-web
gh attestation verify "oci://$runner_image" --repo FinnLeh/klee-web
```

Print the three complete assignments:

```bash
printf 'FRONTEND_IMAGE=%s\nBACKEND_IMAGE=%s\nRUNNER_IMAGE=%s\n' \
  "$frontend_image" "$backend_image" "$runner_image"
```

Keep this local shell open because it contains the verified references. Copy
the three printed lines into the remote file in the next phase.

### Reconcile the EC2 host

From the local workstation, open an interactive shell on EC2:

```bash
ssh -t ubuntu@"$public_ip"
```

The following commands run inside that EC2 shell. First preserve the previous
desired state:

```bash
sudo install -m 0644 \
  /etc/klee-web/deployment.env \
  /etc/klee-web/deployment.env.rollback
```

Open the active file:

```bash
sudoedit /etc/klee-web/deployment.env
```

Replace exactly these three assignments. Each placeholder after `sha256:` must
be replaced by the candidate image's full 64-character OCI index digest copied
from the local verified references:

```dotenv
FRONTEND_IMAGE=ghcr.io/finnleh/klee-web-frontend@sha256:FRONTEND_INDEX_DIGEST
BACKEND_IMAGE=ghcr.io/finnleh/klee-web-backend@sha256:BACKEND_INDEX_DIGEST
RUNNER_IMAGE=ghcr.io/finnleh/klee-web-runner@sha256:RUNNER_INDEX_DIGEST
```

Leave every other deployment value unchanged. Pull the selected images before
asking systemd to reconcile them:

```bash
sudo /opt/klee-web/pull-images.sh
sudo systemctl reload klee-web.service
```

The pull must succeed before reload. Run `exit` after reload to return to the
local shell. From there, verify readiness, the active image references, Redis
state, and a real uncached Job. Do not prune the old images during this check.

This edit changes the running host only. For a deliberate future instance
replacement, supply the accepted references through Terraform's
`frontend_image`, `backend_image`, and `runner_image` variables. Changing those
first-boot inputs in Terraform proposes instance replacement rather than an
in-place upgrade.

Rollback starts by opening the EC2 shell again from the local workstation:

```bash
ssh -t ubuntu@"$public_ip"
```

Inside EC2, restore the preserved references and reload without pulling:

```bash
sudo install -m 0644 \
  /etc/klee-web/deployment.env.rollback \
  /etc/klee-web/deployment.env
sudo systemctl reload klee-web.service
```

This rollback does not depend on the registry while the old images remain on
the host. Run `exit`, then repeat the health, state, and Job checks from the
local workstation after reconciliation.

## Destroy

On the local workstation, return to `infra/aws`. Capture any required
operational or cost evidence first. Then create and review a saved destroy plan:

```bash
terraform plan -destroy -out=destroy.tfplan
terraform show destroy.tfplan
```

The plan must contain only deletions for resources owned by this state. Apply
that exact plan:

```bash
terraform apply destroy.tfplan
terraform state list
```

`terraform state list` should return no resources. Independently query AWS or
use its console to confirm that no instance, EBS volume, network interface,
Elastic IP, snapshot, load balancer, NAT gateway, or other billable resource
from the deployment remains. Billing data can lag resource deletion.
