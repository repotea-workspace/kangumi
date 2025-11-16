
# variable "region" {
#   default = var.ALI_REGION
# }


# 获取可用区信息
data "alicloud_zones" "default" {
  available_disk_category     = "cloud_efficiency"
  available_resource_creation = "VSwitch"
  available_instance_type     = var.ALI_ECS_INSTANCE_TYPE
}

# 获取默认VPC（如果没有指定VPC ID，会获取默认VPC）
data "alicloud_vpcs" "default" {
  is_default = true
}

# 获取默认VPC中的VSwitch
data "alicloud_vswitches" "default" {
  vpc_id  = data.alicloud_vpcs.default.vpcs.0.id
  zone_id = data.alicloud_zones.default.zones.0.id
}

# 如果没有找到合适的VSwitch，可以添加一个本地值来处理
locals {
  vpc_id = data.alicloud_vpcs.default.vpcs.0.id
  vswitch_id = length(data.alicloud_vswitches.default.vswitches) > 0 ? data.alicloud_vswitches.default.vswitches.0.id : null
}

# 获取默认安全组
data "alicloud_security_groups" "default" {
  vpc_id     = local.vpc_id
  name_regex = "default"
}

# 创建安全组（如果需要自定义规则且有权限）
resource "alicloud_security_group" "github_runner" {
  count               = var.USE_DEFAULT_SECURITY_GROUP ? 0 : 1
  security_group_name = "${var.ALI_ECS_NAME}-sg"
  description         = "Security group for GitHub runner"
  vpc_id              = local.vpc_id
}

# 允许SSH访问
resource "alicloud_security_group_rule" "allow_ssh" {
  count             = var.USE_DEFAULT_SECURITY_GROUP ? 0 : 1
  type              = "ingress"
  ip_protocol       = "tcp"
  nic_type          = "intranet"
  policy            = "accept"
  port_range        = "22/22"
  priority          = 1
  security_group_id = alicloud_security_group.github_runner[0].id
  cidr_ip           = "0.0.0.0/0"
}

# 允许出站访问
resource "alicloud_security_group_rule" "allow_outbound" {
  count             = var.USE_DEFAULT_SECURITY_GROUP ? 0 : 1
  type              = "egress"
  ip_protocol       = "all"
  nic_type          = "intranet"
  policy            = "accept"
  port_range        = "-1/-1"
  priority          = 1
  security_group_id = alicloud_security_group.github_runner[0].id
  cidr_ip           = "0.0.0.0/0"
}

locals {
  security_group_id = var.USE_DEFAULT_SECURITY_GROUP ? data.alicloud_security_groups.default.groups[0].id : alicloud_security_group.github_runner[0].id
}

# ECS实例
resource "alicloud_instance" "github_runner" {
  availability_zone = data.alicloud_zones.default.zones.0.id
  security_groups   = [local.security_group_id]

  instance_type        = var.ALI_ECS_INSTANCE_TYPE
  system_disk_category = "cloud_efficiency"
  system_disk_name     = "${var.ALI_ECS_NAME}-system"
  system_disk_size     = var.SYSTEM_DISK_SIZE
  image_id             = data.alicloud_images.ubuntu.images.0.id
  instance_name        = var.ALI_ECS_NAME
  vswitch_id           = local.vswitch_id

  # 密钥对和密码二选一
  key_name = var.KEY_PAIR_NAME != "" ? var.KEY_PAIR_NAME : null
  password = var.INSTANCE_PASSWORD != "" ? var.INSTANCE_PASSWORD : null

  tags = {
    Name        = var.ALI_ECS_NAME
    Environment = "ci"
    Purpose     = "github-runner"
  }
}

# 获取Ubuntu镜像
data "alicloud_images" "ubuntu" {
  most_recent = true
  owners      = "system"
  name_regex  = "^ubuntu_20_04_x64"
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

output "vpc_id" {
  value = local.vpc_id
}

output "vswitch_id" {
  value = local.vswitch_id
}
