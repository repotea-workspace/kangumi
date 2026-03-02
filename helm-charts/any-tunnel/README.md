# Any-Tunnel Helm Chart

Unified proxy service supporting TCP, HTTP, SOCKS, and more with GOST and Nginx in a single deployment.

## Overview

Any-Tunnel is a flexible Helm chart that allows you to deploy GOST and Nginx proxy services in a single Kubernetes deployment. Each proxy can be independently enabled and configured based on your specific use case.

## Features

- 🔀 **Multiple Proxy Backends**: Support for GOST and Nginx
- 🔧 **Flexible Configuration**: Each proxy can be independently enabled and configured
- 📦 **Shared Deployment**: All proxies run in the same pod for efficient resource usage
- 🗂️ **ConfigMap Support**: Easy configuration management with ConfigMaps
- 🌐 **Service & Ingress**: Expose proxies via Kubernetes Service or Ingress
- 📊 **Auto-scaling**: Optional HPA support
- 🔒 **Security**: ServiceAccount, SecurityContext support

## Supported Proxies

| Proxy | Type | Protocols |
|-------|------|-----------|
| **GOST** | Multi-protocol | HTTP/HTTPS/HTTP2/SOCKS4/SOCKS5/Shadowsocks |
| **Nginx** | HTTP/HTTPS | Reverse proxy, load balancer |

## Installation

### Prerequisites

- Kubernetes 1.19+
- Helm 3.0+

### Install Chart

```bash
helm install my-tunnel ./any-tunnel
```

## Configuration Examples

### Example 1: GOST HTTP and SOCKS5 Proxy

```yaml
proxies:
  gost:
    enabled: true
    image:
      repository: gogost/gost
      tag: latest
    args:
      - "-L=:8080"
      - "-L=socks5://:1080"
    ports:
      - name: http
        containerPort: 8080
        protocol: TCP
      - name: socks5
        containerPort: 1080
        protocol: TCP
    servicePorts:
      - name: http
        port: 8080
        targetPort: 8080
        protocol: TCP
      - name: socks5
        port: 1080
        targetPort: 1080
        protocol: TCP
    resources:
      limits:
        cpu: 200m
        memory: 256Mi
```

### Example 2: Nginx Reverse Proxy with ConfigMap

```yaml
proxies:
  nginx:
    enabled: true
    image:
      repository: nginx
      tag: alpine
    ports:
      - name: http
        containerPort: 80
        protocol: TCP
    servicePorts:
      - name: http
        port: 80
        targetPort: 80
        protocol: TCP
    configMap:
      enabled: true
      mountPath: /etc/nginx/conf.d
      data:
        default.conf: |
          server {
            listen 80;
            location / {
              proxy_pass http://backend-service:8080;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
            }
          }
```

### Example 3: Multiple Proxies (GOST + Nginx)

```yaml
globalEnv:
  - name: TZ
    value: "Asia/Shanghai"

proxies:
  gost:
    enabled: true
    image:
      repository: gogost/gost
      tag: latest
    args:
      - "-L=:8080"
    ports:
      - name: http
        containerPort: 8080
        protocol: TCP
    servicePorts:
      - name: http
        port: 8080
        targetPort: 8080

  nginx:
    enabled: true
    image:
      repository: nginx
      tag: alpine
    ports:
      - name: http
        containerPort: 80
        protocol: TCP
    servicePorts:
      - name: http
        port: 80
        targetPort: 80
    configMap:
      enabled: true
      mountPath: /etc/nginx/conf.d
      data:
        default.conf: |
          server {
            listen 80;
            location / {
              proxy_pass http://localhost:8080;
            }
          }
```

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `imagePullSecrets` | Image pull secrets | `[]` |
| `serviceAccount.create` | Create service account | `false` |
| `service.type` | Service type | `ClusterIP` |
| `ingress.enabled` | Enable ingress | `false` |
| `resources` | Resource limits/requests | `{}` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `globalEnv` | Global environment variables for all containers | `[]` |
| `additionalVolumes` | Additional volumes | `[]` |
| `additionalVolumeMounts` | Additional volume mounts | `[]` |

