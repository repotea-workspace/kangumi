# any-cors Helm Chart

This Helm Chart deploys corsanywhere application, providing CORS proxy service.

## Configuration Options

### corsanywhere Configuration

Configure application parameters through the `corsanywhere` section in `values.yaml`:

```yaml
corsanywhere:
  # Port for the server to listen on (default: 8080)
  port: 8080
  
  # Require Origin header on requests (default: true)
  requireOrigin: true
  
  # Auto follow 307/308 redirects (default: false)
  enableRedirect: false
  
  # Maximum number of redirects to follow (default: 3)
  maxRedirects: 3
  
  # Timeout (seconds) for HTTP client and transport (default: 30)
  timeout: 30
```

## Usage Examples

### 1. Deploy with Default Configuration

```bash
helm install my-cors ./any-cors
```

### 2. Deploy with Custom Configuration

Create a custom values file:

```yaml
# custom-values.yaml
# Override corsanywhere configuration
corsanywhere:
  # Change the port from default 8080
  port: 3333
  # Disable origin requirement
  requireOrigin: false
  # Enable redirect following
  enableRedirect: true
  # Increase max redirects
  maxRedirects: 5
  # Increase timeout
  timeout: 60

# Update service port to match container port
service:
  type: ClusterIP
  port: 3333

# Optional: Add ingress if needed
ingress:
  enabled: true
  className: "nginx"
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
  hosts:
    - host: cors.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []

# Optional: Set resource limits
resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

Then deploy:

```bash
helm install my-cors ./any-cors -f custom-values.yaml
```

### 3. Override Individual Parameters via Command Line

```bash
helm install my-cors ./any-cors \
  --set corsanywhere.port=3333 \
  --set corsanywhere.requireOrigin=false \
  --set service.port=3333
```

## Command Line Arguments Mapping

These values.yaml configuration options are converted to corsanywhere startup arguments:

- `corsanywhere.port` → `-port=<value>`
- `corsanywhere.requireOrigin` → `-require-origin=<value>`
- `corsanywhere.enableRedirect` → `-enable-redirect=<value>`
- `corsanywhere.maxRedirects` → `-max-redirects=<value>`
- `corsanywhere.timeout` → `-timeout=<value>`

## Important Notes

- When modifying `corsanywhere.port`, remember to also update `service.port` to ensure proper service access
- If ingress is enabled, ensure ingress configuration points to the correct service port
- Health check probes will automatically use the configured port

## Upgrading

When upgrading from previous versions, make sure to check:

1. Port configuration adjustments needed
2. Service type and port match
3. Ingress configuration updates if applicable

## Troubleshooting

If you encounter issues, check:

1. Pod logs: `kubectl logs deployment/<release-name>-any-cors`
2. Service configuration: `kubectl get svc <release-name>-any-cors -o yaml`
3. Port consistency: container port, service port, and ingress configuration

## Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `corsanywhere.port` | Port for the server to listen on | `8080` |
| `corsanywhere.requireOrigin` | Require Origin header on requests | `true` |
| `corsanywhere.enableRedirect` | Auto follow 307/308 redirects | `false` |
| `corsanywhere.maxRedirects` | Maximum number of redirects to follow | `3` |
| `corsanywhere.timeout` | Timeout (seconds) for HTTP client and transport | `30` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `8080` |
| `ingress.enabled` | Enable ingress | `false` |
| `resources` | Resource limits and requests | `{}` |
