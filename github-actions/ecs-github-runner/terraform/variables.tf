
variable "ALI_ACCESS_KEY" {}
variable "ALI_SECRET_KEY" {}
variable "ALI_REGION" {}

variable "ALI_ECS_INSTANCE_TYPE" {
  description = "ECS instance type"
  type        = string
  default     = "ecs.c7a.large"
}

variable "ALI_ECS_NAME" {
  description = "ECS instance name"
  type        = string
  default     = "egr-[0,6]"
}

# Hostname
variable "HOST_NAME" {
  description = "ECS instance hostname"
  type        = string
  default     = "egr-[0,6]"
}

# Optional: use an SSH key pair instead of a password
variable "KEY_PAIR_NAME" {
  description = "Name of the key pair to use for SSH access"
  type        = string
  default     = ""
}

# Optional: set an instance password
variable "INSTANCE_PASSWORD" {
  description = "Password for the ECS instance"
  type        = string
  default     = ""
  sensitive   = true
}

# Optional: system disk size
variable "SYSTEM_DISK_SIZE" {
  description = "Size of the system disk in GB"
  type        = number
  default     = 100
}

# System disk name
variable "SYSTEM_DISK_NAME" {
  description = "System disk name (must follow naming rules)"
  type        = string
  default     = "egr-system"
}



# # Manually specify VPC ID (required to avoid permission issues)
# variable "VPC_ID" {
#   description = "VPC ID to use. Must be provided to avoid permission issues."
#   type        = string
# }

# Manually specify VSwitch ID (required to avoid permission issues)
variable "VSWITCH_ID" {
  description = "VSwitch ID to use. Must be provided to avoid permission issues."
  type        = string
}

# Manually specify availability zone (required to avoid permission issues)
variable "AVAILABILITY_ZONE" {
  description = "Availability zone to use. Must be provided to avoid permission issues."
  type        = string
}

# Manually specify security group ID (required to avoid permission issues)
variable "SECURITY_GROUP_ID" {
  description = "Security Group ID to use. Must be provided to avoid permission issues."
  type        = string
}

# Manually specify image ID (required to avoid permission issues)
variable "IMAGE_ID" {
  description = "Image ID to use. Must be provided to avoid permission issues. Example: ubuntu_24_04_x64_20G_alibase_20251102.vhd"
  type        = string
}

# Instance charge type PostPaid/PrePaid
variable "INSTANCE_CHARGE_TYPE" {
  description = "Instance charge type. PostPaid (Pay-As-You-Go) or PrePaid (Subscription)"
  type        = string
  default     = "PostPaid"
}

# System disk category
variable "SYSTEM_DISK_CATEGORY" {
  description = "System disk category. cloud_efficiency, cloud_ssd, cloud_essd"
  type        = string
  default     = "cloud_essd"
}

# System disk performance tier (only cloud_essd supports this)
variable "SYSTEM_DISK_PERFORMANCE_LEVEL" {
  description = "System disk performance level. PL0, PL1, PL2, PL3 (only for cloud_essd)"
  type        = string
  default     = "PL0"
}

# Network billing type
variable "INTERNET_CHARGE_TYPE" {
  description = "Internet charge type. PayByBandwidth or PayByTraffic"
  type        = string
  default     = "PayByTraffic"
}

# Maximum public bandwidth (outbound)
variable "INTERNET_MAX_BANDWIDTH_OUT" {
  description = "Maximum outbound public bandwidth (Mbps)"
  type        = number
  default     = 100
}

# Security hardening strategy
variable "SECURITY_ENHANCEMENT_STRATEGY" {
  description = "Security enhancement strategy. Active or Deactive"
  type        = string
  default     = "Active"
}

# I/O optimization
variable "IO_OPTIMIZED" {
  description = "Whether the instance is I/O optimized. optimized or none"
  type        = string
  default     = "optimized"
}

# Spot strategy (optional, disabled by default)
variable "SPOT_STRATEGY" {
  description = "Spot strategy. NoSpot (default), SpotWithPriceLimit, SpotAsPriceGo"
  type        = string
  default     = "NoSpot"
}

# Spot instance protection duration
variable "SPOT_DURATION" {
  description = "Spot instance duration in hours (1-6)"
  type        = number
  default     = 1
}

# HTTP Tokens
variable "HTTP_TOKENS" {
  description = "Whether to force IMDSv2. required or optional"
  type        = string
  default     = "optional"
}

# Auto-release time
variable "AUTO_RELEASE_TIME" {
  description = "Automatic release time for Pay-As-You-Go instances (UTC time in RFC3339 format, e.g., 2025-11-16T18:48:30Z)"
  type        = string
  default     = ""
}

# Whether Terraform should provision (true) or destroy (false) the ECS runner
variable "RUNNER_ENABLED" {
  description = "Set to false to destroy the ECS runner when re-applying Terraform"
  type        = bool
  default     = true
}

# Optional custom runner name (defaults to ALI_ECS_NAME)
variable "RUNNER_NAME" {
  description = "Custom GitHub runner name"
  type        = string
  default     = ""
}

variable "RUNNER_USER" {
  description = "Linux user used to run the GitHub runner service"
  type        = string
  default     = "github"
}

variable "RUNNER_WORKDIR" {
  description = "Working directory for the GitHub runner"
  type        = string
  default     = "/opt/actions-runner/_work"
}

variable "RUNNER_VERSION" {
  description = "GitHub runner version to install"
  type        = string
  default     = "2.316.0"
}

variable "RUNNER_EPHEMERAL" {
  description = "Whether to register the runner as ephemeral (single job)"
  type        = bool
  default     = true
}

variable "GITHUB_OWNER" {
  description = "GitHub organization or user that owns the repository"
  type        = string
  default     = ""
}

variable "GITHUB_REPOSITORY" {
  description = "Repository name when scope is repo"
  type        = string
  default     = ""
}

variable "GITHUB_SCOPE" {
  description = "Runner registration scope: repo or org"
  type        = string
  default     = "repo"
  validation {
    condition     = contains(["repo", "org"], var.GITHUB_SCOPE)
    error_message = "GITHUB_SCOPE must be either 'repo' or 'org'"
  }
}

variable "GITHUB_RUNNER_TOKEN" {
  description = "Registration token generated via the GitHub Actions API"
  type        = string
  default     = ""
  sensitive   = true
}

variable "GITHUB_RUNNER_LABELS" {
  description = "Comma separated list of labels assigned to the runner"
  type        = string
  default     = "ecs,alicloud"
}

variable "REGISTER_RUNNER" {
  description = "Whether to install and register the GitHub runner on the ECS instance"
  type        = bool
  default     = true
}

variable "CUSTOM_USER_DATA" {
  description = "Additional shell script content appended to user data"
  type        = string
  default     = ""
}