### Per-Proxy Parameters

Each proxy under `proxies.<name>` supports:

| Parameter | Description | Required |
|-----------|-------------|----------|
| `enabled` | Enable this proxy | Yes |
| `image.repository` | Image repository | Yes |
| `image.tag` | Image tag | Yes |
| `image.pullPolicy` | Image pull policy | No |
| `command` | Container command | No |
| `args` | Container args | No |
| `env` | Environment variables | No |
| `ports` | Container ports | No |
| `servicePorts` | Service ports | No |
| `resources` | Resource limits/requests | No |
| `livenessProbe` | Liveness probe config | No |
| `readinessProbe` | Readiness probe config | No |
| `configMap.enabled` | Enable ConfigMap | No |
| `configMap.mountPath` | ConfigMap mount path | No |
| `configMap.data` | ConfigMap data | No |

## GOST Configuration Examples

GOST is a powerful tunnel that supports many protocols. Here are some common configurations:

### HTTP Proxy
```yaml
args:
  - "-L=:8080"
```

### SOCKS5 Proxy
```yaml
args:
  - "-L=socks5://:1080"
```

### HTTP Proxy with Authentication
```yaml
args:
  - "-L=user:pass@:8080"
```

### Proxy Chain (Forward through another proxy)
```yaml
args:
  - "-L=:8080"
  - "-F=http://upstream-proxy:8080"
```

### Multiple Listeners
```yaml
args:
  - "-L=:8080"
  - "-L=socks5://:1080"
  - "-L=ss://AEAD_CHACHA20_POLY1305:password@:8338"
```

For more GOST configurations, see: https://gost.run

## Nginx Configuration Examples

### Basic Reverse Proxy
```yaml
configMap:
  enabled: true
  mountPath: /etc/nginx/conf.d
  data:
    default.conf: |
      server {
        listen 80;
        location / {
          proxy_pass http://backend:8080;
        }
      }
```

### Load Balancing
```yaml
configMap:
  enabled: true
  mountPath: /etc/nginx/conf.d
  data:
    default.conf: |
      upstream backend {
        server backend1:8080;
        server backend2:8080;
        server backend3:8080;
      }
      
      server {
        listen 80;
        location / {
          proxy_pass http://backend;
        }
      }
```

### SSL Termination
```yaml
configMap:
  enabled: true
  mountPath: /etc/nginx/conf.d
  data:
    default.conf: |
      server {
        listen 443 ssl;
        ssl_certificate /etc/nginx/certs/tls.crt;
        ssl_certificate_key /etc/nginx/certs/tls.key;
        
        location / {
          proxy_pass http://backend:8080;
        }
      }
```

## Advanced Usage

### Using with Secrets

```yaml
proxies:
  gost:
    enabled: true
    env:
      - name: PROXY_USER
        valueFrom:
          secretKeyRef:
            name: proxy-secret
            key: username
      - name: PROXY_PASS
        valueFrom:
          secretKeyRef:
            name: proxy-secret
            key: password
```

### Shared Storage Between Proxies

```yaml
additionalVolumes:
  - name: shared-cache
    emptyDir: {}

additionalVolumeMounts:
  - name: shared-cache
    mountPath: /cache

proxies:
  nginx:
    enabled: true
    # ... nginx config with cache at /cache
  
  gost:
    enabled: true
    # ... gost can also access /cache
```

## Troubleshooting

### Check proxy logs
```bash
kubectl logs -f deployment/my-tunnel -c <proxy-name>
# Example: kubectl logs -f deployment/my-tunnel -c gost
```

### Test proxy connection
```bash
# Port forward
kubectl port-forward deployment/my-tunnel 8080:8080

# Test HTTP proxy
curl -x http://localhost:8080 https://www.google.com

# Test SOCKS5 proxy
curl --socks5 localhost:1080 https://www.google.com
```

## Links

