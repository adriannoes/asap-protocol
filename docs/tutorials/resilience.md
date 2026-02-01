# Building Resilient Agents

**Time:** ~25 minutes | **Level:** Advanced

This tutorial shows how to build agents that handle failures gracefully: retries with backoff, circuit breakers, fallbacks, and state recovery. The patterns align with ASAP's chaos testing (Sprint 8): message loss, server crashes, timeouts, and cascading failures.

**Prerequisites:** [Building Your First Agent](first-agent.md), [Stateful Workflows](stateful-workflows.md), [Multi-Agent Orchestration](multi-agent.md)

---

## Why Resilience Matters

Distributed agent systems face transient and persistent failures:

- **Transient:** Network timeouts, temporary overload, message loss — often fixed by retrying.
- **Persistent:** Down agent, repeated 5xx — retrying blindly can make things worse. Use circuit breakers and fallbacks.

Chaos testing (Sprint 8) validated ASAP's handling of: server crashes, message loss, network partition, and clock skew. This tutorial applies those lessons to your agents.

---

## Pattern 1: Retry with Backoff

### Using ASAPClient's Built-in Retry

`ASAPClient` retries transient failures by default. Configure via `RetryConfig`:

```python
from asap.transport.client import ASAPClient, RetryConfig
from asap.models.envelope import Envelope

config = RetryConfig(
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0,
    jitter=True,  # Add randomness to avoid thundering herd
)

async with ASAPClient("http://agent.example.com", retry_config=config) as client:
    response = await client.send(envelope)
```

- **Exponential backoff:** delay = min(base_delay × 2^attempt, max_delay)
- **Jitter:** Reduces synchronized retries when many clients fail at once

### Standalone Retry for Custom Operations

For non-client operations (e.g. DB, external APIs), use the `error_recovery` pattern:

```python
from asap.examples.error_recovery import retry_with_backoff

def flaky_operation() -> str:
    # May raise ConnectionError, TimeoutError, etc.
    return call_external_service()

result = retry_with_backoff(
    flaky_operation,
    max_retries=3,
    base_delay=0.5,
    max_delay=30.0,
    jitter=True,
)
```

Run the built-in demo: `uv run python -m asap.examples.error_recovery --skip-circuit --skip-fallback`

---

## Pattern 2: Circuit Breaker

The circuit breaker stops requests when a target is failing repeatedly, then tests recovery after a timeout.

### States

| State     | Meaning                                      |
|-----------|----------------------------------------------|
| CLOSED    | Normal; requests allowed                     |
| OPEN      | Too many failures; requests rejected         |
| HALF_OPEN | Testing; one request allowed to probe recovery |

### Using ASAPClient with Circuit Breaker

```python
from asap.transport.client import ASAPClient, RetryConfig
from asap.errors import CircuitOpenError

config = RetryConfig(
    max_retries=3,
    circuit_breaker_enabled=True,
    circuit_breaker_threshold=5,   # Open after 5 consecutive failures
    circuit_breaker_timeout=60.0,  # Try again after 60 seconds
)

async with ASAPClient("http://agent.example.com", retry_config=config) as client:
    try:
        response = await client.send(envelope)
    except CircuitOpenError:
        # Circuit is open; use fallback or return cached/default result
        response = get_fallback_response()
```

### Standalone Circuit Breaker

For custom logic (e.g. wrapping non-ASAP calls):

```python
from asap.errors import CircuitOpenError
from asap.transport.circuit_breaker import CircuitBreaker, CircuitState

breaker = CircuitBreaker(threshold=5, timeout=60.0)

def call_with_breaker():
    if not breaker.can_attempt():
        raise CircuitOpenError("Circuit is open")
    try:
        result = risky_operation()
        breaker.record_success()
        return result
    except Exception as e:
        breaker.record_failure()
        raise
```

Run the circuit breaker demo: `uv run python -m asap.examples.error_recovery --skip-retry --skip-fallback`

---

## Pattern 3: Fallback

When the primary operation fails, use a fallback: cached value, secondary agent, or default.

### Using the Fallback Helper

For sync operations, use `with_fallback`:

```python
from asap.examples.error_recovery import with_fallback

def primary() -> dict:
    # Call primary agent (sync wrapper or in-process logic)
    return call_primary_service()

def fallback() -> dict:
    # Return cached result or default; should not raise
    return {"status": "fallback", "message": "Using cached/default result"}

result = with_fallback(primary, fallback)
```

### Fallback in Multi-Agent Orchestration

```python
async def call_worker_with_fallback(primary_url: str, backup_url: str) -> Envelope:
    try:
        async with ASAPClient(primary_url) as client:
            return await client.send(envelope)
    except (ASAPConnectionError, ASAPTimeoutError) as e:
        logger.warning("Primary worker failed, trying backup", error=str(e))
        async with ASAPClient(backup_url) as client:
            return await client.send(envelope)
```

Run the fallback demo: `uv run python -m asap.examples.error_recovery --skip-retry --skip-circuit`

---

## Pattern 4: State Recovery

Combine resilience with [Stateful Workflows](stateful-workflows.md): persist state at checkpoints and resume after failures.

```python
from asap.state.snapshot import InMemorySnapshotStore
from asap.examples.long_running import run_steps, resume_from_store

store = InMemorySnapshotStore()
task_id = "task_01HX5K4N..."

# Run until failure (e.g. crash, timeout)
try:
    run_steps(store, task_id, num_steps=10, crash_after_step=3)
except Exception:
    pass  # State saved at step 3

# Resume from last checkpoint
final = resume_from_store(store, task_id, num_steps=10)
```

Use a persistent `SnapshotStore` (Redis, PostgreSQL) in production so state survives process restarts.

---

## Combining Patterns

### Retry + Circuit Breaker (ASAPClient)

```python
config = RetryConfig(
    max_retries=3,
    circuit_breaker_enabled=True,
    circuit_breaker_threshold=5,
)
async with ASAPClient(url, retry_config=config) as client:
    response = await client.send(envelope)
```

### Retry + Fallback

```python
def primary_with_retry():
    return retry_with_backoff(lambda: call_primary_agent())

result = with_fallback(primary_with_retry, fallback)
```

### Circuit Breaker + Fallback

```python
try:
    response = await client.send(envelope)
except CircuitOpenError:
    response = fallback_response()
```

---

## Chaos Testing Scenarios (Sprint 8)

ASAP's chaos tests validate these scenarios:

| Scenario            | Client behavior                                  |
|---------------------|--------------------------------------------------|
| Message loss        | Retries until max_retries; raises `ASAPTimeoutError` |
| Server crash        | Retries; raises `ASAPConnectionError`            |
| 503 Service Unavailable | Retries (transient)                          |
| Circuit open        | Immediate `CircuitOpenError`; no retries         |
| Network partition   | Timeout; retries; circuit opens after threshold  |

---

## Best Practices

1. **Retry only idempotent operations** — Task requests are typically idempotent; others may not be.
2. **Use jitter** — Avoid synchronized retries across many clients.
3. **Circuit breaker per target** — One breaker per agent URL, not global.
4. **Fallback should not fail** — Keep fallback logic simple and reliable.
5. **Log failures** — Use structured logging (`get_logger`) for debugging.

---

## Next Steps

- [Production Deployment Checklist](production-checklist.md) — Security, monitoring, scaling
- [Error Handling](../error-handling.md) — ASAP error taxonomy
- [State Management](../state-management.md) — Snapshots and custom stores
