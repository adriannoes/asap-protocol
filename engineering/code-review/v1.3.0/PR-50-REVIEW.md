# PR #50 Review — `feat: v1.3.0 — SLA Framework, Observability Metering, Delegation Tokens`

**Date:** 2026-02-18 | **Reviewer:** Antigravity | **Verdict:** 🟡 Approve with Required Fixes

---

## Executive Summary

PR #50 delivers the v1.3.0 milestone: SLA Framework (E3), Observability Metering (E1), and Delegation Tokens (E2). The implementation is well-structured with clean model definitions, good separation of concerns between `sla.py`, `sla_storage.py`, and `sla_api.py`, and a solid showcase script.

**Key concerns:** A 778KB build artifact is committed, a concurrency bottleneck exists in breach broadcasting, and type safety issues in percentage-string fields create fragile parsing that silently skips breach checks.

| Category | Critical | Warning | Nit |
|---|---|---|---|
| Pre-flight (Sync I/O, Standards) | 1 | 1 | 0 |
| Concurrency & Reliability | 0 | 2 | 0 |
| Security & Identity | 0 | 1 | 0 |
| Test & Quality | 0 | 0 | 1 |
| Tech-Specific (Pydantic/FastAPI) | 0 | 1 | 0 |

---

## RF-1 🔴 CRITICAL — `coverage_report.json` committed to repository

**File:** `coverage_report.json` (root)

A **778KB** ephemeral coverage report is committed. `.gitignore` has `coverage.json` but not `coverage_report.json`, so git tracks it.

**Why it matters:** Bloats repo history permanently. Coverage artifacts belong in CI, not in source control.

### Action
1. Remove the file from the branch:
   ```bash
   git rm coverage_report.json
   ```
2. Add the filename to `.gitignore` (right after the existing `coverage.json` line):
   ```diff
    coverage.json
   +coverage_report.json
   ```
3. Commit both changes together.

---

## RF-2 🟡 INFO — SLA API uses REST endpoints (consistent with existing operator APIs)

**File:** `src/asap/transport/sla_api.py`

The SLA API introduces three REST GET endpoints (`GET /sla`, `/sla/history`, `/sla/breaches`). While `tech-stack-decisions.md` says *"All agent-to-agent transport is JSON-RPC 2.0"*, this is the established pattern for **operator-facing APIs** throughout the codebase:

| API | Transport | Auth | Purpose |
|---|---|---|---|
| `POST /asap` | JSON-RPC 2.0 | OAuth2/Bearer | **Agent-to-agent** messaging |
| `WS /asap/ws` | JSON-RPC 2.0 | — | **Agent-to-agent** real-time |
| `GET /health`, `/ready` | REST | None | Kubernetes probes |
| `GET /.well-known/asap/manifest.json` | REST | None | Agent discovery (RFC 8615) |
| `GET /asap/metrics` | REST | None | Prometheus scraping |
| `GET /usage/*` (7 endpoints) | REST | None¹ | Operator metering dashboard |
| `POST/DELETE/GET /asap/delegations` | REST | OAuth2 | Operator delegation mgmt |
| **`GET /sla/*` (3 endpoints)** | **REST** | **None¹** | **Operator SLA dashboard** |

¹ Docstring warns: *"Intended for local/operator use only."*

**Conclusion:** The SLA API follows the exact same pattern as `/usage/*` and `/health`. JSON-RPC is reserved for `asap.send` and `asap.ack` message exchange. **No change needed.** However, `tech-stack-decisions.md` should be clarified to distinguish agent-to-agent (JSON-RPC) from operator APIs (REST).

### Action
Add a clarifying note to `tech-stack-decisions.md` (in the JSON-RPC 2.0 section):
```markdown
> **Note:** JSON-RPC 2.0 applies to agent-to-agent transport (`POST /asap`, `WS /asap/ws`).
> Operator-facing APIs (health, metrics, usage, SLA, delegations) use standard REST
> for compatibility with dashboards, Prometheus, and Kubernetes probes.
```

---

