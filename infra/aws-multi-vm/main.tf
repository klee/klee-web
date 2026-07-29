# Select the AWS Region and attach ownership tags to supported resources.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "aws-multi-vm"
      ManagedBy   = "Terraform"
      Project     = "klee-web"
    }
  }
}

# Verify the pinned AMI is an available AMD64 Ubuntu 24.04 image owned by Canonical.
data "aws_ami" "ubuntu" {
  owners = ["099720109477"]

  filter {
    name   = "image-id"
    values = [var.ubuntu_ami_id]
  }

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# Render shared deployment files and one desired environment per host role.
locals {
  resource_name      = "klee-web-aws-multi-vm"
  vpc_cidr           = format("%d.%d.%d.%d/%d", 10, 0, 0, 0, 16)
  public_subnet_cidr = format("%d.%d.%d.%d/%d", 10, 0, 1, 0, 24)
  worker_subnet_cidr = format("%d.%d.%d.%d/%d", 10, 0, 2, 0, 24)
  all_ipv4_cidr      = format("%d.%d.%d.%d/%d", 0, 0, 0, 0, 0)
  web_private_ip     = cidrhost(local.public_subnet_cidr, 10)
  worker_names = toset([
    for index in range(var.worker_count) : "klee-worker-${index + 1}"
  ])

  common_deployment_environment = templatefile("${path.module}/../../deploy/deployment.env.tftpl", {
    backend_image          = var.backend_image
    frontend_image         = var.frontend_image
    runner_image           = var.runner_image
    worker_replicas        = 1
    worker_concurrency_max = 1
    redis_maxmemory        = var.redis_maxmemory
    runner_cpus            = var.runner_cpus
    runner_memory_mb       = var.runner_memory_mb
    runner_swap_mb         = var.runner_swap_mb
    runner_pids_limit      = var.runner_pids_limit
    runner_storage_mb      = var.runner_storage_mb
  })

  web_deployment_environment = join("\n", [
    trimspace(local.common_deployment_environment),
    "DEPLOYMENT_ROLE=web",
    "REDIS_BIND_ADDRESS=${local.web_private_ip}",
    "",
  ])

  worker_deployment_environments = {
    for worker_name in local.worker_names : worker_name => join("\n", [
      trimspace(local.common_deployment_environment),
      "DEPLOYMENT_ROLE=worker",
      "REDIS_URL=redis://${local.web_private_ip}:6379/0",
      "CELERY_BROKER_URL=redis://${local.web_private_ip}:6379/1",
      "WORKER_NAME=celery@${worker_name}",
      "",
    ])
  }

  provision_tls = templatefile("${path.module}/../aws/provision-tls.sh.tftpl", {
    public_ip = aws_eip.web.public_ip
  })

  cloud_init_files = {
    docker_compose_b64     = filebase64("${path.module}/../../docker-compose.yml")
    compose_production_b64 = filebase64("${path.module}/../../deploy/compose.production.yml")
    compose_worker_b64     = filebase64("${path.module}/../../deploy/compose.worker.yml")
    bootstrap_host_b64     = filebase64("${path.module}/../../deploy/bootstrap-host.sh")
    maintain_host_b64      = filebase64("${path.module}/../../deploy/maintain-host.sh")
    compose_deployment_b64 = filebase64("${path.module}/../../deploy/compose-deployment.sh")
    pull_images_b64        = filebase64("${path.module}/../../deploy/pull-images.sh")
    set_admin_password_b64 = filebase64("${path.module}/../../deploy/set-admin-password.sh")
    klee_web_service_b64   = filebase64("${path.module}/../../deploy/klee-web.service")
  }

  web_cloud_init = templatefile(
    "${path.module}/../../deploy/cloud-init.yaml.tftpl",
    merge(local.cloud_init_files, {
      provision_tls_b64  = base64encode(local.provision_tls)
      deployment_env_b64 = base64encode(local.web_deployment_environment)
    })
  )

  worker_cloud_init = {
    for worker_name, deployment_environment in local.worker_deployment_environments :
    worker_name => templatefile(
      "${path.module}/../../deploy/cloud-init.yaml.tftpl",
      merge(local.cloud_init_files, {
        provision_tls_b64  = ""
        deployment_env_b64 = base64encode(deployment_environment)
      })
    )
  }
}

# Create the isolated private network that contains every deployment role.
resource "aws_vpc" "main" {
  cidr_block           = local.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = local.resource_name
  }
}

