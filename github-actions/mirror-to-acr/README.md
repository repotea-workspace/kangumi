# Mirror Docker Images to Aliyun ACR

This action mirrors Docker images from public or private registries (Docker Hub, GHCR, Quay.io, etc.) to Alibaba Cloud Container Registry (ACR) via internal network.

## Why this action?

Since servers in China cannot directly access Docker Hub and other international registries, this action:

1. Pulls images on GitHub Actions runners (outside China)
2. Saves images as tar files
3. Provisions an Aliyun ECS instance in China
4. Uploads tar files to ECS via SCP
5. Loads and pushes images to ACR via internal network
6. Destroys the ECS instance

## Usage

There are **three ways** to specify which images to mirror:

### Method 1: Single Image (Quick)

For mirroring a single image to one or more targets, use `source_image` and `target_image`:

```yaml
# Single target
- uses: ./github-actions/mirror-to-acr
  with:
    source_image: ghcr.io/org/app:v1.0.0
    target_image: registry-vpc.cn-shenzhen.aliyuncs.com/myns/app:v1.0.0
    # ... other inputs

# Multiple targets (comma or newline separated)
- uses: ./github-actions/mirror-to-acr
  with:
    source_image: ghcr.io/org/app:v1.0.0
    target_image: |
      registry-vpc.cn-shenzhen.aliyuncs.com/myns/app:v1.0.0
      registry-vpc.cn-shenzhen.aliyuncs.com/myns/app:latest
    # ... other inputs
```

### Method 2: Inline Config (Dynamic)

Provide config content directly as a YAML string. Supports both single `target` and multiple `targets`:

```yaml
- uses: ./github-actions/mirror-to-acr
  with:
    config_content: |
      mirror:
        # Single target (legacy format)
        - source: docker.io/nginx:1.25
          target: registry-vpc.cn-shenzhen.aliyuncs.com/myns/nginx:1.25

        # Multiple targets (new format)
        - source: ghcr.io/org/app:v1.0.0
          targets:
            - registry-vpc.cn-shenzhen.aliyuncs.com/myns/app:v1.0.0
            - registry-vpc.cn-shenzhen.aliyuncs.com/myns/app:latest
    # ... other inputs
```

This is useful when generating the config dynamically in a previous step.

### Method 3: Config File (Traditional)

Create a YAML config file (e.g., `mirror-config.yaml`) with the images to mirror:

```yaml
mirror:
  # Single target
  - source: bitnami/sealed-secrets-controller:0.33.1
    target: crpi-xxx.cn-shenzhen.personal.cr.aliyuncs.com/coohub/bitnami_sealed-secrets-controller:0.33.1

  # Multiple targets - mirror to both SZ and HK regions
  - source: ghcr.io/0xfe10/cert-manager-alicloud-esa-webhook:v0.1.10
    targets:
      - crpi-xxx.cn-shenzhen.personal.cr.aliyuncs.com/coohub/0xfe10_cert-manager-alicloud-esa-webhook:v0.1.10
      - registry-vpc.cn-hongkong.aliyuncs.com/coohub/0xfe10_cert-manager-alicloud-esa-webhook:v0.1.10
```

```yaml
- uses: ./github-actions/mirror-to-acr
  with:
    config_file: mirror-config.yaml
    # ... other inputs
```

### Naming Convention

Convert source image path to target name by replacing `/` with `_`:

| Source | Target Name |
|--------|-------------|
| `bitnami/sealed-secrets-controller:0.33.1` | `bitnami_sealed-secrets-controller:0.33.1` |
| `ghcr.io/0xfe10/cert-manager-alicloud-esa-webhook:v0.1.10` | `0xfe10_cert-manager-alicloud-esa-webhook:v0.1.10` |
| `docker.io/kubernetesui/dashboard-web:1.7.0` | `kubernetesui_dashboard-web:1.7.0` |

### Workflow Example

