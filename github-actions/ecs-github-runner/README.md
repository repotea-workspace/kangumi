ecs-github-runner
===

提供一个可复用的 GitHub Action，利用 `terraform/` 目录里的配置，在阿里云上按需创建 / 销毁自托管 ECS Runner。

## 用法

在需要动态 Runner 的工作流中，创建三个 job：

1. `provision-runner`：使用本 Action (`mode: start`) 创建 ECS，并输出唯一 label。
2. `run-on-ecs`：使用 `runs-on: [self-hosted, <label>]` 执行实际任务。
3. `destroy-runner`：使用本 Action (`mode: destroy`)，即使任务失败也会清理实例。

参考 [`workflow-example.yml`](./workflow-example.yml)：

```yaml
jobs:
  provision-runner:
    runs-on: ubuntu-latest
    outputs:
      runner-label: ${{ steps.start.outputs.runner-label }}
    steps:
      - id: start
        uses: kangumi/github-actions/ecs-github-runner@main
        with:
          mode: start
          github_owner: ${{ github.repository_owner }}
          github_repository: ${{ github.event.repository.name }}
          github_pat: ${{ secrets.GH_RUNNER_PAT }}
          ali_access_key: ${{ secrets.ALI_ACCESS_KEY }}
          ali_secret_key: ${{ secrets.ALI_SECRET_KEY }}
          ali_region: ${{ secrets.ALI_REGION }}
          vswitch_id: ${{ vars.ALI_VSWITCH_ID }}
          availability_zone: ${{ vars.ALI_AVAILABILITY_ZONE }}
          security_group_id: ${{ vars.ALI_SECURITY_GROUP_ID }}
          image_id: ${{ vars.ALI_IMAGE_ID }}

  run-on-ecs:
    needs: provision-runner
    runs-on:
      - self-hosted
      - ${{ needs.provision-runner.outputs.runner-label }}
    steps:
      - run: make test

  destroy-runner:
    if: always()
    needs:
      - provision-runner
      - run-on-ecs
    runs-on: ubuntu-latest
    steps:
      - uses: kangumi/github-actions/ecs-github-runner@main
        with:
          mode: destroy
          github_owner: ${{ github.repository_owner }}
          github_repository: ${{ github.event.repository.name }}
          ali_access_key: ${{ secrets.ALI_ACCESS_KEY }}
          ali_secret_key: ${{ secrets.ALI_SECRET_KEY }}
          ali_region: ${{ secrets.ALI_REGION }}
          vswitch_id: ${{ vars.ALI_VSWITCH_ID }}
          availability_zone: ${{ vars.ALI_AVAILABILITY_ZONE }}
          security_group_id: ${{ vars.ALI_SECURITY_GROUP_ID }}
          image_id: ${{ vars.ALI_IMAGE_ID }}
```

> `state_artifact_name` 默认是 `ecs-github-runner-tfstate`。如需修改，请确保 start/destroy 两个 job 输入一致。

## 必填输入

| 输入 | 说明 |
| --- | --- |
| `ali_access_key` / `ali_secret_key` / `ali_region` | 阿里云认证信息，建议存入 `Secrets` |
| `vswitch_id` | VSwitch ID，需与安全组在同一 VPC |
| `availability_zone` | 可用区，与 VSwitch 匹配 |
| `security_group_id` | 安全组 ID |
| `image_id` | ECS 镜像 ID（如 `ubuntu_24_04_x64_20G_alibase_20251102.vhd`） |
| `github_owner` | GitHub 组织或用户 |
| `github_repository` | 仓库名称（当 `github_scope=repo` 时）|
| `github_pat` 或 `github_runner_token` | PAT 用于换取 registration token，也可直接传入 token |

其余 Terraform 变量都有默认值，可通过输入覆盖，比如 `runner_name`、`runner_additional_labels`、`key_pair_name` 等。

## 可选配置

| 输入 | 默认值 | 作用 |
| --- | --- | --- |
| `runner_ephemeral` | `true` | 设置为 `false` 可在同一台机器上串行执行多个 Job（示例见 `multi-job.yml`） |
| `register_runner` | `true` | 设为 `false` 时仅创建 ECS 机器，不安装/注册 GitHub Runner（“Nonstd 模式”） |
| `expose_instance_password` | `false` | 若填 `true`，Action 会把 `instance_password` 作为输出返回，方便后续 SSH（谨慎使用） |
| `custom_user_data` | `""` | 追加自定义 shell 脚本到 user-data，满足个性化初始化需求（默认空） |
| `state_artifact_name` | `ecs-github-runner-tfstate` | 如果一个 workflow 需要多次创建/销毁，可用不同 artifact 名称隔离状态 |

## 运行机制

- 当 `mode: start`：
  - Action 会请求 GitHub registration token → `terraform apply`（`RUNNER_ENABLED=true`）→ 上传 `terraform.tfstate` artifact。
  - 输出 `runner-label`、`runner-name`、`instance-id`、`public-ip` 等，供后续 job 复用。
- 当 `mode: destroy`：
  - Action 下载同名 artifact → `terraform apply -var "RUNNER_ENABLED=false"`，保证 ECS 被销毁 → 删除本地 state。

Terraform 变量与 Java 代码的映射详情请见 [`terraform/JAVA_TERRAFORM_MAPPING.md`](./terraform/JAVA_TERRAFORM_MAPPING.md)。

## 示例工作流

`examples/` 目录提供了多种场景：

1. [`simple.yml`](./examples/simple.yml)：最小化示例，按顺序执行 “创建 → 单个 Job → 销毁”，并在最后调用 `remove-self-hosted-runner` Action 清理离线 Runner。
2. [`multi-job.yml`](./examples/multi-job.yml)：展示如何在同一 ECS Runner 上串行运行多个 Job（smoke test + Rust 构建/测试），以及如何生成自定义密码、复用标签和执行最终清理。
3. [`non-std.yml`](./examples/non-std.yml)：示例化 “只开机、不注册 Runner” 的流程，Action 会回传公网 IP 和密码，方便在受限网络环境下手动 SSH 进主机执行任务。

可以直接复制这些文件到你自己的仓库，根据文档替换变量/密钥即可。记得保留最后的销毁与清理步骤，避免遗留 ECS 资源或离线 Runner。

## Non-Standard 网络模式说明

由于 GitHub Actions 容器运行在境外，在中国大陆或其他受限网络环境下可能无法访问到 ECS 机器。此时可以：

1. `register_runner: "false"`：只创建 ECS 机器，不注册 Runner。
2. `expose_instance_password: "true"`：把实例密码作为输出返回，配合公网 IP 直接 SSH 登录。
3. 在工作流里提示运维人员使用输出信息登录到服务器（参考 [`non-std.yml`](./examples/non-std.yml)）。
4. 手动/脚本执行完毕后，仍需运行 `mode: destroy` 来释放实例。

> 如果你只需要“开机 + 获取凭据”，可以跳过 `run-on-ecs` 这样的自托管 Job，只保留 `provision` 和 `destroy` 两个 Job。
