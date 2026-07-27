# Record the exact Canonical image selected for the host.
output "ubuntu_image_urn" {
  description = "Canonical Ubuntu 24.04 AMD64 Marketplace image used by the host."
  value       = "Canonical:ubuntu-24_04-lts:server:${data.azurerm_platform_image.ubuntu.version}"
}

# Identify the resource group that owns the complete deployment.
output "resource_group_name" {
  description = "Azure resource group containing the KLEE Web deployment."
  value       = azurerm_resource_group.main.name
}

# Identify the VM for inspection and teardown checks.
output "virtual_machine_id" {
  description = "Azure resource ID of the KLEE Web host."
  value       = azurerm_linux_virtual_machine.host.id
}

# Record the Azure Region selected for the experiment.
output "location" {
  description = "Azure Region containing the KLEE Web host."
  value       = azurerm_resource_group.main.location
}

# Expose the stable address assigned to the deployment.
output "public_ip" {
  description = "Static public IPv4 address for KLEE Web."
  value       = azurerm_public_ip.public.ip_address
}

# Provide the browser endpoint backed by the short-lived IP certificate.
output "https_url" {
  description = "Public HTTPS URL for KLEE Web."
  value       = "https://${azurerm_public_ip.public.ip_address}"
}

# Provide the login command used with the existing SSH agent.
output "ssh_command" {
  description = "SSH command for the Ubuntu operator account."
  value       = "ssh ${local.admin_username}@${azurerm_public_ip.public.ip_address}"
}
