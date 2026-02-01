# Deploy ASAP Agent on Kubernetes

This guide walks through testing and deploying an ASAP Protocol agent on Kubernetes using **minikube** or **kind**, with **Helm**. Target: deploy and verify in **under 10 minutes**.

## Published Docker images

On each release (git tag `v*`), the project builds and pushes a Docker image to GitHub Container Registry:

- **Image**: `ghcr.io/adriannoes/asap-protocol`
- **Tags**: `latest`, `v1.0.0`, `v1.0`, `v1` (for release v1.0.0; other releases get `latest` and semver tags)

To use the published image with Helm (no local build):

```bash
helm install asap-agent ./helm/asap-agent \
  --set image.repository=ghcr.io/adriannoes/asap-protocol \
  --set image.tag=v1.0.0
```

To pull locally: `docker pull ghcr.io/adriannoes/asap-protocol:latest`

## Prerequisites

- **Docker** (for building the image and for kind/minikube)
- **kubectl** ([install](https://kubernetes.io/docs/tasks/tools/))
- **Helm 3** ([install](https://helm.sh/docs/intro/install/))
- **kind** or **minikube** (one is enough):
  - [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation): `brew install kind` or see kind docs
  - [minikube](https://minikube.sigs.k8s.io/docs/start/): `brew install minikube` or see minikube docs

## Option A: kind (recommended for CI and local test)

### 1. Create cluster and build image

```bash
# From repo root
cd /path/to/asap-protocol

# Create kind cluster (usually < 1 min)
kind create cluster --name asap-test

# Build the Docker image
docker build -t asap-protocol:latest .

# Load image into kind (no registry needed)
kind load docker-image asap-protocol:latest --name asap-test
```

### 2. Install with Helm

```bash
# Install the chart (release name = asap-agent)
helm install asap-agent ./helm/asap-agent \
  --set image.repository=asap-protocol \
  --set image.tag=latest \
  --set image.pullPolicy=IfNotPresent
```

### 3. Wait for pod and verify

```bash
# Wait for deployment to be ready (default timeout 120s)
kubectl wait --for=condition=ready pod -l app=asap-agent --timeout=120s

# Port-forward and hit health endpoint
kubectl port-forward svc/asap-agent 8000:8000 &
sleep 2
curl -s http://localhost:8000/health
# Expected: {"status":"ok"}

curl -s http://localhost:8000/ready
# Expected: {"status":"ok"}

# Optional: manifest
curl -s http://localhost:8000/.well-known/asap/manifest.json | head -5

# Stop port-forward
kill %1 2>/dev/null || true
```

### 4. Cleanup

```bash
kind delete cluster --name asap-test
```

---

## Option B: minikube

### 1. Start minikube and build image

```bash
cd /path/to/asap-protocol

# Start minikube (use docker driver; first run may take a few minutes)
minikube start

# Build image inside minikube's Docker daemon so no need to push
eval $(minikube docker-env)
docker build -t asap-protocol:latest .
```

### 2. Install with Helm

```bash
helm install asap-agent ./helm/asap-agent \
  --set image.repository=asap-protocol \
  --set image.tag=latest \
  --set image.pullPolicy=IfNotPresent
```

### 3. Wait and verify

```bash
kubectl wait --for=condition=ready pod -l app=asap-agent --timeout=120s
minikube service asap-agent --url
# Or: kubectl port-forward svc/asap-agent 8000:8000
# Then: curl http://localhost:8000/health
```

### 4. Cleanup

```bash
helm uninstall asap-agent
minikube stop
```

---

## Validating the chart without a cluster

To only check that the Helm chart renders valid manifests (no Docker/Kubernetes needed):

```bash
# From repo root
helm template asap-agent ./helm/asap-agent
```

Exit code 0 means the chart is valid. You can also run the script:

```bash
./scripts/test_k8s_deploy.sh
```

That script runs `helm template` and, if `kind` and `helm` are available, optionally runs a full deploy test (create cluster, build image, load, install, verify /health, delete cluster) and reports elapsed time (target &lt; 10 minutes).

---

## Summary

| Step              | kind                    | minikube                 |
|-------------------|-------------------------|--------------------------|
| Create/start      | `kind create cluster`    | `minikube start`         |
| Build image       | `docker build`          | `eval $(minikube docker-env)` then `docker build` |
| Load image        | `kind load docker-image`| (built in minikube)      |
| Install           | `helm install ...`      | `helm install ...`       |
| Verify            | `kubectl wait` + `curl /health` | same                    |
| Cleanup            | `kind delete cluster`   | `helm uninstall` + `minikube stop` |

Target: from zero to a working agent responding on `/health` and `/ready` in **under 10 minutes**.
