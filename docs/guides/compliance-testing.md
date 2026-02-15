# Compliance Testing (v1.2)

The **asap-compliance** package validates that ASAP agents follow the protocol specification. Use it to certify your agents are ASAP-compliant and interoperable.

## Installation

```bash
uv add asap-compliance
# or
pip install asap-compliance
```

## Quick Start

Run compliance tests against a running agent:

```bash
pytest --asap-agent-url https://your-agent.example.com -m asap_compliance
```

Or set the URL via environment variable:

```bash
ASAP_AGENT_URL=https://your-agent.example.com pytest -m asap_compliance
```

## Test Categories

| Category | What it validates |
|----------|------------------|
| **handshake** | Agent reachable, health endpoint (200, application/json), manifest schema, signed manifest verification, version compatibility |
| **schema** | Envelope, TaskRequest, TaskResponse, McpToolResult, MessageAck; `extra="forbid"` compliance |
| **state** | Task state machine transitions (PENDING → RUNNING → COMPLETED/FAILED) |
| **sla** | Task completes within timeout; progress schema valid (optional, requires echo skill) |

## Programmatic Usage

### Handshake validation (against live agent)

```python
from asap_compliance import ComplianceConfig, validate_handshake

config = ComplianceConfig(agent_url="https://your-agent.example.com")
result = validate_handshake(config)
if result.passed:
    print("Agent is compliant")
else:
    for check in result.checks:
        if not check.passed:
            print(f"FAIL: {check.name} - {check.message}")
```

### Schema validation (static, for envelope/payload dicts)

```python
from asap_compliance import validate_schema

envelope_dict = {
    "asap_version": "0.1",
    "sender": "urn:asap:agent:a",
    "recipient": "urn:asap:agent:b",
    "payload_type": "task.request",
    "payload": {"conversation_id": "conv-1", "skill_id": "echo", "input": {}},
}
result = validate_schema(envelope_dict)
if result.passed:
    print("Envelope and payload schema valid")
```

### State machine validation

```python
from asap_compliance import ComplianceConfig, validate_state_machine_async

config = ComplianceConfig(
    agent_url="https://your-agent.example.com",
    sla_skill_id="echo",  # Agent must implement this skill
)
result = await validate_state_machine_async(config)
if result.passed:
    print("State transitions correct")
```

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `agent_url` | Required | Base URL of the agent under test |
| `timeout_seconds` | 30.0 | HTTP timeout |
| `test_categories` | handshake, schema, state | Categories to run |
| `sla_skill_id` | echo | Skill ID for SLA and state validation |
| `skip_checks` | [] | Check names to skip (e.g. `sla`) |

## Requirements for Compliance

1. **Health endpoint**: `GET /.well-known/asap/health` returns 200 with `application/json`
2. **Manifest endpoint**: `GET /.well-known/asap/manifest.json` returns valid manifest (plain or signed)
3. **ASAP endpoint**: `POST /asap` accepts JSON-RPC with envelope, returns valid response
4. **Echo skill**: For full pipeline, agent must implement `echo` skill (or set `sla_skill_id` to match)
5. **Schema**: Envelope and payloads must pass Pydantic validation with `extra="forbid"`

## Signed Manifests

The handshake validator accepts both plain and signed manifests. If the agent returns a signed manifest (v1.2), the harness verifies the Ed25519 signature before proceeding.

## See Also

- [asap-compliance README](../../asap-compliance/README.md) — Package overview
- [Identity Signing](identity-signing.md) — How to sign manifests
- [Testing](../testing.md) — General testing guide for ASAP development