## RF-3 🟡 WARNING — `broadcast_sla_breach` sends notifications sequentially

**File:** `src/asap/transport/websocket.py` — `broadcast_sla_breach` (line ~830)

```python
for ws in list(subscribers):
    try:
        await ws.send_text(text)
    except (RuntimeError, OSError) as e:
        logger.debug("asap.websocket.sla_breach_send_error", error=str(e))
        subscribers.discard(ws)
```

Each subscriber is awaited **sequentially**. If one connection has a full TCP send buffer, it blocks all subsequent notifications. With N subscribers and one slow connection, worst case is O(N × timeout).

**Why it matters:** SLA breach notifications are time-sensitive — a slow subscriber shouldn't delay alerts to healthy ones.

**Precedent:** This same pattern exists in the WebSocket heartbeat loop (`_heartbeat_loop`), but heartbeats only target a single connection. Broadcasts fan out to N connections, making the bottleneck multiplicative.

### Action
Replace the sequential loop with `asyncio.gather`. In `src/asap/transport/websocket.py`:

```python
async def broadcast_sla_breach(
    breach: "SLABreach",
    subscribers: set[WebSocket],
) -> None:
    payload = {
        "jsonrpc": "2.0",
        "method": SLA_BREACH_NOTIFICATION_METHOD,
        "params": {"breach": breach.model_dump(mode="json")},
    }
    text = json.dumps(payload, default=str)

    async def _safe_send(ws: WebSocket) -> None:
        try:
            await ws.send_text(text)
        except (RuntimeError, OSError) as e:
            logger.debug("asap.websocket.sla_breach_send_error", error=str(e))
            subscribers.discard(ws)

    await asyncio.gather(*(_safe_send(ws) for ws in list(subscribers)))
```

---

## RF-4 🟡 WARNING — `SLADefinition` percentage fields accept invalid strings silently

**File:** `src/asap/models/entities.py` — `SLADefinition`
**File:** `src/asap/economics/sla.py` — `evaluate_breach_conditions`

```python
# entities.py
availability: str | None = Field(default=None, description='Target uptime as percentage (e.g., "99.5%")')
max_error_rate: str | None = Field(default=None, description='Maximum error rate as percentage (e.g., "1%")')
```

These accept arbitrary strings like `"ninety-nine"` or `"0.995"`. Their values are parsed at breach-evaluation time by `parse_percentage()`, which raises `ValueError` on bad input. The `evaluate_breach_conditions` function wraps each check in `try/except ValueError: pass` — so **an invalid string silently disables the breach check** instead of flagging the error.

**Why it matters:** An operator configuring `availability: "99.5"` (missing `%` suffix) would have *zero breach detection* for availability without any error or warning. This is a silent failure mode.

### Action
Add a Pydantic `field_validator` to `SLADefinition` in `src/asap/models/entities.py`. This catches bad data at model construction (manifest load time) rather than silently skipping at evaluation:

```python
from pydantic import field_validator
from asap.economics.sla import parse_percentage  # or inline the regex

class SLADefinition(ASAPBaseModel):
    # ... existing fields ...

    @field_validator("availability", "max_error_rate", mode="before")
    @classmethod
    def _validate_percentage_format(cls, v: str | None) -> str | None:
        if v is not None:
            parse_percentage(v)  # raises ValueError if format is invalid
        return v
```

> **Note:** This creates a dependency from `models.entities` → `economics.sla`. If that's undesirable, extract the regex from `parse_percentage` into a shared constant in `models/` and use it directly.

---

## RF-5 🟡 WARNING — SLA history pagination fetches all rows then slices in Python

**File:** `src/asap/transport/sla_api.py` — `get_sla_history` (line ~137)

```python
metrics = await storage.query_metrics(agent_id=agent_id, start=start, end=end)
total = len(metrics)
paginated = metrics[offset : offset + (limit or 100)]
```

The endpoint fetches **all** matching metrics into memory, then applies `offset`/`limit` via Python list slicing. With large time windows or many agents, this is O(n) memory.