```yaml
name: Mirror Images to ACR

on:
  push:
    paths:
      - 'mirror-config.yaml'
  workflow_dispatch:

env:
  ECS_REGION: cn-shenzhen
  ECS_VSWITCH_ID: vsw-xxxxx
  ECS_AVAILABILITY_ZONE: cn-shenzhen-e
  ECS_SECURITY_GROUP_ID: sg-xxxxx
  ECS_KEYPAIR_NAME: keypair-ali-generic

jobs:
  mirror:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Mirror images to ACR
        uses: ./github-actions/mirror-to-acr
        with:
          config_file: mirror-config.yaml

          # Registry credentials (JSON format)
          # Keys are registry hosts, values are {username, password} objects
          # Supports multiple source and target registries
          registry_credentials: |
            {
              "ghcr.io": {
                "username": "${{ github.actor }}",
                "password": "${{ secrets.GITHUB_TOKEN }}"
              },
              "docker.io": {
                "username": "${{ secrets.DOCKER_USERNAME }}",
                "password": "${{ secrets.DOCKER_PASSWORD }}"
              },
              "crpi-xxx.cn-shenzhen.personal.cr.aliyuncs.com": {
                "username": "${{ secrets.ACR_USERNAME }}",
                "password": "${{ secrets.ACR_PASSWORD }}"
              },
              "crpi-yyy.cn-hangzhou.personal.cr.aliyuncs.com": {
                "username": "${{ secrets.ACR_HZ_USERNAME }}",
                "password": "${{ secrets.ACR_HZ_PASSWORD }}"
              }
            }

          # Aliyun credentials
          ali_access_key: ${{ secrets.ALI_ACCESS_KEY }}
          ali_secret_key: ${{ secrets.ALI_SECRET_KEY }}
          ali_region: ${{ env.ECS_REGION }}

          # ECS configuration
          vswitch_id: ${{ env.ECS_VSWITCH_ID }}
          availability_zone: ${{ env.ECS_AVAILABILITY_ZONE }}
          security_group_id: ${{ env.ECS_SECURITY_GROUP_ID }}
          key_pair_name: ${{ env.ECS_KEYPAIR_NAME }}
          ssh_private_key: ${{ secrets.SSH_KEYPAIR_ALI_GENERIC }}
```

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `source_image` | Source image to mirror (use with `target_image`) | No* | - |
| `target_image` | Target image in ACR (use with `source_image`) | No* | - |
| `config_content` | YAML config content as string | No* | - |
| `config_file` | Path to YAML config file | No* | - |
| `registry_credentials` | JSON object with registry credentials (see below) | No | `{}` |
| `ali_access_key` | Alibaba Cloud Access Key | Yes | - |
| `ali_secret_key` | Alibaba Cloud Secret Key | Yes | - |
| `ali_region` | Alibaba Cloud region | Yes | `cn-shenzhen` |
| `vswitch_id` | VSwitch ID | Yes | - |
| `availability_zone` | Availability zone | Yes | - |
| `security_group_id` | Security group ID | Yes | - |
| `image_id` | ECS image ID | No | Ubuntu 24.04 |
| `instance_type` | ECS instance type | No | `ecs.c7a.large` |
| `system_disk_size` | System disk size (GB) | No | `40` |
| `spot_strategy` | Spot strategy | No | `SpotAsPriceGo` |
| `key_pair_name` | SSH key pair name (for key-based auth) | No | - |
| `ssh_private_key` | SSH private key (for key-based auth) | No | - |
| `instance_password` | ECS instance password (for password auth) | No | - |
| `post_ssh_wait_seconds` | Wait time after SSH ready | No | `30` |
| `scp_timeout` | SCP timeout | No | `30m` |
| `ssh_timeout` | SSH timeout | No | `30m` |
| `ecs_auto_release_hours` | Hours until ECS auto-release (safety) | No | `1` |

\* You must provide **one of**: `source_image` + `target_image`, `config_content`, or `config_file`

### Authentication Options

You can choose one of two authentication methods for ECS SSH access:

**Option 1: Key-based authentication**
```yaml
key_pair_name: ${{ env.ECS_KEYPAIR_NAME }}
ssh_private_key: ${{ secrets.SSH_KEYPAIR_ALI_GENERIC }}
```

**Option 2: Password authentication**
```yaml
instance_password: ${{ secrets.ECS_PASSWORD }}
```

## Outputs

| Name | Description |
|------|-------------|
| `mirrored_images` | JSON array of mirrored image targets |

## Required Secrets

- `ALI_ACCESS_KEY` - Alibaba Cloud Access Key ID
- `ALI_SECRET_KEY` - Alibaba Cloud Secret Key
- `SSH_KEYPAIR_ALI_GENERIC` - SSH private key for ECS access (if using key-based auth)
- Or `ECS_PASSWORD` - ECS instance password (if using password auth)

### Registry Credentials Format

The `registry_credentials` input is a JSON object where:
- Keys are registry hosts (e.g., `ghcr.io`, `docker.io`, `crpi-xxx.cn-shenzhen.personal.cr.aliyuncs.com`)
- Values are objects with `username` and `password` fields

```json
{
  "ghcr.io": {
    "username": "github-username",
    "password": "github-token"
  },
  "crpi-xxx.cn-shenzhen.personal.cr.aliyuncs.com": {
    "username": "acr-username",
    "password": "acr-password"
  }
}
```

**Note:** The action automatically detects which registries are used from the `source` and `target` fields in your config file, and logs in to those registries using the provided credentials.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       GitHub Actions                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │  0. docker login│    │  2. docker save │    │  3. SCP tar  │ │
│  │  (optional)     │    │  (create tar)   │    │  to ECS      │ │
│  └────────┬────────┘    └────────▲────────┘    └──────────────┘ │
│           │                      │                               │
│           v                      │                               │
│  ┌─────────────────┐             │                               │
│  │  1. docker pull │ ────────────┘                               │
│  │  (public/private│                                             │
│  └─────────────────┘                                             │
└──────────────────────────────────────────────────────────────────┘
                                                         │
                                                         v
┌──────────────────────────────────────────────────────────────────┐
│                     Aliyun ECS (China)                           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │  4. docker load │ -> │  5. docker tag  │ -> │ 6. docker    │ │
│  │  (restore img)  │    │  (rename)       │    │ push (ACR)   │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                                         │
                                                         v
                                              ┌──────────────────┐
                                              │  Aliyun ACR      │
                                              │  (internal net)  │
                                              └──────────────────┘
```
