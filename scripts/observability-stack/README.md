# Observability stack (Prometheus + Grafana)

Optional local stack to test ASAP Grafana dashboards.

## Prerequisites

- Docker and Docker Compose
- ASAP server running and exposing `/asap/metrics` (e.g. on port 8000)

## Run

From the repository root:

```bash
docker compose -f scripts/observability-stack/docker-compose.yml up -d
```

- **Prometheus**: http://localhost:9090 (scrapes `host.docker.internal:8000/asap/metrics` on Mac/Windows; on Linux you may need to set `extra_hosts: ["host.docker.internal:host-gateway"]` or change the target in `prometheus.yml` to your host IP).
- **Grafana**: http://localhost:3000 (login: `admin` / `admin`).

Dashboards are auto-provisioned under the **ASAP** folder. If no data appears, ensure the ASAP server is running and reachable from the host at port 8000 (or update `prometheus.yml` with the correct target).

## Stop

```bash
docker compose -f scripts/observability-stack/docker-compose.yml down
```
