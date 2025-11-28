# ECS GitHub Runner Terraform Configuration

这个Terraform配置用于在阿里云上创建ECS实例作为GitHub Runner。

## 特点

- 使用现有的默认VPC和VSwitch，避免权限问题
- 支持使用默认安全组或创建自定义安全组
- 灵活的认证配置（密钥对或密码）

> ✅ 推荐：直接在 GitHub 工作流里使用 [`kangumi/github-actions/ecs-github-runner`](../action.yml) 这个 Action，它会自动调用本 Terraform 项目并处理状态文件。同时也可以在本地按以下步骤单独执行 Terraform。

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

复制示例配置文件：

```bash
cp terraform.tfvars.example terraform.tfvars
```

编辑 `terraform.tfvars` 文件，填入必需的资源ID：

```hcl
# 必填项
VPC_ID = "vpc-wz9hx87d99bvtrixq99f4"           # 你的VPC ID
VSWITCH_ID = "vsw-wz9abc123def456ghi"          # 你的VSwitch ID
AVAILABILITY_ZONE = "cn-shenzhen-a"            # VSwitch所在可用区
SECURITY_GROUP_ID = "sg-wz9xyz789abc012def"    # 你的安全组ID
IMAGE_ID = "ubuntu_20_04_x64_20G_alibase_20231221.vhd"  # Ubuntu镜像ID

# 可选配置
KEY_PAIR_NAME = "your-key-pair"                # 密钥对名称（推荐）
# INSTANCE_PASSWORD = "YourSecurePassword123!"  # 或者使用密码
SYSTEM_DISK_SIZE = 40                          # 系统盘大小
```

### 3. 选择计费模式（可选）

使用切换脚本轻松在不同计费模式间切换：

```bash
# 运行计费模式切换工具
chmod +x scripts/switch-billing-mode.sh
./scripts/switch-billing-mode.sh
```

或手动编辑terraform.tfvars：

```hcl
# 按量付费模式（默认，稳定）
SPOT_STRATEGY = "NoSpot"

# 竞价实例模式（便宜但可能被回收）
# SPOT_STRATEGY = "SpotAsPriceGo"
# SPOT_DURATION = 1
```

### 4. 执行部署

```bash
# 初始化
terraform init

# 规划
terraform plan

# 应用
terraform apply
```

当需要释放机器时，不必删除 `server.tf`，只需将变量 `RUNNER_ENABLED` 设为 `false` 再次 `apply` 即可：

```bash
terraform apply -auto-approve -var "RUNNER_ENABLED=false"
```

### 5. GitHub Action 工作流集成

