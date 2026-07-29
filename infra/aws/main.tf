# Select the AWS Region and attach ownership tags to supported resources.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "aws-baseline"
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

# Render the provider-independent deployment files and AWS TLS input for cloud-init.
locals {
  resource_name      = "klee-web-aws-baseline"
  vpc_cidr           = format("%d.%d.%d.%d/%d", 10, 0, 0, 0, 16)
  public_subnet_cidr = format("%d.%d.%d.%d/%d", 10, 0, 1, 0, 24)
  all_ipv4_cidr      = format("%d.%d.%d.%d/%d", 0, 0, 0, 0, 0)

  deployment_environment = templatefile("${path.module}/../../deploy/deployment.env.tftpl", {
    backend_image          = var.backend_image
    frontend_image         = var.frontend_image
    runner_image           = var.runner_image
    worker_replicas        = var.worker_replicas
    worker_concurrency_max = var.worker_concurrency_max
    redis_maxmemory        = var.redis_maxmemory
    runner_cpus            = var.runner_cpus
    runner_memory_mb       = var.runner_memory_mb
    runner_swap_mb         = var.runner_swap_mb
    runner_pids_limit      = var.runner_pids_limit
    runner_storage_mb      = var.runner_storage_mb
  })

  provision_tls = templatefile("${path.module}/provision-tls.sh.tftpl", {
    public_ip = aws_eip.public.public_ip
  })

  # Base64 preserves embedded shell and Compose syntax when cloud-init parses YAML.
  cloud_init = templatefile("${path.module}/../../deploy/cloud-init.yaml.tftpl", {
    docker_compose_b64     = filebase64("${path.module}/../../docker-compose.yml")
    compose_production_b64 = filebase64("${path.module}/../../deploy/compose.production.yml")
    compose_worker_b64     = filebase64("${path.module}/../../deploy/compose.worker.yml")
    bootstrap_host_b64     = filebase64("${path.module}/../../deploy/bootstrap-host.sh")
    maintain_host_b64      = filebase64("${path.module}/../../deploy/maintain-host.sh")
    compose_deployment_b64 = filebase64("${path.module}/../../deploy/compose-deployment.sh")
    pull_images_b64        = filebase64("${path.module}/../../deploy/pull-images.sh")
    set_admin_password_b64 = filebase64("${path.module}/../../deploy/set-admin-password.sh")
    provision_tls_b64      = base64encode(local.provision_tls)
    deployment_env_b64     = base64encode(local.deployment_environment)
    klee_web_service_b64   = filebase64("${path.module}/../../deploy/klee-web.service")
  })
}

# Create the isolated private network that contains the deployment.
resource "aws_vpc" "main" {
  cidr_block           = local.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = local.resource_name
  }
}

# Give the VPC a route to and from the public internet.
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = local.resource_name
  }
}

# Place the single host in one public subnet without assigning a moving public IP.
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  availability_zone       = var.availability_zone
  cidr_block              = local.public_subnet_cidr
  map_public_ip_on_launch = false

  tags = {
    Name = "${local.resource_name}-public"
  }
}

# Send traffic outside the VPC through the internet gateway.
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

# Apply the public route table to the deployment subnet.
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Define the firewall boundary around the EC2 host.
resource "aws_security_group" "host" {
  name        = local.resource_name
  description = "Public KLEE Web edge and restricted SSH"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = local.resource_name
  }
}

# Permit SSH only from the operator's current public address.
resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.host.id
  description       = "SSH from the operator address"
  cidr_ipv4         = var.operator_cidr
  from_port         = 22
  ip_protocol       = "tcp"
  to_port           = 22
}

# Permit HTTP for redirects and the temporary certificate challenge.
resource "aws_vpc_security_group_ingress_rule" "http" {
  security_group_id = aws_security_group.host.id
  description       = "HTTP redirect and ACME challenge"
  cidr_ipv4         = local.all_ipv4_cidr
  from_port         = 80
  ip_protocol       = "tcp"
  to_port           = 80
}

# Permit browsers to reach nginx over HTTPS.
resource "aws_vpc_security_group_ingress_rule" "https" {
  security_group_id = aws_security_group.host.id
  description       = "Public HTTPS edge"
  cidr_ipv4         = local.all_ipv4_cidr
  from_port         = 443
  ip_protocol       = "tcp"
  to_port           = 443
}

# Permit outbound package, image, gVisor, and certificate downloads.
resource "aws_vpc_security_group_egress_rule" "internet" {
  security_group_id = aws_security_group.host.id
  description       = "Outbound package, image, and certificate access"
  cidr_ipv4         = local.all_ipv4_cidr
  ip_protocol       = "-1"
}

# Register only the public half of the 1Password-held SSH key.
resource "aws_key_pair" "operator" {
  key_name   = "${local.resource_name}-operator"
  public_key = trimspace(var.ssh_public_key)
}

# Create the primary virtual network card before launching the instance.
resource "aws_network_interface" "host" {
  subnet_id       = aws_subnet.public.id
  security_groups = [aws_security_group.host.id]

  tags = {
    Name = "${local.resource_name}-primary"
  }
}

# Reserve a stable public address before rendering the certificate request.
resource "aws_eip" "public" {
  domain = "vpc"

  tags = {
    Name = local.resource_name
  }
}

# Launch the complete Compose topology on one Ubuntu host.
resource "aws_instance" "host" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = aws_key_pair.operator.key_name

  primary_network_interface {
    network_interface_id = aws_network_interface.host.id
  }

  # EC2 receives gzip bytes encoded as base64. Cloud-init detects and expands them.
  user_data_base64            = base64gzip(local.cloud_init)
  user_data_replace_on_change = true

  # Ask Nitro for KVM support. The guest still proves it with a real gVisor probe.
  cpu_options {
    nested_virtualization = "enabled"
  }

  # Require token-authenticated metadata and prevent container access through extra hops.
  metadata_options {
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
    http_tokens                 = "required"
    instance_metadata_tags      = "disabled"
  }

  # Keep enough encrypted disk for the current images plus upgrade and rollback overlap.
  root_block_device {
    delete_on_termination = true
    encrypted             = true
    volume_size           = var.root_volume_size_gib
    volume_type           = "gp3"
  }

  volume_tags = {
    Name = "${local.resource_name}-root"
  }

  tags = {
    Name = local.resource_name
  }

  # Do not let first-boot package and image downloads race network policy creation.
  depends_on = [
    aws_eip_association.host,
    aws_route_table_association.public,
    aws_vpc_security_group_egress_rule.internet,
    aws_vpc_security_group_ingress_rule.http,
    aws_vpc_security_group_ingress_rule.https,
    aws_vpc_security_group_ingress_rule.ssh,
  ]
}

# Bind the final public address to the network card before EC2 launches.
resource "aws_eip_association" "host" {
  allocation_id        = aws_eip.public.id
  network_interface_id = aws_network_interface.host.id
}
