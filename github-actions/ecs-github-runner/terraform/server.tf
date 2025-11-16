

# ECS实例
resource "alicloud_instance" "github_runner" {
  availability_zone = var.AVAILABILITY_ZONE
  security_groups   = [var.SECURITY_GROUP_ID]
  vswitch_id        = var.VSWITCH_ID

  # 实例配置
  instance_type             = var.ALI_ECS_INSTANCE_TYPE
  instance_charge_type      = var.INSTANCE_CHARGE_TYPE
  instance_name             = var.ALI_ECS_NAME
  host_name                 = var.HOST_NAME
  image_id                  = var.IMAGE_ID

  # 系统盘配置 - 匹配Java代码中的cloud_essd配置
  system_disk_category      = var.SYSTEM_DISK_CATEGORY
  system_disk_name          = var.SYSTEM_DISK_NAME
  system_disk_size          = var.SYSTEM_DISK_SIZE
  system_disk_performance_level = var.SYSTEM_DISK_PERFORMANCE_LEVEL

  # 网络配置 - 匹配Java代码中的按流量计费
  internet_charge_type      = var.INTERNET_CHARGE_TYPE
  internet_max_bandwidth_out = var.INTERNET_MAX_BANDWIDTH_OUT

  # 安全配置
  security_enhancement_strategy = var.SECURITY_ENHANCEMENT_STRATEGY

  # 竞价实例配置（如果需要）
  spot_strategy            = var.SPOT_STRATEGY
  spot_duration            = var.SPOT_DURATION

  # 元数据配置
  http_tokens              = var.HTTP_TOKENS

  # 自动释放时间（仅对按量付费实例有效）
  auto_release_time        = var.AUTO_RELEASE_TIME != "" ? var.AUTO_RELEASE_TIME : null

  # 密钥对和密码二选一
  key_name = var.KEY_PAIR_NAME != "" ? var.KEY_PAIR_NAME : null
  password = var.INSTANCE_PASSWORD != "" ? var.INSTANCE_PASSWORD : null

  tags = {
    Name        = var.ALI_ECS_NAME
    Environment = "ci"
    Purpose     = "github-runner"
  }
}

# 输出信息
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
