# ASAP Agent Helm Chart

Helm chart for deploying ASAP Protocol agents to Kubernetes.

## Prerequisites

- Kubernetes cluster
- Helm 3.x
- Docker image: build locally (`docker build -t asap-protocol:latest .`) or use the [published image](https://github.com/adriannoes/asap-protocol/pkgs/container/asap-protocol) `ghcr.io/adriannoes/asap-protocol` (tags: `latest`, `v1.0.0`, `v1.0`, `v1` on release)

## Install

```bash
# Install with release name 'asap-agent' and default values
helm install asap-agent ./helm/asap-agent

# Install with custom image
helm install asap-agent ./helm/asap-agent \
  --set image.repository=ghcr.io/adriannoes/asap-protocol \
  --set image.tag=v1.0.0

# Install with custom values file
helm install asap-agent ./helm/asap-agent -f my-values.yaml
```

## Upgrade

```bash
helm upgrade asap-agent ./helm/asap-agent -f my-values.yaml
```

## Uninstall

```bash
helm uninstall asap-agent
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `asap-protocol` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `config.host` | ASAP bind host | `0.0.0.0` |
| `config.port` | ASAP bind port | `8000` |
| `config.workers` | Uvicorn workers | `1` |
| `config.debug` | ASAP_DEBUG | `false` |
| `config.rateLimit` | ASAP_RATE_LIMIT | `10/second;100/minute` |
| `config.maxRequestSize` | Max request size (bytes) | `10485760` |
| `probes.liveness.path` | Liveness probe path | `/.well-known/asap/manifest.json` |
| `probes.readiness.path` | Readiness probe path | `/.well-known/asap/manifest.json` |
| `resources.requests` | Resource requests | `128Mi`, `100m` |
| `resources.limits` | Resource limits | `512Mi`, `500m` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |
| `ingress.enabled` | Enable Ingress | `false` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts` | Ingress hosts | `asap-agent.local` |

Probe paths: `probes.liveness.path` (default `/health`), `probes.readiness.path` (default `/ready`).

## Port-forward (local test)

```bash
kubectl port-forward svc/asap-agent 8000:8000
curl http://localhost:8000/.well-known/asap/manifest.json
```
