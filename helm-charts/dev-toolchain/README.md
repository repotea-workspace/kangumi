# Dev Toolchain Helm Chart

A Helm chart for deploying development toolchain containers with a built-in Docker daemon on Kubernetes.

## Features

- 🐳 **Built-in Docker**: Run Docker CLI and dockerd in the main container
- 💾 **Persistent Storage**: PVC or per-directory hostPath storage
- 🌐 **Optional TUN Proxy**: Run Mihomo as a native sidecar for pod-wide egress
- 🌍 **Optional Port Gateway**: Publish dynamic HTTP/WebSocket development ports through one wildcard Ingress
- 🌐 **NodePort + ClusterIP Services**: external node ports plus optional in-cluster discovery for hostNetwork toolchains
- 🚀 **Multi-Instance**: Deploy multiple independent toolchain instances
- 📦 **Flexible Configuration**: Comprehensive values.yaml with sensible defaults
- 🛠️ **Auto-Install Dev Tools**: Automatically install development tools on first startup
- 🔧 **Unified Container**: Docker daemon runs in the main container, sharing the same filesystem

## Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.0+
- StorageClass supporting ReadWriteOnce (when using a main PVC)
- Kubernetes 1.29+ and `/dev/net/tun` on the selected node (when using the Mihomo sidecar)
- StorageClass supporting ReadWriteMany (optional, for shared storage)
- NodePort range 17000-18000 available

## Architecture

```
┌─────────────────────────────────────────┐
│  Pod: dev-toolchain-fewensa             │
│                                         │
│  ┌─────────────────────────────────────┐│
│  │ dev-toolchain (privileged)          ││
│  │                                     ││
│  │  ┌──────────────┐                  ││
│  │  │ Docker CLI   │                  ││
│  │  └──────┬───────┘                  ││
│  │         │ unix:///var/run/docker.sock
│  │         ↓                           ││
│  │  ┌──────────────┐                  ││
│  │  │ dockerd      │                  ││
│  │  │ (s6 service) │                  ││
│  │  └──────────────┘                  ││
│  │                                     ││
│  │  Dev Tools and SSH                  ││
│  │                                     ││
│  │  Shared filesystem for mounts       ││
│  └─────────────────────────────────────┘│
│                   ↓                     │
│        PVC or hostPath Volumes          │
└─────────────────────────────────────────┘
```

**Key improvements:**
- Docker daemon runs in the main container (managed by s6-overlay)
- Single filesystem - docker mounts work correctly
- No network overhead between CLI and daemon
- Simpler architecture, easier to debug

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

### Development Tools Auto-Installation

Automatically install development tools on first container startup:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `devTools.autoInstall` | Enable auto-installation | `false` |
| `devTools.packages` | List of tools to install (string or object format) | `[]` |

The `packages` field supports two formats:

#### 1. Simple String Format
For tools available in Homebrew or defined in `tools.yaml`:
```yaml
devTools:
  packages:
    - golang
    - nodejs
    - k8s-tools
    - terraform
```

#### 2. Object Format with Tap Support
For tools requiring custom taps (no need to rebuild Docker image):
```yaml
devTools:
  packages:
    - flutter
    - name: fvm
      tap: leoafarias/fvm
      formula: fvm  # optional, defaults to 'name'
    - name: talosctl
      tap: siderolabs/tap
      formula: siderolabs/tap/talosctl
```

#### 3. Mixed Format
Combine both formats as needed:
```yaml
devTools:
  packages:
    - golang          # Simple string
    - nodejs          # Simple string
    - name: fvm       # Object with custom tap
      tap: leoafarias/fvm
```

**Available predefined tools** (from `tools.yaml`):
- `nodejs` - Node.js and npm
- `golang` - Go programming language
- `java` - OpenJDK 17
- `flutter` - Flutter SDK
- `terraform` - Infrastructure as code
- `docker-compose` - Docker Compose
- `k8s-tools` - kubectl, helm, kustomize, helmfile, argocd, kubeseal
- `talosctl` - Talos Linux CLI (includes tap)
- `git-credential-manager` - Git credential helper
- Any Homebrew formula name

**Full Example**:
```yaml
toolchains:
  fewensa:
    devTools:
      autoInstall: true
      packages:
        - golang
        - nodejs
        - k8s-tools
        - name: fvm
          tap: leoafarias/fvm
```

**How it works**:
1. On first container startup, a `postStart` lifecycle hook runs
2. Checks for `/root/.dev-tools-installed` marker file
3. If not found, runs installation scripts for specified packages
4. Creates marker file to prevent duplicate installations
5. Subsequent restarts skip installation

**Manual installation**:
If you prefer manual installation, keep `autoInstall: false` and run scripts inside the container:
```bash
# SSH into container
ssh -p 17000 root@<NODE_IP>

# Run installation scripts
/opt/install-scripts/install-nodejs.sh
/opt/install-scripts/install-rust.sh
/opt/install-scripts/install-k8s-tools.sh
```

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

### hostNetwork + Service Discovery

When `network.mode: hostNetwork` is enabled, the pod can still reach normal Kubernetes
Services as long as `dnsPolicy: ClusterFirstWithHostNet` works in the cluster.

For reverse traffic from other pods back into the toolchain, declare fixed ports in
`ports.extra`. The chart will then create a `ClusterIP` Service automatically for
those ports even though the workload itself still uses `hostNetwork`.

