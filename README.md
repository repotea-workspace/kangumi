# Kangumi

> A comprehensive collection of Helm charts, Docker images, and GitLab CI/CD workflows for Kubernetes and containerized application deployment and management.

## 📁 Project Structure

This repository serves as a centralized hub for reusable infrastructure components and deployment tools.

### 🚢 Helm Charts

Ready-to-deploy Kubernetes applications distributed via OCI registry with customizable configurations:

| Chart    | Description                 | OCI Address                                        | Version |
| -------- | --------------------------- | -------------------------------------------------- | ------- |
| any-cors | CORS-anywhere proxy service | `oci://ghcr.io/repotea-workspace/kangumi/any-cors` | v0.1.13 |

#### Installation

Install Helm charts using OCI registry:

```bash
# Install any-cors
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors

# Use custom values file
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors -f values.yaml

# Upgrade existing deployment
helm upgrade my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors
```

### 🐳 Docker Images

Optimized container images for various use cases:

| Image                                                       | Description                                   |
| ----------------------------------------------------------- | --------------------------------------------- |
| [appbox](docker-image/appbox)                               | Application sandbox environment               |
| [artelad](docker-image/artelad)                             | Artelad blockchain node                       |
| [cypress-browsers-edge](docker-image/cypress-browsers-edge) | Cypress testing environment with Edge browser |
| [dev-toolchain](docker-image/dev-toolchain)                 | Development tools container                   |
| [fat-android-sdk](docker-image/fat-android-sdk)             | Android SDK with additional tools             |
| [fuel](docker-image/fuel)                                   | Fuel blockchain components                    |
| [gotenberg](docker-image/gotenberg)                         | Document conversion service                   |
| [harmonytools](docker-image/harmonytools)                   | Open Harmony tools                            |
| [k8ops](docker-image/k8ops)                                 | Kubernetes operations utilities               |
| [node-liveness-probe](docker-image/node-liveness-probe)     | Node health monitoring probe                  |
| [nubit](docker-image/nubit)                                 | Nubit blockchain node                         |
| [srtool](docker-image/srtool)                               | Substrate runtime building tools              |
| [terraform](docker-image/terraform)                         | Terraform infrastructure automation           |

### ⚙️ GitLab Workflows

Reusable CI/CD pipeline definitions:

- **definition.yml** - Common pipeline definitions
- **deploy.yml** - Deployment workflows
- **docker.yml** - Docker build and push pipelines
- **generic.yml** - Generic reusable templates
- **github.yml** - GitHub integration workflows
- **helm.yml** - Helm chart deployment pipelines
- **maven.yml** - Maven-based Java project workflows
- **npm.yml** - Node.js/NPM project workflows
- **vercel.yml** - Vercel deployment workflows

## 🚀 Quick Start

### Using Helm Charts

Install directly from OCI registry:

```bash
# Install with default configuration
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors

# Install with custom configuration
helm install my-cors oci://ghcr.io/repotea-workspace/kangumi/any-cors --set service.port=8080

# View available configuration options
helm show values oci://ghcr.io/repotea-workspace/kangumi/any-cors
```

### Using Docker Images

```bash
# Pull and run pre-built images
docker pull ghcr.io/repotea-workspace/kangumi/<image-name>:<tag>
docker run ghcr.io/repotea-workspace/kangumi/<image-name>:<tag>
```

### Using GitLab CI Workflows

Include workflows in your `.gitlab-ci.yml`:

```yaml
include:
  - project: "repotea-workspace/kangumi"
    ref: main
    file: "/gitlab-workflow/docker.yml"
  - project: "repotea-workspace/kangumi"
    ref: main
    file: "/gitlab-workflow/helm.yml"
```

## 📋 Requirements

### Helm Charts

- Kubernetes 1.19+
- Helm 3.8+

### Docker Images

- Docker 20.10+
- Or compatible container runtime

### GitLab Workflows

- GitLab CI/CD 14.0+

## 🔧 Development Guide

### Project Maintenance

This project includes maintenance scripts for multiple components:

- **Docker image build automation**
- **Helm chart version management**
- **CI/CD pipeline templates**

### Contributing

1. Fork this project
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Directory Structure

```
kangumi/
├── docker-image/          # Docker image source code
├── gitlab-workflow/       # GitLab CI workflow templates
├── helm-charts/          # Helm chart source code
└── scripts/              # Maintenance and build scripts
```

---

**Note**: All OCI addresses point to GitHub Container Registry (ghcr.io), ensure you have appropriate access permissions.