# Give the public subnet a route to and from the internet.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = local.resource_name
  }
}

# Place the web interface and NAT gateway in one public subnet.
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = var.availability_zone
  cidr_block              = local.public_subnet_cidr
  map_public_ip_on_launch = false

  tags = {
    Name = "${local.resource_name}-public"
  }
}

# Place every Worker in one subnet without direct internet addressing.
resource "aws_subnet" "worker" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = var.availability_zone
  cidr_block              = local.worker_subnet_cidr
  map_public_ip_on_launch = false

  tags = {
    Name = "${local.resource_name}-worker"
  }
}

# Send public-subnet traffic outside the VPC through the internet gateway.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = local.all_ipv4_cidr
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${local.resource_name}-public"
  }
}

# Apply the public route table to the web and NAT subnet.
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Reserve an address for outbound Worker traffic through the NAT gateway.
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "${local.resource_name}-nat"
  }
}

# Give private Workers outbound package, gVisor, and image access.
resource "aws_nat_gateway" "worker" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id

  tags = {
    Name = "${local.resource_name}-worker"
  }

  depends_on = [aws_internet_gateway.main]
}

# Route Worker internet traffic through the public-subnet NAT gateway.
resource "aws_route_table" "worker" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = local.all_ipv4_cidr
    nat_gateway_id = aws_nat_gateway.worker.id
  }

  tags = {
    Name = "${local.resource_name}-worker"
  }
}

# Apply the private route table to the Worker subnet.
resource "aws_route_table_association" "worker" {
  subnet_id      = aws_subnet.worker.id
  route_table_id = aws_route_table.worker.id
}

# Define the firewall boundary around the public web and state host.
resource "aws_security_group" "web" {
  name        = "${local.resource_name}-web"
  description = "Public KLEE Web edge, private Redis, and restricted SSH"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.resource_name}-web"
  }
}

# Define the firewall boundary around private execution hosts.
resource "aws_security_group" "worker" {
  name        = "${local.resource_name}-worker"
  description = "Private KLEE Web Workers"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${local.resource_name}-worker"
  }
}

# Permit SSH to the web host only from the operator's current public address.
resource "aws_vpc_security_group_ingress_rule" "web_ssh" {
  security_group_id = aws_security_group.web.id
  description       = "SSH from the operator address"
  cidr_ipv4         = var.operator_cidr
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
}

# Permit HTTP for redirects and the temporary certificate challenge.
resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.web.id
  description       = "HTTP redirect and ACME challenge"
  cidr_ipv4         = local.all_ipv4_cidr
  from_port         = 80
  ip_protocol       = "tcp"
  to_port           = 80
}

# Permit browsers to reach nginx over HTTPS.
resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.web.id
  description       = "Public HTTPS edge"
  cidr_ipv4         = local.all_ipv4_cidr
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443
}

# Permit Redis only from network interfaces carrying the Worker identity.
resource "aws_vpc_security_group_ingress_rule" "redis" {
  security_group_id            = aws_security_group.web.id
  referenced_security_group_id = aws_security_group.worker.id
  description                  = "Redis from private Workers"
  from_port                    = 6379
  ip_protocol                  = "tcp"
  to_port                      = 6379
}

# Permit Worker SSH only through the web host as a bastion.
resource "aws_vpc_security_group_ingress_rule" "worker_ssh" {
  security_group_id            = aws_security_group.worker.id
  referenced_security_group_id = aws_security_group.web.id
  description                  = "SSH from the web bastion"
  from_port                    = 22
  ip_protocol                  = "tcp"
  to_port                      = 22
}

# Permit web-host downloads and responses to established private connections.
resource "aws_vpc_security_group_egress_rule" "web" {
  security_group_id = aws_security_group.web.id
  description       = "Outbound package, image, certificate, and private traffic"
  cidr_ipv4         = local.all_ipv4_cidr
  ip_protocol       = "-1"
}

