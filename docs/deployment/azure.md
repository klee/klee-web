# Deploying to Azure

`infra/azure/` deploys the complete Compose topology on one public Azure VM. It
creates a resource group, virtual network, subnet, network security group and
rules, static public IPv4 address, network interface, and Linux VM with a managed
OS disk. HTTP and HTTPS are public. SSH is restricted to one operator IPv4
address.

The deployment stores Redis data on the VM's OS disk. Destroying the VM and disk
deletes that data. Terraform state is local and ignored by Git, so retain
`terraform.tfstate` until teardown is complete.

The Azure TLS adapter obtains a short-lived Let's Encrypt certificate for the
static public IP. It has no renewal mechanism. Destroy the deployment or replace
the adapter before the certificate's 160-hour lifetime ends.

## Command contexts

Run commands on the local operator workstation unless a section explicitly says
that they run inside the Azure VM. A local command such as
`ssh ubuntu@"$public_ip" 'command'` opens SSH, runs the quoted command remotely,
and returns to the local shell. `ssh -t ubuntu@"$public_ip"` instead opens an
interactive remote shell. Commands entered there remain remote until `exit`.

## Prerequisites

- Terraform 1.15.x.
- Azure CLI authenticated interactively with `az login`.
- Permission to manage Compute, Network, and resource-group resources in the
  selected subscription.
- An Ed25519 SSH public key. The private key never enters Terraform.
- The operator's current public IPv4 address as a `/32` CIDR.

The defaults target `polandcentral`, `Standard_B2as_v2`, a 32 GiB Standard SSD,
and the pinned Canonical Ubuntu 24.04 AMD64 image
`Canonical:ubuntu-24_04-lts:server:24.04.202607140`. The default Region reflects
the observed Azure for Students policy and quota. The selected burstable AMD host
meets the deployment minimum of two x64 vCPUs and 8 GiB RAM but is not intended to
match AWS hardware or performance. When changing Region, first verify subscription
policy, family quota, SKU restrictions, and image availability together.

### Select the subscription

Azure CLI can expose several subscriptions and may select an unrelated one after
login. Select and verify the intended subscription before every plan session:

```bash
az account set --subscription "Azure for Students"
test "$(az account show --query name --output tsv)" = "Azure for Students"
export TF_VAR_subscription_id="$(az account show --query id --output tsv)"
```

AzureRM requires the subscription UUID explicitly so a reviewed plan cannot
silently follow a later CLI default change. The UUID remains in the local shell,
plan, and state; do not place it in a committed `.tfvars` file or evidence record.
The provider is configured not to register unrelated Azure resource providers.

New subscriptions may not have the two required service APIs enabled. Register
only those namespaces once before planning:

```bash
az provider register \
  --subscription "$TF_VAR_subscription_id" \
  --namespace Microsoft.Compute \
  --wait
az provider register \
  --subscription "$TF_VAR_subscription_id" \
  --namespace Microsoft.Network \
  --wait
```

Registration is non-billable and grants no RBAC permission. It enables the VM and
network APIs for principals that already have permission.

### SSH public key

Terraform needs one complete Ed25519 public key, not its SHA-256 fingerprint. If
the key has a standard public-key file, export that single line:

```bash
export TF_VAR_ssh_public_key="$(<"$HOME/.ssh/id_ed25519.pub")"
```

If an SSH agent manages the key, use `ssh-add -L` to list its complete public
keys and export exactly the intended `ssh-ed25519` line. Verify the selected key:

```bash
printf '%s\n' "$TF_VAR_ssh_public_key" | ssh-keygen -lf /dev/stdin
```

The private key remains in its file, hardware token, or agent and never enters
Terraform.

## Plan and apply

On the local workstation, obtain the public IPv4 address seen for the current
connection and set the remaining required input:

```bash
public_ipv4=$(curl -fsS --max-time 10 https://api.ipify.org)
export TF_VAR_operator_cidr="$public_ipv4/32"
cd infra/azure
```

The `/32` permits SSH only from that address. Recheck it after changing network
or VPN because the security rule does not follow a later address change.

Initialise Terraform and create a saved plan:

```bash
terraform init
terraform plan -out=azure.tfplan
terraform show azure.tfplan
```

Planning reads the pinned Marketplace image and existing subscription but creates
no Azure resource. The default empty-state plan should propose 12 creates with no
changes or deletions. Review all of these controls:

