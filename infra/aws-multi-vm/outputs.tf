# Record the exact Canonical image selected by the Ubuntu release filter.
output "ubuntu_ami_id" {
  description = "Canonical Ubuntu 24.04 AMD64 AMI used by every host."
  value       = data.aws_ami.ubuntu.id
}

# Identify the persistent web and state host for inspection.
output "web_instance_id" {
  description = "EC2 instance ID for the web and state host."
  value       = aws_instance.web.id
}

# Identify every stateless execution host by its stable Worker name.
output "worker_instance_ids" {
  description = "EC2 instance IDs keyed by Worker name."
  value = {
    for worker_name, instance in aws_instance.worker : worker_name => instance.id
  }
}

# Record the physical availability boundary selected for the experiment.
output "availability_zone" {
  description = "Availability Zone containing every KLEE Web host."
  value       = aws_instance.web.availability_zone
}

# Expose the stable address assigned to the public web edge.
output "public_ip" {
  description = "Elastic IPv4 address for the KLEE Web edge."
  value       = aws_eip.web.public_ip
}

# Record the private Redis endpoint derived from the web network interface.
output "web_private_ip" {
  description = "Private IPv4 address for the web host and Redis endpoint."
  value       = aws_network_interface.web.private_ip
}

# Identify each private Worker endpoint for inspection through the bastion.
output "worker_private_ips" {
  description = "Private IPv4 addresses keyed by Worker name."
  value = {
    for worker_name, instance in aws_instance.worker : worker_name => instance.private_ip
  }
}

# Record the public source address shared by outbound Worker connections.
output "nat_public_ip" {
  description = "Elastic IPv4 address used by the Worker NAT gateway."
  value       = aws_eip.nat.public_ip
}

# Provide the browser endpoint backed by the short-lived IP certificate.
output "https_url" {
  description = "Public HTTPS URL for KLEE Web."
  value       = "https://${aws_eip.web.public_ip}"
}

# Provide the direct login command for the public web host.
output "web_ssh_command" {
  description = "SSH command for the web host's Ubuntu operator account."
  value       = "ssh ubuntu@${aws_eip.web.public_ip}"
}

# Provide local-agent ProxyJump commands for private Worker inspection.
output "worker_ssh_commands" {
  description = "SSH ProxyJump commands keyed by Worker name."
  value = {
    for worker_name, instance in aws_instance.worker :
    worker_name => "ssh -J ubuntu@${aws_eip.web.public_ip} ubuntu@${instance.private_ip}"
  }
}
