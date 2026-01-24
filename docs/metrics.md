# Metrics Guide

> Prometheus-compatible metrics for monitoring ASAP protocol agents.

---

## Overview

ASAP provides built-in metrics collection for observability and monitoring. Metrics are exposed in Prometheus text format via the `/asap/metrics` endpoint.

### Features

- **Request Counts**: Track total, successful, and failed requests
- **Latency Histograms**: Measure request processing duration
- **Error Classification**: Categorize errors by type
- **Process Uptime**: Monitor agent availability

---

## Metrics Endpoint

### GET `/asap/metrics`

Returns all collected metrics in Prometheus text format.

#### Request

```bash
curl http://localhost:8000/asap/metrics
```

#### Response

```text
# HELP asap_requests_total Total number of ASAP requests received
# TYPE asap_requests_total counter
asap_requests_total{payload_type="task.request",status="success"} 42
asap_requests_total{payload_type="task.request",status="error"} 3

# HELP asap_requests_success_total Total number of successful ASAP requests
# TYPE asap_requests_success_total counter
asap_requests_success_total{payload_type="task.request"} 42

# HELP asap_requests_error_total Total number of failed ASAP requests
# TYPE asap_requests_error_total counter
asap_requests_error_total{payload_type="task.request",error_type="handler_not_found"} 2
asap_requests_error_total{payload_type="task.request",error_type="invalid_envelope"} 1

# HELP asap_request_duration_seconds Request processing duration in seconds
# TYPE asap_request_duration_seconds histogram
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="0.005"} 10
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="0.01"} 25
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="0.025"} 38
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="0.05"} 40
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="0.1"} 41
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="0.25"} 42
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="0.5"} 42
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="1.0"} 42
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="2.5"} 42
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="5.0"} 42
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="10.0"} 42
asap_request_duration_seconds_bucket{payload_type="task.request",status="success",le="+Inf"} 42
asap_request_duration_seconds_sum{payload_type="task.request",status="success"} 1.234
asap_request_duration_seconds_count{payload_type="task.request",status="success"} 42

# HELP asap_process_uptime_seconds Time since server start
# TYPE asap_process_uptime_seconds gauge
asap_process_uptime_seconds 3600.123
```

---

## Available Metrics

### Counters

| Metric | Labels | Description |
|--------|--------|-------------|
| `asap_requests_total` | `payload_type`, `status` | Total requests received |
| `asap_requests_success_total` | `payload_type` | Successful requests |
| `asap_requests_error_total` | `payload_type`, `error_type` | Failed requests |

### Histograms

| Metric | Labels | Buckets | Description |
|--------|--------|---------|-------------|
| `asap_request_duration_seconds` | `payload_type`, `status` | 5ms to 10s | Processing duration |

### Gauges

| Metric | Description |
|--------|-------------|
| `asap_process_uptime_seconds` | Time since server start |

---

## Labels

### `payload_type`

The ASAP payload type being processed:

- `task.request` - Task request
- `task.response` - Task response
- `mcp.tool_call` - MCP tool invocation
- `unknown` - Unrecognized or malformed payload

### `status`

Request outcome:

- `success` - Request processed successfully
- `error` - Request failed

### `error_type`

Error classification (only on error metrics):

- `invalid_envelope` - Malformed envelope structure
- `handler_not_found` - No handler for payload type
- `internal_error` - Unhandled exception

---

## Using the Metrics API

### Programmatic Access

```python
from asap.observability import get_metrics

# Get the global metrics collector
metrics = get_metrics()

# Increment a counter
metrics.increment_counter(
    "asap_requests_total",
    {"payload_type": "task.request", "status": "success"}
)

# Record a histogram observation
metrics.observe_histogram(
    "asap_request_duration_seconds",
    0.125,  # 125ms
    {"payload_type": "task.request", "status": "success"}
)

# Export Prometheus format
prometheus_output = metrics.export_prometheus()
print(prometheus_output)
```

### Custom Metrics

Register custom metrics for your agent:

```python
from asap.observability import get_metrics

metrics = get_metrics()

# Register a custom counter
metrics.register_counter(
    "myagent_tasks_processed_total",
    "Total tasks processed by my agent"
)

# Register a custom histogram
metrics.register_histogram(
    "myagent_skill_duration_seconds",
    "Time spent executing skills",
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0)
)

# Use custom metrics
metrics.increment_counter(
    "myagent_tasks_processed_total",
    {"skill": "research"}
)
metrics.observe_histogram(
    "myagent_skill_duration_seconds",
    2.5,
    {"skill": "research"}
)
```