- The resource group and every resource use `polandcentral`.
- The image is Canonical Ubuntu `24.04.202607140`, x64 generation V2.
- The VM is `Standard_B2as_v2` with regular priority and burstable CPU credits.
- The encrypted managed OS disk is 32 GiB `StandardSSD_LRS` and is deleted with
  the VM.
- The public IP is static, Standard, IPv4, and attached directly to the host NIC.
- The supported Basv2 NIC has Accelerated Networking enabled and the subnet disables
  Azure's implicit default outbound address.
- Only ports 80 and 443 are public; port 22 uses the operator `/32`.
- The frontend, backend, and Runner references are the reviewed immutable OCI
  digests.
- Secure Boot and vTPM are disabled under the Standard security profile. Bootstrap
  proves `runsc` and selects `runsc-kvm` only if an independent real container
  succeeds; the B-series host is expected to retain the portable `runsc` path.

Apply only the exact reviewed plan:

```bash
terraform apply azure.tfplan
```

Do not recreate a plan between review and apply. Keep the resulting local state
file. Terraform needs it to inspect and destroy the same resources later. The
first VM allocation is also the definitive subscription quota and physical
capacity check.

## Prepare and activate

Cloud-init installs Docker, Compose, and gVisor. It proves systrap with a real
container, then selects `runsc-kvm` only if a separate KVM container succeeds. An
absent `/dev/kvm` is a supported outcome and selects `runsc`. Cloud-init then
pulls the exact application images and provisions TLS, but deliberately does not
start KLEE Web before an administrator password exists.

On the local workstation, read the address and wait for cloud-init on the VM:

```bash
public_ip=$(terraform output -raw public_ip)
ssh ubuntu@"$public_ip" 'cloud-init status --wait --long'
```

Ubuntu package updates may reboot the host after cloud-init finishes. If SSH
disconnects, wait for it to return and rerun the same cloud-init status command.

Create the password through an interactive SSH terminal. Do not put it on the
command line or in Terraform:

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

Run these commands from the local workstation:

```bash
ssh ubuntu@"$public_ip" 'sudo systemctl status klee-web.service'
ssh ubuntu@"$public_ip" 'sudo journalctl -u klee-web.service'
```

Restarting through SSH recreates the full Compose project while preserving the
Redis named volume:

```bash
ssh ubuntu@"$public_ip" 'sudo systemctl restart klee-web.service'
```

Reboot through Azure and wait for the same systemd service to restore the app:

```bash
resource_group=$(terraform output -raw resource_group_name)
az vm restart \
  --subscription "$TF_VAR_subscription_id" \
  --resource-group "$resource_group" \
  --name klee-web-azure-baseline
ssh ubuntu@"$public_ip" 'systemctl is-active klee-web.service'
```

Use the [shared host-maintenance procedure](host-maintenance.md) for controlled
Ubuntu security updates and post-reboot verification.

Inspect the certificate deadline with:

```bash
ssh ubuntu@"$public_ip" \
  'sudo openssl x509 -in /etc/klee-web/tls/fullchain.pem -noout -dates'
```

## Upgrade and roll back

### One-time cache-identity migration

Hosts provisioned before the API received `RUNNER_IMAGE` need one shared Compose
update. New hosts already contain it. From the accepted source checkout that
matches the candidate image set, copy the base file to the VM:

```bash
scp docker-compose.yml \
  ubuntu@"$public_ip":/home/ubuntu/klee-web-docker-compose.yml
ssh -t ubuntu@"$public_ip"
```

Run the migration inside the VM. Back up the installed file, install the
candidate, and render the complete deployment before changing any image:

```bash
sudo install -m 0644 \
  /opt/klee-web/docker-compose.yml \
  /opt/klee-web/docker-compose.yml.rollback
sudo install -o root -g root -m 0644 \
  /home/ubuntu/klee-web-docker-compose.yml \
  /opt/klee-web/docker-compose.yml
sudo /opt/klee-web/compose-deployment.sh config
rm /home/ubuntu/klee-web-docker-compose.yml
```

If rendering fails, restore `docker-compose.yml.rollback` before leaving the
host:

```bash
sudo install -m 0644 \
  /opt/klee-web/docker-compose.yml.rollback \
  /opt/klee-web/docker-compose.yml
```