# Permit Workers to reach private Redis and public dependencies through NAT.
resource "aws_vpc_security_group_egress_rule" "worker" {
  security_group_id = aws_security_group.worker.id
  description       = "Outbound Redis, package, gVisor, and image traffic"
  cidr_ipv4         = local.all_ipv4_cidr
  ip_protocol       = "-1"
}

# Register only the public half of the 1Password-held SSH key.
resource "aws_key_pair" "operator" {
  key_name   = "${local.resource_name}-operator"
  public_key = trimspace(var.ssh_public_key)
}

# Create the web host's primary network card before launching the instance.
resource "aws_network_interface" "web" {
  subnet_id       = aws_subnet.public.id
  security_groups = [aws_security_group.web.id]
  private_ips     = [local.web_private_ip]

  tags = {
    Name = "${local.resource_name}-web-primary"
  }
}

# Reserve the stable public address used by the web edge and certificate.
resource "aws_eip" "web" {
  domain = "vpc"

  tags = {
    Name = "${local.resource_name}-web"
  }
}

# Bind the final public address to the web card before EC2 launches.
resource "aws_eip_association" "web" {
  allocation_id        = aws_eip.web.id
  network_interface_id = aws_network_interface.web.id
}

# Launch nginx, FastAPI, and persistent Redis on the public web/state host.
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.web_instance_type
  key_name      = aws_key_pair.operator.key_name

  primary_network_interface {
    network_interface_id = aws_network_interface.web.id
  }

  # EC2 receives gzip bytes encoded as base64. Cloud-init detects and expands them.
  user_data_base64            = base64gzip(local.web_cloud_init)
  user_data_replace_on_change = true

  # Require token-authenticated metadata and prevent container access through extra hops.
  metadata_options {
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
    http_tokens                 = "required"
    instance_metadata_tags      = "disabled"
  }

  credit_specification {
    cpu_credits = "standard"
  }

  root_block_device {
    delete_on_termination = true
    encrypted             = true
    volume_size           = var.web_root_volume_size_gib
    volume_type           = "gp3"
  }

  volume_tags = {
    Name = "${local.resource_name}-web-root"
  }

  tags = {
    Name = "${local.resource_name}-web"
    Role = "web"
  }

  # Do not let first-boot downloads race public addressing or network policy.
  depends_on = [
    aws_eip_association.web,
    aws_route_table_association.public,
    aws_vpc_security_group_egress_rule.web,
    aws_vpc_security_group_ingress_rule.http,
    aws_vpc_security_group_ingress_rule.https,
    aws_vpc_security_group_ingress_rule.redis,
    aws_vpc_security_group_ingress_rule.web_ssh,
  ]
}

# Launch one stateless execution host for each stable Worker identity.
resource "aws_instance" "worker" {
  for_each = local.worker_names

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.worker_instance_type
  key_name                    = aws_key_pair.operator.key_name
  subnet_id                   = aws_subnet.worker.id
  vpc_security_group_ids      = [aws_security_group.worker.id]
  associate_public_ip_address = false

  user_data_base64            = base64gzip(local.worker_cloud_init[each.key])
  user_data_replace_on_change = true

  # Ask Nitro for KVM support. Each guest still proves it with a real gVisor probe.
  cpu_options {
    nested_virtualization = "enabled"
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
    http_tokens                 = "required"
    instance_metadata_tags      = "disabled"
  }

  root_block_device {
    delete_on_termination = true
    encrypted             = true
    volume_size           = var.worker_root_volume_size_gib
    volume_type           = "gp3"
  }

  volume_tags = {
    Name = "${local.resource_name}-${each.key}-root"
  }

  tags = {
    Name = "${local.resource_name}-${each.key}"
    Role = "worker"
  }

  # Do not let first-boot downloads race NAT or private access policy.
  depends_on = [
    aws_route_table_association.worker,
    aws_vpc_security_group_egress_rule.worker,
    aws_vpc_security_group_ingress_rule.redis,
    aws_vpc_security_group_ingress_rule.worker_ssh,
  ]
}
