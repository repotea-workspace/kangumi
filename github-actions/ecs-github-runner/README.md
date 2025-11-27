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

## 运行机制

- 当 `mode: start`：
  - Action 会请求 GitHub registration token → `terraform apply`（`RUNNER_ENABLED=true`）→ 上传 `terraform.tfstate` artifact。
  - 输出 `runner-label`、`runner-name`、`instance-id`、`public-ip` 等，供后续 job 复用。
- 当 `mode: destroy`：
  - Action 下载同名 artifact → `terraform apply -var "RUNNER_ENABLED=false"`，保证 ECS 被销毁 → 删除本地 state。

Terraform 变量与 Java 代码的映射详情请见 [`terraform/JAVA_TERRAFORM_MAPPING.md`](./terraform/JAVA_TERRAFORM_MAPPING.md)。
