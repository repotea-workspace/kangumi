# Dev Toolchain Helm Chart

A Helm chart for deploying development toolchain containers with Docker-in-Docker (DinD) support on Kubernetes.

## Features

- 🐳 **Docker-in-Docker Support**: Run Docker commands inside containers via DinD sidecar
- 🔒 **Secure Architecture**: Main container runs without privileged mode; only DinD sidecar requires privileges
- 💾 **Persistent Storage**: PVC-based storage with flexible mount configurations
- 🌐 **NodePort Services**: SSH and custom ports in the 17000-18000 range
- 🚀 **Multi-Instance**: Deploy multiple independent toolchain instances
- 📦 **Flexible Configuration**: Comprehensive values.yaml with sensible defaults

## Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.0+
- StorageClass supporting ReadWriteOnce (for main PVC)
- StorageClass supporting ReadWriteMany (optional, for shared storage)
- NodePort range 17000-18000 available

## Architecture

```
┌─────────────────────────────────────────┐
│  Pod: dev-toolchain-fewensa             │
│                                         │
│  ┌─────────────────┐  ┌──────────────┐ │
│  │ dev-toolchain   │  │ dind         │ │
│  │ (main)          │  │ (sidecar)    │ │
│  │                 │  │              │ │
│  │ Docker CLI ─────┼──┼─→ Docker     │ │
│  │ (tcp://localhost:2375)  Daemon   │ │
│  │                 │  │              │ │
│  │ Dev Tools       │  │ privileged   │ │
│  │ (no privilege)  │  │              │ │
│  └─────────────────┘  └──────────────┘ │
│         │                     │         │
│         └─────────┬───────────┘         │
│                   ↓                     │
│           Shared Network                │
│           PVC Volumes                   │
└─────────────────────────────────────────┘
```

## Installation

### Quick Start

1. Add the repository (if published to OCI registry):
   ```bash
   helm repo add kangumi oci://ghcr.io/repotea-workspace/kangumi
   helm repo update
   ```

2. Install with default values:
   ```bash
   helm install dev-tc ./dev-toolchain -n dev-toolchain --create-namespace
   ```

### Custom Installation

1. Create a custom `values.yaml`:
   ```yaml
   toolchains:
     fewensa:
       enabled: true
       ports:
         ssh:
           nodePort: 17000
         extra:
           - name: http
             containerPort: 8080
             nodePort: 17100
       storage:
         pvc:
           enabled: true
           size: 200Gi
   ```

2. Install with custom values:
   ```bash
   helm install dev-tc ./dev-toolchain \
     -n dev-toolchain \
     --create-namespace \
     -f custom-values.yaml
   ```

## Configuration

### Global Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Container image registry | `ghcr.io` |
| `global.imagePullPolicy` | Image pull policy | `Always` |
| `global.imagePullSecrets` | Image pull secrets | `[]` |

### Toolchain Instance Configuration

Each toolchain instance supports the following configuration:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `enabled` | Enable/disable this instance | `true` |
| `hostname` | Container hostname | `tch-<name>` |
| `image` | Container image | `repotea-workspace/kangumi/dev-toolchain:latest` |
| `machineId` | Machine ID for SSH key generation | `""` |

### Port Configuration

SSH port follows the pattern: `17000 + instance_number`

```yaml
ports:
  ssh:
    containerPort: 22
    nodePort: 17000      # Fixed: 17000-17999
  extra:                  # Shared pool: 17100-18000
    - name: http
      containerPort: 8080
      nodePort: 17100
    - name: https
      containerPort: 8443
      nodePort: 17101
```

### Storage Configuration

#### Main PVC (per instance)

```yaml
storage:
  pvc:
    enabled: true
    name: tch-fewensa-data
    storageClassName: ""  # Use cluster default
    size: 100Gi
    accessMode: ReadWriteOnce
```

#### Volume Mounts

The PVC is organized with subPaths for different purposes:

| Mount Path | SubPath | Purpose |
|------------|---------|---------|
| `/etc/profile.d/env.sh` | `config/env.sh` | Environment variables |
| `/etc/ssh/sshd_config.d` | `config/sshd_config.d` | SSH configuration |
| `/root` | `home/root` | Root home directory |
| `/home` | `home/users` | User home directories |
| `/data` | `workspace/data` | Data directory |
| `/opt` | `workspace/opt` | Software installations |
| `/code` | `workspace/code` | Code repositories |

#### Shared PVC (optional)

For shared storage across instances (requires ReadWriteMany):

```yaml
storage:
  sharedPVC:
    enabled: true
    name: dev-shared-wwwroot
    storageClassName: nfs-client  # Must support RWX
    size: 50Gi
    accessMode: ReadWriteMany
    mountPath: /data/wwwroot
```

### Docker-in-Docker Configuration

```yaml
dind:
  enabled: true
  image: docker:27-dind
  storage:
    type: emptyDir  # or 'pvc' for persistence
    # size: 50Gi    # only if type: pvc
```

### Resource Limits

```yaml
resources:
  limits:
    cpu: "8"
    memory: 32Gi
  requests:
    cpu: "2"
    memory: 4Gi
```

