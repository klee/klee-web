# Pin Terraform to the reviewed subscription and avoid unrelated provider registration.
provider "azurerm" {
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"

  features {
    virtual_machine {
      delete_os_disk_on_deletion = true
    }
  }
}

# Verify that the pinned Canonical image exists in the selected Region.
data "azurerm_platform_image" "ubuntu" {
  location  = var.location
  publisher = "Canonical"
  offer     = "ubuntu-24_04-lts"
  sku       = "server"
  version   = var.ubuntu_image_version
}

# Render the provider-independent deployment files and Azure TLS input for cloud-init.
locals {
  resource_name      = "klee-web-azure-baseline"
  admin_username     = "ubuntu"
  vnet_cidr          = format("%d.%d.%d.%d/%d", 10, 0, 0, 0, 16)
  public_subnet_cidr = format("%d.%d.%d.%d/%d", 10, 0, 1, 0, 24)
  all_ipv4_cidr      = format("%d.%d.%d.%d/%d", 0, 0, 0, 0, 0)

  tags = {
    Environment = "azure-baseline"
    ManagedBy   = "Terraform"
    Project     = "klee-web"
  }

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
    public_ip = azurerm_public_ip.public.ip_address
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

# Group every deployment-owned Azure resource for inspection and teardown.
resource "azurerm_resource_group" "main" {
  name     = local.resource_name
  location = var.location
  tags     = local.tags
}

# Create the isolated private network that contains the deployment.
resource "azurerm_virtual_network" "main" {
  name                = "${local.resource_name}-vnet"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = [local.vnet_cidr]
  tags                = local.tags
}

# Place the single host in one subnet; its NIC receives the static public address.
resource "azurerm_subnet" "public" {
  name                            = "public"
  resource_group_name             = azurerm_resource_group.main.name
  virtual_network_name            = azurerm_virtual_network.main.name
  address_prefixes                = [local.public_subnet_cidr]
  default_outbound_access_enabled = false
}

# Define the firewall boundary around the Azure host.
resource "azurerm_network_security_group" "host" {
  name                = "${local.resource_name}-nsg"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

# Permit SSH only from the operator's current public address.
resource "azurerm_network_security_rule" "ssh" {
  name                        = "ssh-from-operator"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = var.operator_cidr
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.host.name
}

# Permit HTTP for redirects and the temporary certificate challenge.
resource "azurerm_network_security_rule" "http" {
  name                        = "public-http"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "80"
  source_address_prefix       = local.all_ipv4_cidr
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.host.name
}

# Permit browsers to reach nginx over HTTPS.
resource "azurerm_network_security_rule" "https" {
  name                        = "public-https"
  priority                    = 120
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = local.all_ipv4_cidr
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.host.name
}

# Permit outbound package, image, gVisor, and certificate downloads.
resource "azurerm_network_security_rule" "internet" {
  name                        = "outbound-internet"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "Internet"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.host.name
}

# Reserve the stable address before rendering the certificate request.
resource "azurerm_public_ip" "public" {
  name                = "${local.resource_name}-public-ip"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  ip_version          = "IPv4"
  sku                 = "Standard"
  tags                = local.tags
}

# Create the host's network card and bind the final public address.
resource "azurerm_network_interface" "host" {
  name                           = "${local.resource_name}-nic"
  resource_group_name            = azurerm_resource_group.main.name
  location                       = azurerm_resource_group.main.location
  accelerated_networking_enabled = true
  tags                           = local.tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.public.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.public.id
  }
}

# Apply the host firewall to its network card.
resource "azurerm_network_interface_security_group_association" "host" {
  network_interface_id      = azurerm_network_interface.host.id
  network_security_group_id = azurerm_network_security_group.host.id
}

# Launch the complete Compose topology on one pinned Ubuntu host.
resource "azurerm_linux_virtual_machine" "host" {
  name                            = local.resource_name
  computer_name                   = "klee-web-azure"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  size                            = var.vm_size
  admin_username                  = local.admin_username
  disable_password_authentication = true
  secure_boot_enabled             = false
  vtpm_enabled                    = false
  custom_data                     = base64gzip(local.cloud_init)
  network_interface_ids           = [azurerm_network_interface.host.id]
  tags                            = local.tags

  admin_ssh_key {
    username   = local.admin_username
    public_key = trimspace(var.ssh_public_key)
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = data.azurerm_platform_image.ubuntu.version
  }

  # Use the constrained Azure tier; measure free space and upgrade overlap on-host.
  os_disk {
    name                 = "${local.resource_name}-os"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = var.os_disk_size_gib
  }

  # Do not let first-boot downloads race network policy creation.
  depends_on = [
    azurerm_network_interface_security_group_association.host,
    azurerm_network_security_rule.http,
    azurerm_network_security_rule.https,
    azurerm_network_security_rule.internet,
    azurerm_network_security_rule.ssh,
  ]
}
