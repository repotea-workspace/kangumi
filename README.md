# Kangumi

> A comprehensive collection of Helm charts, Docker images, and GitLab CI/CD workflows for Kubernetes and containerized applications.

## 📁 Project Structure

This repository serves as a centralized hub for reusable infrastructure components and deployment tools.

### 🚢 Helm Charts

Ready-to-deploy Kubernetes applications with customizable configurations:

| Chart | Description | Version |
|-------|-------------|---------|
| [any-cors](helm-charts/any-cors) | CORS-anywhere proxy service | v0.1.10 |
| [codimd](helm-charts/codimd) | Collaborative markdown editor | - |

### 🐳 Docker Images

Optimized container images for various use cases:

| Image | Description |
|-------|-------------|
| [appbox](docker-image/appbox) | Application sandbox environment |
| [artelad](docker-image/artelad) | Artelad blockchain node |
| [cypress-browsers-edge](docker-image/cypress-browsers-edge) | Cypress testing with Edge browser |
| [dev-toolchain](docker-image/dev-toolchain) | Development tools container |
| [fat-android-sdk](docker-image/fat-android-sdk) | Android SDK with additional tools |
| [fuel](docker-image/fuel) | Fuel blockchain components |
| [gotenberg](docker-image/gotenberg) | Document conversion service |
| [harmonytools](docker-image/harmonytools) | Harmony blockchain tools |
| [k8ops](docker-image/k8ops) | Kubernetes operations utilities |
| [node-liveness-probe](docker-image/node-liveness-probe) | Node health monitoring probe |
| [nubit](docker-image/nubit) | Nubit blockchain node |
| [srtool](docker-image/srtool) | Substrate runtime building tools |
| [terraform](docker-image/terraform) | Terraform infrastructure automation |

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

```bash
# Add the repository (if published to a Helm registry)
helm repo add kangumi <repository-url>

# Install a chart
helm install my-cors kangumi/any-cors

# Or install directly from source
helm install my-cors ./helm-charts/any-cors
```

### Using Docker Images

```bash
# Pull and run a pre-built image
docker pull <registry>/kangumi/<image-name>:<tag>
docker run <registry>/kangumi/<image-name>:<tag>
```

### Using GitLab CI Workflows

Include the workflows in your `.gitlab-ci.yml`:

```yaml
include:
  - project: 'repotea-workspace/kangumi'
    ref: main
    file: '/gitlab-workflow/docker.yml'
```

## 🔧 Development

### Project Maintenance

- **`.maintain/docker-image.sh`** - Docker image build automation
- **`.maintain/helm-charts.sh`** - Helm chart packaging and publishing

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test your changes
5. Submit a pull request

## 📝 License

This project is part of the repotea-workspace ecosystem.
