# ECS GitHub Runner Terraform Configuration

这个Terraform配置用于在阿里云上创建ECS实例作为GitHub Runner。

## 特点

- 使用现有的默认VPC和VSwitch，避免权限问题
- 支持使用默认安全组或创建自定义安全组
- 灵活的认证配置（密钥对或密码）

## 使用方法

### 1. 环境变量配置

复制 `.env.example` 到 `.env` 并填写你的阿里云配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 阿里云认证信息
ALI_ACCESS_KEY=your_access_key
ALI_SECRET_KEY=your_secret_key
ALI_REGION=cn-hangzhou

# ECS配置
ALI_ECS_INSTANCE_TYPE=ecs.c7a.large
ALI_ECS_NAME=github-runner
```

### 2. Terraform变量配置

如果你遇到权限问题无法创建安全组，可以在 `terraform.tfvars` 中设置：

```hcl
use_default_security_group = true
```

其他可选配置：

```hcl
# 使用密钥对（推荐）
key_pair_name = "your-key-pair"

# 或者使用密码
instance_password = "YourSecurePassword123!"

# 系统盘大小
system_disk_size = 40
```

### 3. 执行部署

```bash
# 初始化
terraform init

# 规划
terraform plan

# 应用
terraform apply
```

### 4. 权限问题解决方案

如果遇到以下错误：

```
Error: [ERROR] terraform-provider-alicloud/alicloud/resource_alicloud_vpc.go:255: Resource alicloud_vpc CreateVpc Failed!!!
Code: Forbidden.RAM
```

请确保：

1. 使用现有VPC和VSwitch（本配置已处理）
2. 如果无法创建安全组，设置 `use_default_security_group = true`
3. 确认RAM用户有以下最小权限：
   - ecs:DescribeZones
   - ecs:DescribeInstances
   - ecs:RunInstances
   - vpc:DescribeVpcs
   - vpc:DescribeVSwitches
   - ecs:DescribeSecurityGroups

## 输出信息

部署完成后会输出：

- `instance_id`: ECS实例ID
- `public_ip`: 公网IP地址
- `private_ip`: 内网IP地址
- `vpc_id`: VPC ID
- `vswitch_id`: VSwitch ID

## 注意事项

1. 如果没有密钥对，可以设置密码进行SSH登录
2. 默认使用Ubuntu 20.04镜像
3. 默认系统盘40GB，可根据需要调整
4. 如果使用默认安全组，请确保安全组规则允许必要的访问