- [GOST Documentation](https://gost.run)
- [Nginx Documentation](https://nginx.org/en/docs/)

## License

This Helm chart is provided as-is under the MIT License.


## Installation

### Prerequisites

- Kubernetes 1.19+
- Helm 3.0+

### Install Chart

```bash
helm install my-tunnel ./any-tunnel
```

## Configuration Examples

### Example 1: GOST HTTP and SOCKS5 Proxy

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `imagePullSecrets` | Image pull secrets | `[]` |
| `serviceAccount.create` | Create service account | `false` |
| `service.type` | Service type | `ClusterIP` |
| `ingress.enabled` | Enable ingress | `false` |
| `resources` | Resource limits/requests | `{}` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `globalEnv` | Global environment variables for all containers | `[]` |
| `additionalVolumes` | Additional volumes | `[]` |
| `additionalVolumeMounts` | Additional volume mounts | `[]` |

### Per-Proxy Parameters

Each proxy under `proxies.<name>` supports:

| Parameter | Description | Required |
|-----------|-------------|----------|
| `enabled` | Enable this proxy | Yes |
| `image.repository` | Image repository | Yes |
| `image.tag` | Image tag | Yes |
| `image.pullPolicy` | Image pull policy | No |
| `command` | Container command | No |
| `args` | Container args | No |
| `env` | Environment variables | No |
| `ports` | Container ports | No |
| `servicePorts` | Service ports | No |
| `resources` | Resource limits/requests | No |
| `livenessProbe` | Liveness probe config | No |
| `readinessProbe` | Readiness probe config | No |
| `configMap.enabled` | Enable ConfigMap | No |
| `configMap.mountPath` | ConfigMap mount path | No |
| `configMap.data` | ConfigMap data | No |

## GOST Configuration Examples

GOST is a powerful tunnel that supports many protocols. Here are some common configurations:

### HTTP Proxy
```yaml
args:
  - "-L=:8080"
```

### SOCKS5 Proxy
```yaml
args:
  - "-L=socks5://:1080"
```

### HTTP Proxy with Authentication
```yaml
args:
  - "-L=user:pass@:8080"
```

### Proxy Chain (Forward through another proxy)
```yaml
args:
  - "-L=:8080"
  - "-F=http://upstream-proxy:8080"
```

### Multiple Listeners
```yaml
args:
  - "-L=:8080"
  - "-L=socks5://:1080"
  - "-L=ss://AEAD_CHACHA20_POLY1305:password@:8338"
```

For more GOST configurations, see: https://gost.run

## Advanced Usage

### Using with Secrets

```yaml
proxies:
  gost:
    enabled: true
    env:
      - name: PROXY_USER
        valueFrom:
          secretKeyRef:
            name: proxy-secret
            key: username
      - name: PROXY_PASS
        valueFrom:
          secretKeyRef:
            name: proxy-secret
            key: password
```

### Shared Storage Between Proxies

```yaml
additionalVolumes:
  - name: shared-cache
    emptyDir: {}

additionalVolumeMounts:
  - name: shared-cache
    mountPath: /cache

proxies:
  nginx:
    enabled: true
    # ... nginx config with cache at /cache
  
  squid:
    enabled: true
    # ... squid config with cache at /cache
```

## Troubleshooting

### Check proxy logs
```bash
kubectl logs -f deployment/my-tunnel -c <proxy-name>
# Example: kubectl logs -f deployment/my-tunnel -c gost
```

### Test proxy connection
```bash
# Port forward
kubectl port-forward deployment/my-tunnel 8080:8080

# Test HTTP proxy
curl -x http://localhost:8080 https://www.google.com

# Test SOCKS5 proxy
curl --socks5 localhost:1080 https://www.google.com
```

## Links

- [GOST Documentation](https://gost.run)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Squid Documentation](http://www.squid-cache.org/Doc/)
- [HAProxy Documentation](https://www.haproxy.org/documentation.html)
- [V2Ray Documentation](https://www.v2fly.org)

## License

This Helm chart is provided as-is under the MIT License.
