
variable ALI_ACCESS_KEY {}
variable ALI_SECRET_KEY {}
variable ALI_REGION {}

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

# 主机名称
variable "HOST_NAME" {
  description = "ECS instance hostname"
  type        = string
  default     = "egr-[0,6]"
}

# 可选：如果你想使用密钥对而不是密码
variable "KEY_PAIR_NAME" {
  description = "Name of the key pair to use for SSH access"
  type        = string
  default     = ""
}

# 可选：如果你想设置实例密码
variable "INSTANCE_PASSWORD" {
  description = "Password for the ECS instance"
  type        = string
  default     = ""
  sensitive   = true
}

# 可选：系统盘大小
variable "SYSTEM_DISK_SIZE" {
  description = "Size of the system disk in GB"
  type        = number
  default     = 40
}

# 系统盘名称
variable "SYSTEM_DISK_NAME" {
  description = "System disk name (must follow naming rules)"
  type        = string
  default     = "egr-system"
}



# # 手动指定VPC ID（必填，避免权限问题）
# variable "VPC_ID" {
#   description = "VPC ID to use. Must be provided to avoid permission issues."
#   type        = string
# }

# 手动指定VSwitch ID（必填，避免权限问题）
variable "VSWITCH_ID" {
  description = "VSwitch ID to use. Must be provided to avoid permission issues."
  type        = string
}

# 手动指定可用区（必填，避免权限问题）
variable "AVAILABILITY_ZONE" {
  description = "Availability zone to use. Must be provided to avoid permission issues."
  type        = string
}

# 手动指定安全组ID（必填，避免权限问题）
variable "SECURITY_GROUP_ID" {
  description = "Security Group ID to use. Must be provided to avoid permission issues."
  type        = string
}

# 手动指定镜像ID（必填，避免权限问题）
variable "IMAGE_ID" {
  description = "Image ID to use. Must be provided to avoid permission issues. Example: ubuntu_24_04_x64_20G_alibase_20251102.vhd"
  type        = string
}

# 实例计费类型
variable "INSTANCE_CHARGE_TYPE" {
  description = "Instance charge type. PostPaid (Pay-As-You-Go) or PrePaid (Subscription)"
  type        = string
  default     = "PostPaid"
}

# 系统盘类型
variable "SYSTEM_DISK_CATEGORY" {
  description = "System disk category. cloud_efficiency, cloud_ssd, cloud_essd"
  type        = string
  default     = "cloud_essd"
}

# 系统盘性能级别（仅cloud_essd支持）
variable "SYSTEM_DISK_PERFORMANCE_LEVEL" {
  description = "System disk performance level. PL0, PL1, PL2, PL3 (only for cloud_essd)"
  type        = string
  default     = "PL0"
}

# 网络计费类型
variable "INTERNET_CHARGE_TYPE" {
  description = "Internet charge type. PayByBandwidth or PayByTraffic"
  type        = string
  default     = "PayByTraffic"
}

# 公网带宽最大值
variable "INTERNET_MAX_BANDWIDTH_OUT" {
  description = "Maximum outbound public bandwidth (Mbps)"
  type        = number
  default     = 100
}

# 安全加固策略
variable "SECURITY_ENHANCEMENT_STRATEGY" {
  description = "Security enhancement strategy. Active or Deactive"
  type        = string
  default     = "Active"
}

# I/O优化
variable "IO_OPTIMIZED" {
  description = "Whether the instance is I/O optimized. optimized or none"
  type        = string
  default     = "optimized"
}

# 竞价策略（可选，默认不使用竞价）
variable "SPOT_STRATEGY" {
  description = "Spot strategy. NoSpot (default), SpotWithPriceLimit, SpotAsPriceGo"
  type        = string
  default     = "NoSpot"
}

# 竞价实例保留时长
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

# 自动释放时间
variable "AUTO_RELEASE_TIME" {
  description = "Automatic release time for Pay-As-You-Go instances (UTC time in RFC3339 format, e.g., 2025-11-16T18:48:30Z)"
  type        = string
  default     = ""
}