**Why it matters:** The `limit` parameter caps at 1000, but the underlying query returns unbounded rows. The same pattern exists in `usage_api.py` (`get_usage`), so this is a codebase-wide concern, not specific to SLA.

### Action
For v1.3.0 this is acceptable given the current scale. Create a follow-up task for v1.4.0:

1. Add `limit` and `offset` parameters to the `SLAStorage.query_metrics()` protocol method.
2. Implement `LIMIT`/`OFFSET` in `SQLiteSLAStorage.query_metrics()`:
   ```python
   query += " LIMIT ? OFFSET ?"
   params.extend([limit, offset])
   ```
3. Apply the same fix to `MeteringStorage.query()` in `usage_api.py` for consistency.

---

## RF-6 🟡 WARNING — `get_sla` performs O(n²) agent deduplication

**File:** `src/asap/transport/sla_api.py` — `get_sla` (line ~76)

```python
for m in metrics_list:
    if m.agent_id in agents_seen:
        continue
    agents_seen.add(m.agent_id)
    agent_metrics = [x for x in metrics_list if x.agent_id == m.agent_id]  # ← re-scans full list
```

For each unique agent, the entire `metrics_list` is re-scanned. With K agents and N total metrics, this is O(K × N).

### Action
Replace with a `defaultdict` grouping in `src/asap/transport/sla_api.py`:

```python
from collections import defaultdict

by_agent: defaultdict[str, list[SLAMetrics]] = defaultdict(list)
for m in metrics_list:
    by_agent[m.agent_id].append(m)

results: list[dict[str, Any]] = []
for agent_id, agent_metrics in by_agent.items():
    aggregated = aggregate_sla_metrics(agent_metrics)
    if aggregated is None:
        continue
    sla = manifest.sla if manifest and manifest.id == agent_id else None
    compliance = _compute_compliance_percent(sla, aggregated)
    results.append({
        "agent_id": agent_id,
        "metrics": aggregated.model_dump(mode="json"),
        "compliance_percent": compliance,
    })
```

---

## Passing Checks ✅

| Check | Status | Details |
|---|---|---|
| Sync I/O in async paths | ✅ | `regenerate_signed_fixtures.py` uses sync I/O but is a CLI-only script, not an async path |
| `limiter.check()` is sync | ✅ | Confirmed `ASAPRateLimiter.check()` is CPU-only (`MemoryStorage`, `MovingWindowRateLimiter`) — no I/O. Same pattern as `POST /asap` handler (line 1537 of `server.py`). Safe in async context. |
| Mutable defaults in Pydantic | ✅ | All `SLAMetrics`, `SLABreach`, `SLADefinition` use immutable defaults |
| `assert` for validation | ✅ | No `assert` in production code; validation uses `HTTPException` and Pydantic validators |
| `asyncio.create_task` retention | ✅ | All task references stored: `_recv_task`, `_ack_check_task`, `_run_task`, `heartbeat_task` |
| Dependency override cleanup | ✅ | No tests override FastAPI dependencies without cleanup |
| Showcase `time.sleep` | ✅ | CLI-only flow; `ASYNC210` ruff ignore configured in `pyproject.toml` for `examples/` |
| SLA compliance single-agent | ℹ️ | `manifest.id == m.agent_id` only matches own manifest. Acceptable for v1.3.0 (single-agent SLA). Document for future multi-agent scenarios. |
| `coverage_report.json` in `.gitignore` | ❌ | See RF-1 |

---

## Verification Steps

After applying fixes, run:

```bash
# 1. Confirm coverage_report.json removed
git status | grep coverage_report  # should show deleted

# 2. Full test suite
uv run pytest tests/ -x -q

# 3. Type checking (ensure field_validator import doesn't break)
uv run mypy src/asap/

# 4. Lint
uv run ruff check src/asap/

# 5. Manual: test bad percentage rejection
python -c "from asap.models.entities import SLADefinition; SLADefinition(availability='bad')"
# Should raise ValidationError after RF-4 fix
```