```yaml
toolchains:
  vibe:
    network:
      mode: hostNetwork
      dnsPolicy: ClusterFirstWithHostNet
    ports:
      ssh:
        containerPort: 22
        nodePort: 17012
      extra:
        - name: webapp
          containerPort: 8080       # in-cluster Service port
          protocol: TCP
          # Optional when the real listener differs:
          # servicePort: 80
          # targetPort: 8080
```

Result:

- external access can still use node IP + host port
- in-cluster clients can use `{{service-name}}.{{namespace}}.svc.cluster.local`
- only explicitly declared fixed ports get Service discovery; arbitrary ad-hoc ports do not

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

#### Per-directory hostPath

Disable the PVC and give every mounted directory an absolute node path. This pins
the data to the selected node, so use a `nodeSelector` and the `Recreate` strategy
already provided by the chart.

```yaml
storage:
  pvc:
    enabled: false
  hostPath:
    enabled: true
  volumes:
    root:
      mountPath: /root
      hostPath: /data/dev-toolchain/birch/root
    docker:
      mountPath: /var/lib/docker
      hostPath: /data/dev-toolchain/birch/docker
```

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

### Mihomo TUN sidecar

```yaml
proxy:
  enabled: true
  image: metacubex/mihomo:v1.19.30
  config: |
    proxy-providers:
      subscription:
        type: http
        url: "__MIHOMO_SUBSCRIPTION_URL__"
  subscriptionSecretName: tch-birch-mihomo
```

The chart stores `proxy.config` in a ConfigMap. An init container replaces the fixed
URL placeholder from the Secret's `subscription-url` key and writes the final config
to an `emptyDir` for Mihomo. The config is responsible for enabling TUN routing and
excluding Kubernetes, node, metadata, and proxy-server destinations that must stay
direct. Updating the external Secret requires restarting the Pod. The legacy
`configSecretName`/`configKey` full-config Secret mode remains supported.

### Dynamic HTTP/WebSocket port gateway

The optional gateway exposes development services without `hostNetwork` or one
NodePort per service. The hostname encodes the target port: for example,
`p3018.birch.example.com` proxies to `127.0.0.1:3018` in the toolchain Pod.

```yaml
portGateway:
  enabled: true
  image: nginx:1.29-alpine
  hostSuffix: birch.example.com
  listenPort: 18080
  allowedPortRanges:
    - start: 3000
      end: 4000
    - start: 8000
      end: 9000
  ingress:
    className: nginx
    clusterIssuer: letsencrypt-prd
    tlsSecretName: tls-cert-birch-example-com
```

Create a wildcard DNS record for `*.birch.example.com` that points to the
Ingress endpoint. The chart creates a wildcard Ingress and asks cert-manager for
the origin certificate. Only HTTP, WebSocket, and SSE traffic is supported;
use SSH tunnels or explicit Service ports for raw TCP and UDP protocols.

The gateway validates the numeric port against `allowedPortRanges`, fixes the
upstream host to `127.0.0.1`, disables response caching, and uses a separate
ClusterIP Service so the gateway cannot bypass the Ingress through NodePort.

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
    devTools:
      autoInstall: true
      packages:
        - nodejs
        - rust
    ports:
      ssh:
        nodePort: 17000
  
  0xfe10:
    enabled: true
    devTools:
      autoInstall: true
      packages:
        - java
        - flutter
    ports:
      ssh:
        nodePort: 17001
```

### Auto-Installing Development Tools

Install tools automatically on first startup:
```bash
# Install with auto-install enabled
helm install dev-tc ./dev-toolchain \
  -n dev-toolchain \
  --create-namespace \
  --set toolchains.fewensa.devTools.autoInstall=true \
  --set toolchains.fewensa.devTools.packages="{nodejs,rust,gcm}"
```

Or use a values file:
```yaml
# custom-values.yaml
toolchains:
  fewensa:
    enabled: true
    devTools:
      autoInstall: true
      packages:
        - nodejs
        - rust
        - k8s-tools
        - gcm
```

```bash
helm install dev-tc ./dev-toolchain \
  -n dev-toolchain \
  --create-namespace \
  -f custom-values.yaml
```

**Check installation progress**:
```bash
# View container logs to see installation progress
kubectl logs -f deployment/dev-toolchain-fewensa -n dev-toolchain

# Expected output:
# → Installing dev tools...
# Installing nodejs...
# ✓ Node.js installed
# Installing rust...
# ✓ Rust installed
# ✓ Dev tools installation completed
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

Built-in Docker daemon:
```bash
kubectl exec deployment/<deployment-name> -n dev-toolchain -- docker info
```

### Access Container Shell

```bash
kubectl exec -it deployment/<deployment-name> -n dev-toolchain -- /bin/bash
```

### Common Issues

#### 1. Docker commands fail

**Symptom**: `Cannot connect to the Docker daemon`

**Solution**: 
- Check the built-in s6 service: `s6-svstat /var/run/s6/legacy-services/dockerd`
- Check the local daemon: `docker info`

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

#### 5. hostNetwork service discovery not working

**Symptom**: other pods cannot reach the toolchain through `*.svc.cluster.local`

**Solution**:
- Verify the target port is declared in `ports.extra`
- Check the generated Service exists: `kubectl get svc`
- Confirm the process is actually listening on the declared port inside the toolchain
- If the listener uses a different real port, set `targetPort`

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

1. **Privileged Container**: The main container runs privileged so its built-in Docker daemon works. Restrict namespace and node access accordingly.

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
