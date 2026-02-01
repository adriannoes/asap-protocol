#!/usr/bin/env bash
# Test Kubernetes deployment for ASAP Protocol agent.
#
# 1. Always: validate Helm chart with `helm template`.
# 2. Optional (if kind, docker, helm available): create kind cluster, build image,
#    load image, helm install, wait for pod, curl /health, report time, delete cluster.
# Target: full deploy test in < 10 minutes.
#
# Usage: from repo root, run:
#   ./scripts/test_k8s_deploy.sh
#   ./scripts/test_k8s_deploy.sh --full   # run full kind test if tools available

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

CHART_DIR="${REPO_ROOT}/helm/asap-agent"
RELEASE_NAME="asap-agent"
IMAGE_NAME="asap-protocol:latest"
KIND_CLUSTER="${KIND_CLUSTER:-asap-test}"
TARGET_SECONDS=600  # 10 minutes

echo "==> Validating Helm chart (helm template)"
if ! command -v helm &>/dev/null; then
  echo "helm not found; install Helm 3 to validate the chart."
  exit 1
fi
helm template "$RELEASE_NAME" "$CHART_DIR" --set image.repository=asap-protocol --set image.tag=latest >/dev/null
echo "    Chart renders OK."

FULL="${1:-}"
if [[ "$FULL" != "--full" ]]; then
  echo "    Skipping full cluster test (use --full to run kind test)."
  exit 0
fi

if ! command -v kind &>/dev/null || ! command -v docker &>/dev/null; then
  echo "    kind or docker not found; skipping full cluster test."
  exit 0
fi

echo "==> Full deploy test with kind (target: < ${TARGET_SECONDS}s)"
START=$(date +%s)

echo "    Creating kind cluster..."
kind create cluster --name "$KIND_CLUSTER" --wait 2m

echo "    Building Docker image..."
docker build -t "$IMAGE_NAME" .

echo "    Loading image into kind..."
kind load docker-image "$IMAGE_NAME" --name "$KIND_CLUSTER"

echo "    Installing with Helm..."
helm install "$RELEASE_NAME" "$CHART_DIR" \
  --set image.repository=asap-protocol \
  --set image.tag=latest \
  --set image.pullPolicy=IfNotPresent \
  --wait --timeout 2m

echo "    Waiting for pod ready..."
kubectl wait --for=condition=ready pod -l app=asap-agent --timeout=120s

echo "    Verifying /health (port-forward + curl)..."
kubectl port-forward "svc/${RELEASE_NAME}" 18000:8000 &
PF_PID=$!
trap "kill $PF_PID 2>/dev/null || true" EXIT
sleep 2
curl -sf http://localhost:18000/health | grep -q '"status":"ok"' || exit 1
kill $PF_PID 2>/dev/null || true
trap - EXIT

ELAPSED=$(($(date +%s) - START))
echo "    Deploy and verify completed in ${ELAPSED}s (target: < ${TARGET_SECONDS}s)."

echo "    Cleaning up kind cluster..."
kind delete cluster --name "$KIND_CLUSTER"

if [[ $ELAPSED -lt $TARGET_SECONDS ]]; then
  echo "==> PASS: Deploy test finished in < 10 minutes."
else
  echo "==> WARN: Deploy test took ${ELAPSED}s (over 10 min)."
fi
exit 0
