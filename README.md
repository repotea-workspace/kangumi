# Kangumi

> 一个全面的 Helm charts、Docker 镜像和 GitLab CI/CD 工作流集合，用于 Kubernetes 和容器化应用程序的部署和管理。

## 📁 项目结构

该存储库作为可重复使用的基础设施组件和部署工具的集中式枢纽。

### 🚢 Helm Charts

通过 OCI 注册表分发的即用型 Kubernetes 应用程序，提供可自定义的配置：

| Chart | 描述 | OCI 地址 | 版本 |
|-------|------|----------|------|
| any-cors | CORS-anywhere 代理服务 | `oci://ghcr.io/repotea-workspace/kangumi/any-cors` | v0.1.13 |

#### 安装方式

使用 OCI 注册表安装 Helm chart：

```bash
# 安装 any-cors
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors

# 使用自定义值文件
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors -f values.yaml

# 升级现有部署
helm upgrade my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors
```

### 🐳 Docker 镜像

针对各种使用场景优化的容器镜像：

| 镜像 | 描述 |
|------|------|
| [appbox](docker-image/appbox) | 应用程序沙盒环境 |
| [artelad](docker-image/artelad) | Artelad 区块链节点 |
| [cypress-browsers-edge](docker-image/cypress-browsers-edge) | 支持 Edge 浏览器的 Cypress 测试环境 |
| [dev-toolchain](docker-image/dev-toolchain) | 开发工具容器 |
| [fat-android-sdk](docker-image/fat-android-sdk) | 包含附加工具的 Android SDK |
| [fuel](docker-image/fuel) | Fuel 区块链组件 |
| [gotenberg](docker-image/gotenberg) | 文档转换服务 |
| [harmonytools](docker-image/harmonytools) | Harmony 区块链工具 |
| [k8ops](docker-image/k8ops) | Kubernetes 运维工具 |
| [node-liveness-probe](docker-image/node-liveness-probe) | Node 健康监控探针 |
| [nubit](docker-image/nubit) | Nubit 区块链节点 |
| [srtool](docker-image/srtool) | Substrate 运行时构建工具 |
| [terraform](docker-image/terraform) | Terraform 基础设施自动化 |

### ⚙️ GitLab 工作流

可重复使用的 CI/CD 流水线定义：

- **definition.yml** - 通用流水线定义
- **deploy.yml** - 部署工作流
- **docker.yml** - Docker 构建和推送流水线
- **generic.yml** - 通用可重复使用模板
- **github.yml** - GitHub 集成工作流
- **helm.yml** - Helm chart 部署流水线
- **maven.yml** - 基于 Maven 的 Java 项目工作流
- **npm.yml** - Node.js/NPM 项目工作流
- **vercel.yml** - Vercel 部署工作流

## 🚀 快速开始

### 使用 Helm Charts

从 OCI 注册表直接安装：

```bash
# 使用默认配置安装
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors

# 使用自定义配置
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors --set service.port=8080

# 查看可用的配置选项
helm show values oci://ghcr.io/repotea-workspace/kangumi/any-cors
```

### 使用 Docker 镜像

```bash
# 拉取并运行预构建镜像
docker pull ghcr.io/repotea-workspace/kangumi/<image-name>:<tag>
docker run ghcr.io/repotea-workspace/kangumi/<image-name>:<tag>
```

### 使用 GitLab CI 工作流

在你的 `.gitlab-ci.yml` 中包含工作流：

```yaml
include:
  - project: 'repotea-workspace/kangumi'
    ref: main
    file: '/gitlab-workflow/docker.yml'
  - project: 'repotea-workspace/kangumi'
    ref: main
    file: '/gitlab-workflow/helm.yml'
```

## � 要求

### Helm Charts
- Kubernetes 1.19+
- Helm 3.8+

### Docker 镜像
- Docker 20.10+
- 或兼容的容器运行时

### GitLab 工作流
- GitLab CI/CD 14.0+

## 🔧 开发指南

### 项目维护

这个项目包含多个组件的维护脚本：

- **Docker 镜像构建自动化**
- **Helm chart 版本管理**
- **CI/CD 流水线模板**

### 贡献

1. Fork 本项目
2. 创建特性分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request

### 目录结构说明

```
kangumi/
├── docker-image/          # Docker 镜像源码
├── gitlab-workflow/       # GitLab CI 工作流模板
├── helm-charts/          # Helm chart 源码
└── scripts/              # 维护和构建脚本
```

## 📄 许可证

本项目采用开源许可证。详情请参阅项目中的许可证文件。

---

**注意**: 所有 OCI 地址均指向 GitHub Container Registry (ghcr.io)，确保您有适当的访问权限。

