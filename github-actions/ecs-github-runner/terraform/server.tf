

locals {
  runner_name = var.RUNNER_NAME != "" ? var.RUNNER_NAME : var.ALI_ECS_NAME
  runner_url  = var.REGISTER_RUNNER ? (var.GITHUB_SCOPE == "org" ? format("https://github.com/%s", var.GITHUB_OWNER) : format("https://github.com/%s/%s", var.GITHUB_OWNER, var.GITHUB_REPOSITORY)) : ""
  runner_user_data = var.RUNNER_ENABLED && var.REGISTER_RUNNER ? base64encode(templatefile("${path.module}/scripts/user_data.sh.tmpl", {
    runner_user      = var.RUNNER_USER
    runner_workdir   = var.RUNNER_WORKDIR
    runner_version   = var.RUNNER_VERSION
    runner_token     = var.GITHUB_RUNNER_TOKEN
    runner_url       = local.runner_url
    runner_labels    = var.GITHUB_RUNNER_LABELS
    runner_name      = local.runner_name
    runner_ephemeral = var.RUNNER_EPHEMERAL ? "true" : "false"
  })) : null
}

# ECS Instance
resource "alicloud_instance" "github_runner" {
  count             = var.RUNNER_ENABLED ? 1 : 0
  availability_zone = var.AVAILABILITY_ZONE
  security_groups   = [var.SECURITY_GROUP_ID]
  vswitch_id        = var.VSWITCH_ID

  # Instance configuration
  instance_type        = var.ALI_ECS_INSTANCE_TYPE
  instance_charge_type = var.INSTANCE_CHARGE_TYPE
  instance_name        = var.ALI_ECS_NAME
  host_name            = var.HOST_NAME
  image_id             = var.IMAGE_ID

  # System disk configuration - matches cloud_essd settings used in Java code
  system_disk_category          = var.SYSTEM_DISK_CATEGORY
  system_disk_name              = var.SYSTEM_DISK_NAME
  system_disk_size              = var.SYSTEM_DISK_SIZE
  system_disk_performance_level = var.SYSTEM_DISK_PERFORMANCE_LEVEL

  # Network configuration - matches pay-by-traffic settings in Java code
  internet_charge_type       = var.INTERNET_CHARGE_TYPE
  internet_max_bandwidth_out = var.INTERNET_MAX_BANDWIDTH_OUT

  # Security configuration
  security_enhancement_strategy = var.SECURITY_ENHANCEMENT_STRATEGY

  # Spot instance configuration (optional, toggleable)
  spot_strategy = var.SPOT_STRATEGY
  spot_duration = var.SPOT_STRATEGY != "NoSpot" ? var.SPOT_DURATION : null

  # Metadata configuration
  http_tokens = var.HTTP_TOKENS

  # Auto-release time (only applicable to Pay-As-You-Go instances)
  auto_release_time = var.AUTO_RELEASE_TIME != "" ? var.AUTO_RELEASE_TIME : null

  # Use either a key pair or a password
  key_name = var.KEY_PAIR_NAME != "" ? var.KEY_PAIR_NAME : null
  password = var.INSTANCE_PASSWORD != "" ? var.INSTANCE_PASSWORD : null

  user_data = local.runner_user_data

  tags = {
    Name        = var.ALI_ECS_NAME
    Environment = "ci"
    Purpose     = "github-runner"
  }
}

# Outputs
output "instance_id" {
  value = length(alicloud_instance.github_runner) > 0 ? alicloud_instance.github_runner[0].id : null
}

output "public_ip" {
  value = length(alicloud_instance.github_runner) > 0 ? alicloud_instance.github_runner[0].public_ip : null
}

output "private_ip" {
  value = length(alicloud_instance.github_runner) > 0 ? alicloud_instance.github_runner[0].private_ip : null
}

# output "vpc_id" {
#   value = var.VPC_ID
# }

output "vswitch_id" {
  value = var.VSWITCH_ID
}