## Usage Examples

### Connecting via SSH

After deployment, get the node IP:
```bash
kubectl get nodes -o wide
```

Connect to the toolchain:
```bash
ssh -p 17000 root@<NODE_IP>
```

### Using Docker Inside Container

Once connected via SSH:
```bash
# Test Docker
docker run hello-world

# Build images
docker build -t myapp .

# Run containers
docker run -d -p 8080:8080 myapp
```

### Accessing Additional Ports

If you configured extra ports:
```yaml
ports:
  extra:
    - name: webapp
      containerPort: 8080
      nodePort: 17100
```

Access from outside:
```bash
curl http://<NODE_IP>:17100
```

### Multiple Instances

Deploy two independent toolchains:
```yaml
toolchains:
  fewensa:
    enabled: true
    ports:
      ssh:
        nodePort: 17000
  
  0xfe10:
    enabled: true
    ports:
      ssh:
        nodePort: 17001
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n dev-toolchain
kubectl describe pod <pod-name> -n dev-toolchain
```

### View Logs

Main container:
```bash
kubectl logs deployment/<deployment-name> -n dev-toolchain
```

DinD sidecar:
```bash
kubectl logs deployment/<deployment-name> -c dind -n dev-toolchain
```

### Access Container Shell

```bash
kubectl exec -it deployment/<deployment-name> -n dev-toolchain -- /bin/bash
```

### Common Issues

#### 1. Docker commands fail

**Symptom**: `Cannot connect to the Docker daemon`

**Solution**: 
- Check DinD sidecar is running: `kubectl logs <pod> -c dind`
- Verify DOCKER_HOST environment variable: `echo $DOCKER_HOST` (should be `tcp://localhost:2375`)

#### 2. PVC not binding

**Symptom**: PVC stuck in `Pending` state

**Solution**:
- Check StorageClass exists: `kubectl get sc`
- Verify storage provisioner is working
- Check PVC events: `kubectl describe pvc <pvc-name>`

#### 3. SSH connection refused

**Symptom**: Cannot connect via SSH

**Solution**:
- Check service exists: `kubectl get svc`
- Verify NodePort is in allowed range
- Check if sshd is running inside container
- Verify firewall rules on nodes

#### 4. Shared PVC mount fails

**Symptom**: Pod fails to start with mount error

**Solution**:
- Ensure StorageClass supports ReadWriteMany
- Check if NFS/CephFS provisioner is configured
- Verify PVC is created: `kubectl get pvc`

## Upgrading

```bash
helm upgrade dev-tc ./dev-toolchain \
  -n dev-toolchain \
  -f values.yaml
```

## Uninstalling

```bash
helm uninstall dev-tc -n dev-toolchain
```

**Note**: PVCs are not automatically deleted. To remove them:
```bash
kubectl delete pvc -l app.kubernetes.io/name=dev-toolchain -n dev-toolchain
```

## Advanced Configuration

### Using Private Registry

```yaml
global:
  imageRegistry: my-registry.example.com
  imagePullSecrets:
    - name: regcred

toolchains:
  fewensa:
    image: my-org/dev-toolchain:v1.0.0
```

Create the secret:
```bash
kubectl create secret docker-registry regcred \
  --docker-server=my-registry.example.com \
  --docker-username=<username> \
  --docker-password=<password> \
  -n dev-toolchain
```

### Node Affinity

Pin toolchain to specific nodes:
```yaml
toolchains:
  fewensa:
    nodeSelector:
      kubernetes.io/hostname: node1
    
    # Or use affinity for more complex rules
    affinity:
      nodeAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
          - matchExpressions:
            - key: node-role.kubernetes.io/worker
              operator: In
              values:
              - "true"
```

### Health Probes

Enable health checks:
```yaml
livenessProbe:
  enabled: true
  exec:
    command:
      - /bin/sh
      - -c
      - pgrep sshd
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  enabled: true
  tcpSocket:
    port: 22
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Custom Environment Variables

```yaml
toolchains:
  fewensa:
    env:
      - name: TZ
        value: Asia/Shanghai
      - name: LANG
        value: en_US.UTF-8
      - name: CUSTOM_VAR
        value: custom-value
```

## Security Considerations

1. **Privileged Containers**: Only the DinD sidecar runs with `privileged: true`. The main container runs without privileges.

2. **Network Isolation**: Consider using NetworkPolicy to restrict traffic.

3. **SSH Keys**: Use strong SSH keys and consider disabling password authentication.

4. **Resource Limits**: Always set resource limits to prevent resource exhaustion.

5. **Storage**: Use encryption at rest for sensitive data in PVCs.

## Contributing

Contributions are welcome! Please submit issues and pull requests to the repository.

## License

This Helm chart is part of the kangumi project.

## Support

For issues and questions:
- GitHub Issues: https://github.com/repotea-workspace/kangumi/issues
- Documentation: https://github.com/repotea-workspace/kangumi

## Changelog

### v0.1.0 (Initial Release)
- Docker-in-Docker sidecar pattern
- Multi-instance support
- Flexible storage configuration with PVC subPaths
- NodePort services (17000-18000 range)
- Comprehensive configuration options