This migration does not reload the running service. The new file is compatible
with the previous backend image, and later application promotions return to the
image-only procedure below.

Application promotion changes only `FRONTEND_IMAGE`, `BACKEND_IMAGE`, and
`RUNNER_IMAGE` in `/etc/klee-web/deployment.env`. Resolve and verify one complete
three-image publication locally before editing the VM. Use immutable signed
digests and verify each with GitHub's attestation identity:

```bash
commit="FULL_COMMIT_SHA"
frontend_digest=$(docker buildx imagetools inspect \
  "ghcr.io/finnleh/klee-web-frontend:sha-$commit" \
  --format '{{.Manifest.Digest}}')
backend_digest=$(docker buildx imagetools inspect \
  "ghcr.io/finnleh/klee-web-backend:sha-$commit" \
  --format '{{.Manifest.Digest}}')
runner_digest=$(docker buildx imagetools inspect \
  "ghcr.io/finnleh/klee-web-runner:sha-$commit" \
  --format '{{.Manifest.Digest}}')

frontend_image="ghcr.io/finnleh/klee-web-frontend@$frontend_digest"
backend_image="ghcr.io/finnleh/klee-web-backend@$backend_digest"
runner_image="ghcr.io/finnleh/klee-web-runner@$runner_digest"

gh attestation verify "oci://$frontend_image" --repo FinnLeh/klee-web
gh attestation verify "oci://$backend_image" --repo FinnLeh/klee-web
gh attestation verify "oci://$runner_image" --repo FinnLeh/klee-web
```

Open an interactive remote shell and preserve the previous desired state:

```bash
ssh -t ubuntu@"$public_ip"
```

The following commands run inside the Azure VM:

```bash
sudo install -m 0644 \
  /etc/klee-web/deployment.env \
  /etc/klee-web/deployment.env.rollback
sudoedit /etc/klee-web/deployment.env
```

Before editing, inspect constrained-disk headroom with `df -h /` and
`sudo docker system df`. Replace exactly the three image assignments with the
verified digest references, then pull before asking systemd to reconcile them:

```bash
sudo /opt/klee-web/pull-images.sh
sudo systemctl reload klee-web.service
exit
```

Verify readiness, active image references, Redis state, and a real uncached Job.
When both image sets fit, retain the old images for offline rollback. If a future
KLEE base cannot coexist on the 32 GiB disk, use a planned maintenance window to
stop the service and prune the old application images before pulling; that path
requires registry access to roll back. Record which path was required rather than
claiming zero-downtime rollback unconditionally.

When the old images remain, restore the preserved references without a registry
pull:

```bash
ssh -t ubuntu@"$public_ip"
```

Run the rollback inside the Azure VM:

```bash
sudo install -m 0644 \
  /etc/klee-web/deployment.env.rollback \
  /etc/klee-web/deployment.env
sudo systemctl reload klee-web.service
exit
```

## Destroy

Capture required operational and cost evidence first. On the local workstation,
retain the resource-group name before applying the reviewed destroy plan:

```bash
resource_group=$(terraform output -raw resource_group_name)
terraform plan -destroy -out=destroy.tfplan
terraform show destroy.tfplan
terraform apply destroy.tfplan
terraform state list
```

`terraform state list` should return no resources. Independently confirm that the
resource group and tagged deployment resources are gone:

```bash
test "$(az group exists \
  --subscription "$TF_VAR_subscription_id" \
  --name "$resource_group")" = false
az resource list \
  --subscription "$TF_VAR_subscription_id" \
  --tag Project=klee-web \
  --query "[?tags.Environment=='azure-baseline'].{type:type,location:location}" \
  --output table
az resource list \
  --subscription "$TF_VAR_subscription_id" \
  --resource-type Microsoft.Compute/disks \
  --query "[?starts_with(name, 'klee-web-azure-baseline')].{name:name,location:location}" \
  --output table
```

Both list commands should return no rows. Billing data can lag deletion. A
deallocated VM is not teardown: its managed disk and static public IP can remain
billable until Terraform destroys them.

Azure can automatically create `NetworkWatcherRG` when the first VNet appears,
outside Terraform state. If the subscription had no pre-existing Network Watcher,
inspect that group after teardown and remove only the experiment-created watcher.
