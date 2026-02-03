# ASAP Grafana Dashboards

Pre-built dashboards for ASAP Protocol observability. Use with Prometheus scraping the `/asap/metrics` endpoint.

## Dashboards

- **asap-red.json** – RED metrics (Request rate, Error rate, Duration/latency) for ASAP requests.
- **asap-detailed.json** – Topology, state machine transitions, and circuit breaker status.

## Setup

1. Configure a Prometheus datasource in Grafana (scrape ASAP server at `http://<asap-host>:<port>/asap/metrics`).
2. **Provisioning**: Copy the JSON files to Grafana's provisioning path, e.g.:
   - Copy to `<grafana provisioning dir>/dashboards/asap/` and set the provisioning config to load from that directory.
   - Or import manually: Grafana UI → Dashboards → Import → Upload JSON file.
3. Select the Prometheus datasource when prompted.

## Metrics used

- `asap_requests_total` – Total requests (labels: `payload_type`, `status`).
- `asap_requests_error_total` – Failed requests.
- `asap_request_duration_seconds` – Request latency histogram.
- `asap_state_transitions_total` – State machine transitions (labels: `from_status`, `to_status`).
- `asap_circuit_breaker_open` – Circuit open state (if exposed by client metrics).
