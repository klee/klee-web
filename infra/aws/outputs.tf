# Record the exact Canonical image selected by the Ubuntu release filter.
output "ubuntu_ami_id" {
  description = "Canonical Ubuntu 24.04 AMD64 AMI used by the host."
  value       = data.aws_ami.ubuntu.id
}

# Identify the EC2 host for inspection and teardown checks.
output "instance_id" {
  description = "EC2 instance ID for the KLEE Web host."
  value       = aws_instance.host.id
}

# Record the physical availability boundary selected for the experiment.
output "availability_zone" {
  description = "Availability Zone containing the KLEE Web host."
  value       = aws_instance.host.availability_zone
}

# Expose the stable address assigned to the deployment.
output "public_ip" {
  description = "Elastic IPv4 address for KLEE Web."
  value       = aws_eip.public.public_ip
}

# Provide the browser endpoint backed by the short-lived IP certificate.
output "https_url" {
  description = "Public HTTPS URL for KLEE Web."
  value       = "https://${aws_eip.public.public_ip}"
}

# Provide the login command used with the existing 1Password SSH agent.
output "ssh_command" {
  description = "SSH command for the Ubuntu operator account."
  value       = "ssh ubuntu@${aws_eip.public.public_ip}"
}
