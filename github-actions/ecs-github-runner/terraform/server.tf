

# ECS Instance
resource "alicloud_instance" "github_runner" {
  availability_zone = var.AVAILABILITY_ZONE
  security_groups   = [var.SECURITY_GROUP_ID]
  vswitch_id        = var.VSWITCH_ID

  # Instance configuration
  instance_type             = var.ALI_ECS_INSTANCE_TYPE
  instance_charge_type      = var.INSTANCE_CHARGE_TYPE
  instance_name             = var.ALI_ECS_NAME
  host_name                 = var.HOST_NAME
  image_id                  = var.IMAGE_ID

  # System disk configuration - matches cloud_essd settings used in Java code
  system_disk_category      = var.SYSTEM_DISK_CATEGORY
  system_disk_name          = var.SYSTEM_DISK_NAME
  system_disk_size          = var.SYSTEM_DISK_SIZE
  system_disk_performance_level = var.SYSTEM_DISK_PERFORMANCE_LEVEL

  # Network configuration - matches pay-by-traffic settings in Java code
  internet_charge_type      = var.INTERNET_CHARGE_TYPE
  internet_max_bandwidth_out = var.INTERNET_MAX_BANDWIDTH_OUT

  # Security configuration
  security_enhancement_strategy = var.SECURITY_ENHANCEMENT_STRATEGY

  # Spot instance configuration (optional, toggleable)
  spot_strategy            = var.SPOT_STRATEGY
  spot_duration            = var.SPOT_STRATEGY != "NoSpot" ? var.SPOT_DURATION : null

  # Metadata configuration
  http_tokens              = var.HTTP_TOKENS

  # Auto-release time (only applicable to Pay-As-You-Go instances)
  auto_release_time        = var.AUTO_RELEASE_TIME != "" ? var.AUTO_RELEASE_TIME : null

  # Use either a key pair or a password
  key_name = var.KEY_PAIR_NAME != "" ? var.KEY_PAIR_NAME : null
  password = var.INSTANCE_PASSWORD != "" ? var.INSTANCE_PASSWORD : null

  tags = {
    Name        = var.ALI_ECS_NAME
    Environment = "ci"
    Purpose     = "github-runner"
  }
}

# Outputs
output "instance_id" {
  value = alicloud_instance.github_runner.id
}

output "public_ip" {
  value = alicloud_instance.github_runner.public_ip
}

output "private_ip" {
  value = alicloud_instance.github_runner.private_ip
}

# output "vpc_id" {
#   value = var.VPC_ID
# }

output "vswitch_id" {
  value = var.VSWITCH_ID
}
