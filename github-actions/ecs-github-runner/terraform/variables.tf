
variable ALI_ACCESS_KEY {}
variable ALI_SECRET_KEY {}
variable ALI_REGION {}

variable ALI_ECS_INSTANCE_TYPE {
  default = "ecs.c7a.large"
}

variable "ALI_ECS_NAME" {
  default = "ecs-github-runner"
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

# 是否使用默认安全组（如果创建安全组权限不足）
variable "USE_DEFAULT_SECURITY_GROUP" {
  description = "Whether to use default security group instead of creating a new one"
  type        = bool
  default     = false
}
