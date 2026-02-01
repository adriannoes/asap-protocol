# ASAP Protocol - Kubernetes Manifests

Plain Kubernetes manifests for deploying ASAP agents (no Helm).

## Prerequisites

- `kubectl` configured for your cluster
- Docker image: build locally (`docker build -t asap-protocol:latest .`) or use the published image `ghcr.io/adriannoes/asap-protocol` (tags: `latest`, `v1.0.0`, `v1.0`, `v1` on release)

## Deploy

```bash
# 1. Deployment (pods)
kubectl apply -f k8s/deployment.yaml

# 2. Service (ClusterIP)
kubectl apply -f k8s/service.yaml

# 3. Ingress (optional; requires Ingress controller)
kubectl apply -f k8s/ingress.yaml
```

## Health probes

- **Liveness**: `GET /health`
- **Readiness**: `GET /ready`

## Customization

- **Image**: Edit `deployment.yaml` and set `spec.template.spec.containers[0].image` to your image (e.g. `ghcr.io/org/asap-protocol:v1.0.0`).
- **Replicas**: Change `spec.replicas` in `deployment.yaml`.
- **Resources**: Adjust `resources.requests` and `resources.limits` in `deployment.yaml`.
- **Ingress**: Set `spec.ingressClassName` and `spec.rules[0].host` in `ingress.yaml` for your cluster.

## Port-forward (local test)

```bash
kubectl port-forward svc/asap-agent 8000:8000
# Then: curl http://localhost:8000/.well-known/asap/manifest.json
```