参考 [machulav/ec2-github-runner](https://github.com/machulav/ec2-github-runner) 的做法，本仓库提供了 `../workflow-example.yml`，完整演示如何在 GitHub Actions 中按需创建/销毁阿里云 ECS Runner：

1. 将 `github-actions/ecs-github-runner/workflow-example.yml` 复制到你的项目 `.github/workflows/ecs-runner.yml`
2. 在仓库 Secrets 中配置：
   - `ALI_ACCESS_KEY`、`ALI_SECRET_KEY`、`ALI_REGION`
   - `GH_RUNNER_PAT`（拥有 `repo` + `workflow` + `self-hosted runners` 权限的 PAT，用于换取一次性的 Runner registration token）
3. 根据自己的 `terraform.tfvars` 完成 VPC/VSwitch/安全组/镜像等参数配置

工作流包含三个 Job：

- **provision-runner**：在 `ubuntu-latest` 上运行，调用 Terraform 创建 ECS，并通过 GitHub API 获取注册 token。创建成功后会把 `terraform.tfstate` 上传为 artifact 以供销毁阶段使用。
- **run-on-ecs**：在新建的自托管 Runner 上执行实际任务，使用 `self-hosted` + 动态标签（`ecs-${run_id}`）确保只绑定到本次实例。
- **destroy-runner**：`always()` 触发，先下载 Terraform state，再将 `RUNNER_ENABLED=false` 重新 `apply`，最终保证 ECS 被销毁，即使中途 Job 失败也会执行。

> ⚠️ `TF_VAR_GITHUB_RUNNER_TOKEN` 由工作流实时调用 GitHub API 生成，仅在 `provision-runner` job 中使用，`destroy-runner` 无需该值。

### 工作流中的状态同步

由于 GitHub Actions 的不同 Job 之间不会共享文件，需要通过 artifact 传递 `terraform.tfstate`：

```yaml
- name: Persist Terraform state for cleanup
  uses: actions/upload-artifact@v4
  with:
    name: ${{ env.TF_STATE_ARTIFACT }}
    path: |
      ${{ env.TF_WORKDIR }}/terraform.tfstate
```

销毁 Job 再用 `download-artifact` 取回 state 后执行 `terraform init && terraform apply -var "RUNNER_ENABLED=false"`，即可完成释放。

结合以上流程，可以做到：

- 当 GitHub Action 触发时自动执行 `terraform apply` 启动 ECS Runner
- Action 完成或失败都会执行清理逻辑，确保 `terraform` 状态为“未创建”
- 不再需要手动删除 `server.tf` 或手工执行 `terraform destroy`

### 4. 获取必需的资源ID

由于权限限制，所有资源ID都需要手动指定。请按以下步骤获取：

**方法1：通过阿里云控制台获取**

1. **VPC ID**：
   - 登录阿里云控制台 → VPC → 专有网络
   - 选择正确地域，复制VPC ID（格式：vpc-xxxxxxxxx）

2. **VSwitch ID**：
   - VPC → 交换机
   - 选择同一VPC下的交换机，复制VSwitch ID（格式：vsw-xxxxxxxxx）
   - 记住交换机所在的可用区

3. **安全组ID**：
   - ECS → 安全组
   - 选择同一VPC下的安全组，复制安全组ID（格式：sg-xxxxxxxxx）

4. **镜像ID**：
   - ECS → 镜像 → 公共镜像
   - 搜索"ubuntu_20_04"，选择最新版本
   - 复制镜像ID

**方法2：如果有阿里云CLI权限**

```bash
# 获取VPC
aliyun ecs DescribeVpcs --region cn-shenzhen

# 获取VSwitch
aliyun ecs DescribeVSwitches --region cn-shenzhen

# 获取安全组
aliyun ecs DescribeSecurityGroups --region cn-shenzhen

# 获取Ubuntu镜像
aliyun ecs DescribeImages --region cn-shenzhen --ImageOwnerAlias system --ImageName "*ubuntu_20_04*"
```## 输出信息

部署完成后会输出：

- `instance_id`: ECS实例ID
- `public_ip`: 公网IP地址
- `private_ip`: 内网IP地址
- `vpc_id`: VPC ID
- `vswitch_id`: VSwitch ID

## 注意事项

1. 如果没有密钥对，可以设置密码进行SSH登录
2. 默认使用Ubuntu 24.04镜像（与Java代码保持一致）
3. 默认系统盘40GB，可根据需要调整
4. 如果使用默认安全组，请确保安全组规则允许必要的访问
5. **实例命名**：
   - 实例名称：`egr-[0,6]`（阿里云会自动添加6位数字后缀）
   - 主机名：`egr-[0,6]`（系统内部计算机名称）
6. **计费模式**：
   - 默认使用按量付费模式（匹配Java代码）
   - 可通过修改 `SPOT_STRATEGY` 切换为竞价实例
   - 竞价实例价格更低但可能被系统回收
7. **系统盘命名**：
   - 系统盘名称必须符合阿里云命名规范
   - 不能包含特殊字符如 `[`, `]` 等
   - 默认使用 `egr-system` 静态名称
7. **自动释放时间**：
   - 仅对按量付费实例有效
   - 使用UTC时间格式（RFC3339）：`2025-11-16T18:48:30Z`
   - 实例会在指定时间自动释放，请提前备份重要数据
   - 如不设置，实例将不会自动释放