---

## Prometheus Integration

### Scrape Configuration

Add the ASAP agent to your Prometheus configuration:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'asap-agents'
    scrape_interval: 15s
    static_configs:
      - targets:
          - 'agent1.example.com:8000'
          - 'agent2.example.com:8000'
    metrics_path: '/asap/metrics'
```

### Service Discovery

For Kubernetes deployments:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'asap-agents'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: asap-agent
        action: keep
      - source_labels: [__meta_kubernetes_pod_container_port_number]
        regex: "8000"
        action: keep
    metrics_path: '/asap/metrics'
```

---

## Grafana Dashboard

### Example Queries

#### Request Rate

```promql
rate(asap_requests_total[5m])
```

#### Success Rate

```promql
sum(rate(asap_requests_success_total[5m])) 
/ 
sum(rate(asap_requests_total[5m]))
```

#### Error Rate by Type

```promql
sum by (error_type) (rate(asap_requests_error_total[5m]))
```

#### P50 Latency

```promql
histogram_quantile(0.5, 
  sum by (le) (rate(asap_request_duration_seconds_bucket[5m]))
)
```

#### P99 Latency

```promql
histogram_quantile(0.99, 
  sum by (le) (rate(asap_request_duration_seconds_bucket[5m]))
)
```

#### Request Duration by Payload Type

```promql
histogram_quantile(0.95, 
  sum by (payload_type, le) (rate(asap_request_duration_seconds_bucket[5m]))
)
```

### Dashboard JSON

A sample Grafana dashboard configuration:

```json
{
  "title": "ASAP Agent Metrics",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "sum(rate(asap_requests_total[5m])) by (status)",
          "legendFormat": "{{status}}"
        }
      ]
    },
    {
      "title": "Latency (P50/P95/P99)",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.5, sum(rate(asap_request_duration_seconds_bucket[5m])) by (le))",
          "legendFormat": "P50"
        },
        {
          "expr": "histogram_quantile(0.95, sum(rate(asap_request_duration_seconds_bucket[5m])) by (le))",
          "legendFormat": "P95"
        },
        {
          "expr": "histogram_quantile(0.99, sum(rate(asap_request_duration_seconds_bucket[5m])) by (le))",
          "legendFormat": "P99"
        }
      ]
    },
    {
      "title": "Errors by Type",
      "type": "piechart",
      "targets": [
        {
          "expr": "sum by (error_type) (increase(asap_requests_error_total[1h]))",
          "legendFormat": "{{error_type}}"
        }
      ]
    }
  ]
}
```

---

## Alerting Rules

Sample Prometheus alerting rules:

```yaml
# alerts.yml
groups:
  - name: asap-agent-alerts
    rules:
      - alert: ASAPHighErrorRate
        expr: |
          sum(rate(asap_requests_error_total[5m])) 
          / 
          sum(rate(asap_requests_total[5m])) 
          > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on ASAP agent"
          description: "Error rate is above 10% for 5 minutes"

      - alert: ASAPHighLatency
        expr: |
          histogram_quantile(0.99, 
            sum(rate(asap_request_duration_seconds_bucket[5m])) by (le)
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency on ASAP agent"
          description: "P99 latency is above 1 second"

      - alert: ASAPAgentDown
        expr: up{job="asap-agents"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ASAP agent is down"
          description: "Agent {{ $labels.instance }} is not responding"
```

---

## Best Practices

### 1. Use Meaningful Labels

Keep labels low-cardinality to avoid metric explosion:

```python
# Good: Fixed set of values
metrics.increment_counter("asap_requests_total", {"status": "success"})

# Avoid: High-cardinality labels
metrics.increment_counter("asap_requests_total", {"request_id": unique_id})
```

### 2. Set Appropriate Scrape Intervals

- **15s**: Standard for most use cases
- **5s**: High-resolution monitoring
- **60s**: Cost-sensitive environments

### 3. Monitor Key SLIs

Focus on the four golden signals:

1. **Latency**: `asap_request_duration_seconds`
2. **Traffic**: `rate(asap_requests_total[5m])`
3. **Errors**: `asap_requests_error_total`
4. **Saturation**: Custom metrics for queue depth, etc.

### 4. Retention Policies

Configure appropriate retention for your metrics:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

storage:
  tsdb:
    retention.time: 15d
    retention.size: 10GB
```

---

## Related Documentation

- [Observability](observability.md) - Logging and tracing
- [Transport](transport.md) - HTTP endpoint details
- [API Reference](api-reference.md) - Complete API documentation
