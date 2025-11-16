# Java代码与Terraform配置对应关系

这个文档说明了Java SDK代码中的配置参数如何对应到Terraform配置中。

## 基本配置对应

| Java变量 | 值 | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `regionId` | `"cn-shenzhen"` | `ALI_REGION` | `provider.region` |
| `zoneId` | `"cn-shenzhen-e"` | `AVAILABILITY_ZONE` | `availability_zone` |
| `instanceType` | `"ecs.c7a.large"` | `ALI_ECS_INSTANCE_TYPE` | `instance_type` |
| `instanceChargeType` | `"PostPaid"` | `INSTANCE_CHARGE_TYPE` | `instance_charge_type` |
| `imageId` | `"ubuntu_24_04_x64_20G_alibase_20251102.vhd"` | `IMAGE_ID` | `image_id` |
| `vSwitchId` | `"vsw-wz9uncyx33urqcxpj8c1p"` | `VSWITCH_ID` | `vswitch_id` |
| `securityGroupId` | `"sg-wz9eo52rpleayua0e1s6"` | `SECURITY_GROUP_ID` | `security_groups` |
| `instanceName` | `"egr-[0,6]"` | `ALI_ECS_NAME` | `instance_name` |
| `hostName` | `"egr-[0,6]"` | `HOST_NAME` | `host_name` |
| `autoReleaseTime` | `"2025-11-16T18:48:30Z"` | `AUTO_RELEASE_TIME` | `auto_release_time` |

## 系统盘配置对应

| Java配置 | 值 | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `systemDisk.size` | `"40"` | `SYSTEM_DISK_SIZE` | `system_disk_size` |
| `systemDisk.category` | `"cloud_essd"` | `SYSTEM_DISK_CATEGORY` | `system_disk_category` |
| *系统盘名称* | *自动生成* | `SYSTEM_DISK_NAME` | `system_disk_name` |
| `systemDisk.performanceLevel` | `"PL0"` | `SYSTEM_DISK_PERFORMANCE_LEVEL` | `system_disk_performance_level` |

## 网络配置对应

| Java变量 | 值 | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `internetChargeType` | `"PayByTraffic"` | `INTERNET_CHARGE_TYPE` | `internet_charge_type` |
| `internetMaxBandwidthOut` | `100` | `INTERNET_MAX_BANDWIDTH_OUT` | `internet_max_bandwidth_out` |

## 竞价实例配置对应

| Java变量 | 值（已移除） | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `spotStrategy` | *已移除* | `SPOT_STRATEGY` | `spot_strategy` |
| `spotDuration` | *已移除* | `SPOT_DURATION` | `spot_duration` |

**竞价实例配置说明**：
- Java代码中已移除竞价相关配置，使用纯按量付费模式
- Terraform保留竞价配置选项，支持灵活切换
- 默认为 `SPOT_STRATEGY = "NoSpot"`（按量付费）
- 可通过修改变量切换为竞价模式

## 安全配置对应

| Java变量 | 值 | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `securityEnhancementStrategy` | `"Active"` | `SECURITY_ENHANCEMENT_STRATEGY` | `security_enhancement_strategy` |
| `httpTokens` | `"optional"` | `HTTP_TOKENS` | `http_tokens` |

## 其他配置对应

| Java变量 | 值 | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `ioOptimized` | `"optimized"` | `IO_OPTIMIZED` | *(已废弃)* |
| `tenancy` | `"default"` | - | *(默认值)* |
| `affinity` | `"default"` | - | *(默认值)* |
| `amount` | `1` | - | *(单实例)* |

## 自动释放时间配置

| Java变量 | 值 | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `autoReleaseTime` | `"2025-11-16T18:48:30Z"` | `AUTO_RELEASE_TIME` | `auto_release_time` |

**重要说明**：
- 自动释放时间仅对按量付费（PostPaid）实例有效
- 时间格式必须为UTC时间，遵循RFC3339格式（如：`2025-11-16T18:48:30Z`）
- 设置后实例会在指定时间自动释放，请确保重要数据已备份
- 如果不设置或设置为空字符串，实例将不会自动释放

## CPU选项配置

Java代码中的CPU选项：
```java
private RunInstancesRequestCpuOptions cpuOptions =
  new RunInstancesRequestCpuOptions().setCore(1).setThreadsPerCore(2);
```

在Terraform中，这通常由实例类型 `ecs.c7a.large` 自动处理，不需要单独配置。

## 镜像选项配置

Java代码中的镜像选项：
```java
private RunInstancesRequestImageOptions imageOptions =
  new RunInstancesRequestImageOptions().setLoginAsNonRoot(false);
```

在Terraform中，这是镜像的默认行为，不需要单独配置。

## 重要差异说明

### 系统盘名称
- **Java SDK**: 自动生成磁盘名称，无需手动指定
- **Terraform**: 需要手动指定符合命名规范的磁盘名称
- **解决方案**: 使用静态名称 `"egr-system"` 避免特殊字符导致的错误

### 实例名称中的特殊字符
- **问题**: `[0,6]` 这样的占位符在磁盘名称中不被允许
- **影响**: 系统盘名称不能直接使用实例名称模板
- **解决**: 系统盘使用独立的静态名称

## 实例命名配置

| Java变量 | 值 | Terraform变量 | Terraform属性 |
|---------|---|-------------|-------------|
| `instanceName` | `"egr-[0,6]"` | `ALI_ECS_NAME` | `instance_name` |
| `hostName` | `"egr-[0,6]"` | `HOST_NAME` | `host_name` |

**命名规则说明**：
- `[0,6]` 是阿里云的自动编号格式，表示从0开始的6位数字后缀
- 实际创建的实例名称会是：`egr-000001`, `egr-000002` 等
- 主机名（hostname）是系统内部的计算机名称，用于网络识别
- 实例名称（instance name）是在阿里云控制台显示的名称

## 使用说明

1. 复制 `terraform.tfvars.example` 到 `terraform.tfvars`
2. 根据Java代码中的具体值填写配置
3. 确保VPC ID与Java代码中的VSwitchId在同一个VPC下
4. 运行 `terraform init && terraform plan && terraform apply`

## 注意事项

- 某些Java代码中的配置在Terraform provider中可能不支持或已废弃
- 网络资源ID必须手动指定以避免权限问题
- 确保所有资源在同一个地域和可用区
