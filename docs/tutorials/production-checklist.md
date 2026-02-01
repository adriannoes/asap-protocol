# Production Deployment Checklist

**Time:** ~15 minutes | **Level:** DevOps

Use this checklist before deploying ASAP agents to production. Covers security, monitoring, and scaling.

**Prerequisites:** [Building Your First Agent](first-agent.md), [Building Resilient Agents](resilience.md)

---

## Security

### TLS and HTTPS

- [ ] Use HTTPS for all production endpoints (no HTTP)
- [ ] Configure valid SSL certificates (not self-signed)
- [ ] Enable TLS 1.2+ (1.3 recommended)
- [ ] Set HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- [ ] Redirect HTTP to HTTPS at reverse proxy (nginx, traefik, etc.)

### Authentication

- [ ] Enable authentication in manifest (`auth=AuthScheme(schemes=["bearer"])` or `["basic"]`)
- [ ] Implement and wire `token_validator` to `create_app()`
- [ ] Store tokens in environment variables (never hardcode)
- [ ] Rotate tokens regularly; use short-lived tokens (15–60 min)
- [ ] Ensure clients send `Authorization` header (Bearer or Basic)

### Rate Limiting

- [ ] Configure rate limits via `ASAP_RATE_LIMIT` or `rate_limit` in `create_app()`
- [ ] Tune limits for your workload (e.g. `10/second;100/minute`)
- [ ] For multi-instance deployments, use Redis-backed rate limiting (slowapi)
- [ ] Monitor `asap_rate_limit_exceeded_total` (or equivalent) for abuse

### Request Size Limits

- [ ] Set `max_request_size` or `ASAP_MAX_REQUEST_SIZE` (default 10MB)
- [ ] Align with reverse proxy (`client_max_body_size`) and ASGI server limits
- [ ] Monitor 413 (Payload Too Large) responses

### Handler Security

- [ ] Validate all payloads with Pydantic models (e.g. `TaskRequest`)
- [ ] Use `FilePart` (or equivalent) for file URIs; block path traversal (`../`)
- [ ] Use `sanitize_for_logging()` before logging envelope/payload
- [ ] Never log secrets or PII
- [ ] Use `validate_handler()` or equivalent before registering handlers

### Replay Protection

- [ ] Keep timestamp validation enabled (default)
- [ ] Consider `require_nonce=True` for high-security flows
- [ ] Use a shared nonce store (Redis, DB) for multi-instance deployments

---

## Monitoring

### Metrics

- [ ] Expose metrics at `/asap/metrics` (Prometheus format)
- [ ] Configure Prometheus to scrape `/asap/metrics`
- [ ] Track: `asap_requests_total`, `asap_requests_error_total`, `asap_request_duration_seconds`
- [ ] Add custom metrics for business logic (e.g. tasks per skill)

### Logging

- [ ] Use structured logging (`configure_logging`, `get_logger`)
- [ ] Set `ASAP_LOG_FORMAT=json` for production
- [ ] Bind `trace_id` and `correlation_id` for distributed tracing
- [ ] Ensure logs are aggregated (e.g. ELK, Loki, CloudWatch)

### Health and Readiness

- [ ] Implement `/health` (liveness) and `/ready` (readiness) endpoints
- [ ] Wire readiness to dependencies (DB, Redis, downstream agents)
- [ ] Configure Kubernetes liveness/readiness probes
- [ ] Test graceful shutdown (SIGTERM) and drain in-flight requests

### Alerting

- [ ] Alert on high error rate (e.g. >10% for 5 min)
- [ ] Alert on high latency (e.g. P99 > 1s)
- [ ] Alert on agent down (scrape failures)
- [ ] Alert on rate limit hits above threshold

---

## Scaling

### Client Configuration

- [ ] Use connection pooling (ASAPClient default; tune `pool_connections`, `pool_maxsize` if needed)
- [ ] Enable compression for payloads > 1KB (default in ASAPClient)
- [ ] Configure `RetryConfig` (retries, circuit breaker) for resilience
- [ ] Set appropriate timeouts (`timeout`, `MANIFEST_REQUEST_TIMEOUT`)

### Server Configuration

- [ ] Use multiple uvicorn workers or Gunicorn with Uvicorn workers
- [ ] Configure worker count based on CPU (e.g. 2–4 per core)
- [ ] Set `DEFAULT_POOL_MAXSIZE` and `DEFAULT_POOL_CONNECTIONS` for high concurrency

### Caching

- [ ] Enable manifest caching (`ManifestCache`) for downstream agent manifests
- [ ] Tune cache TTL (e.g. 5 min) for your discovery pattern
- [ ] Use shared cache (Redis) for multi-instance deployments if needed

### State and Snapshots

- [ ] Use a persistent `SnapshotStore` (Redis, PostgreSQL) for long-running tasks
- [ ] Avoid `InMemorySnapshotStore` in production (data lost on restart)
- [ ] Tune checkpoint frequency; keep snapshots lean

### Horizontal Scaling

- [ ] Run agents as stateless pods/containers where possible
- [ ] Use sticky sessions or shared state (Redis) if required
- [ ] Configure autoscaling (HPA, cluster autoscaler) based on CPU/memory/request rate

---

## Resilience

- [ ] Enable retries with backoff on the client
- [ ] Enable circuit breaker for failing downstream agents
- [ ] Implement fallbacks for critical paths (cached value, backup agent)
- [ ] Use state snapshots for resumable long-running tasks

---

## Quick Reference

| Area       | Key docs                                |
|-----------|------------------------------------------|
| Security  | [Security Guide](../security.md)         |
| Metrics   | [Metrics Guide](../metrics.md)           |
| Transport | [Transport Guide](../transport.md)       |
| Resilience| [Building Resilient Agents](resilience.md)|
