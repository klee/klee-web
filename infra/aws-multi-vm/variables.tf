variable "aws_region" {
  description = "AWS Region for the role-separated deployment."
  type        = string
  default     = "eu-west-2"
}

variable "availability_zone" {
  description = "Availability Zone containing both deployment subnets."
  type        = string
  default     = "eu-west-2a"
}

variable "ubuntu_ami_id" {
  description = "Pinned Canonical Ubuntu 24.04 AMD64 AMI in the selected Region."
  type        = string
  default     = "ami-01029182857b20417"

  validation {
    condition     = can(regex("^ami-[0-9a-f]+$", var.ubuntu_ami_id))
    error_message = "ubuntu_ami_id must be an AWS AMI identifier."
  }
}

variable "web_instance_type" {
  description = "Linux AMD64 EC2 instance type used by the web/state role."
  type        = string
  default     = "t3.small"

  validation {
    condition     = startswith(var.web_instance_type, "t3.")
    error_message = "web_instance_type must use the T3 burstable family."
  }
}

variable "worker_instance_type" {
  description = "Nested-virtualisation-capable Linux AMD64 EC2 instance type used by Workers."
  type        = string
  default     = "m7i-flex.large"
}

variable "web_root_volume_size_gib" {
  description = "Encrypted gp3 root-volume size in GiB for the web/state VM."
  type        = number
  default     = 20

  validation {
    condition = (
      var.web_root_volume_size_gib >= 20 &&
      floor(var.web_root_volume_size_gib) == var.web_root_volume_size_gib
    )
    error_message = "web_root_volume_size_gib must be an integer of at least 20 GiB."
  }
}

variable "worker_root_volume_size_gib" {
  description = "Encrypted gp3 root-volume size in GiB for each Worker VM."
  type        = number
  default     = 32

  validation {
    condition = (
      var.worker_root_volume_size_gib >= 32 &&
      floor(var.worker_root_volume_size_gib) == var.worker_root_volume_size_gib
    )
    error_message = "worker_root_volume_size_gib must be an integer of at least 32 GiB."
  }
}

variable "worker_count" {
  description = "Number of private one-slot Worker VMs in the controlled deployment."
  type        = number
  default     = 1

  validation {
    condition     = contains([1, 2], var.worker_count)
    error_message = "worker_count must be one or two."
  }
}

variable "operator_cidr" {
  description = "Single public IPv4 address in /32 CIDR notation allowed to use SSH."
  type        = string

  validation {
    condition = (
      can(cidrnetmask(var.operator_cidr)) &&
      endswith(var.operator_cidr, "/32")
    )
    error_message = "operator_cidr must be one IPv4 address with a /32 prefix."
  }
}

variable "ssh_public_key" {
  description = "Ed25519 public key registered for the Ubuntu EC2 user."
  type        = string

  validation {
    condition     = startswith(trimspace(var.ssh_public_key), "ssh-ed25519 ")
    error_message = "ssh_public_key must be an Ed25519 public key."
  }
}

variable "frontend_image" {
  description = "Immutable frontend OCI image reference."
  type        = string
  default     = "ghcr.io/finnleh/klee-web-frontend@sha256:3e9bccc57278ac5fa71f3f829ca4b0605295989aea7c3913e9d673414883fe70"

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.frontend_image))
    error_message = "frontend_image must end with an immutable SHA-256 digest."
  }
}

variable "backend_image" {
  description = "Immutable backend OCI image reference used by the API and Worker."
  type        = string
  default     = "ghcr.io/finnleh/klee-web-backend@sha256:4921a00dc0130cb8e8b1db459bde1b3febe66a37ea102d61d53bb9d68086a22d"

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.backend_image))
    error_message = "backend_image must end with an immutable SHA-256 digest."
  }
}

variable "runner_image" {
  description = "Immutable Runner OCI image reference launched for each Job."
  type        = string
  default     = "ghcr.io/finnleh/klee-web-runner@sha256:25ba8f02cbc4d497213f874fc3c11f4111cb455e796d121d2527dc29eee7b670"

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.runner_image))
    error_message = "runner_image must end with an immutable SHA-256 digest."
  }
}

variable "redis_maxmemory" {
  description = "Redis dataset memory limit passed to Compose."
  type        = string
  default     = "256mb"
}

variable "runner_cpus" {
  description = "CPU Cap applied to each Runner container."
  type        = number
  default     = 2

  validation {
    condition     = var.runner_cpus > 0
    error_message = "runner_cpus must be greater than zero."
  }
}

variable "runner_memory_mb" {
  description = "Hard-memory Cap in MiB applied to each Runner container."
  type        = number
  default     = 3072

  validation {
    condition = (
      var.runner_memory_mb > 0 &&
      floor(var.runner_memory_mb) == var.runner_memory_mb
    )
    error_message = "runner_memory_mb must be a positive integer."
  }
}

variable "runner_swap_mb" {
  description = "Additional swap allowance in MiB for each Runner container."
  type        = number
  default     = 0

  validation {
    condition = (
      var.runner_swap_mb >= 0 &&
      floor(var.runner_swap_mb) == var.runner_swap_mb
    )
    error_message = "runner_swap_mb must be a non-negative integer."
  }
}

variable "runner_pids_limit" {
  description = "Process-count Cap applied to each Runner container."
  type        = number
  default     = 128

  validation {
    condition = (
      var.runner_pids_limit > 0 &&
      floor(var.runner_pids_limit) == var.runner_pids_limit
    )
    error_message = "runner_pids_limit must be a positive integer."
  }
}

variable "runner_storage_mb" {
  description = "Writable tmpfs Cap in MiB applied to each Runner container."
  type        = number
  default     = 768

  validation {
    condition = (
      var.runner_storage_mb > 0 &&
      floor(var.runner_storage_mb) == var.runner_storage_mb
    )
    error_message = "runner_storage_mb must be a positive integer."
  }
}
