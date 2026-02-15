# ASAP Compliance Harness

Protocol compliance testing suite for ASAP (Async Simple Agent Protocol) implementations.

## Overview

The Compliance Harness validates that ASAP agents follow the protocol specification. Third parties can use this package to certify their agents are ASAP-compliant, enabling ecosystem interoperability.

## Installation

```bash
uv add asap-compliance
# or
pip install asap-compliance
```

## Usage

Run compliance tests against an agent:

```bash
pytest --asap-agent-url https://your-agent.example.com -m asap_compliance
```

Or set the agent URL via environment variable:

```bash
ASAP_AGENT_URL=https://your-agent.example.com pytest -m asap_compliance
```

## Test Categories

- **handshake** (implemented): Agent connection, health/content-type, manifest schema,
  signature verification, version negotiation
- **schema** (implemented): Pydantic model compliance (Envelope, TaskRequest,
  TaskResponse, McpToolResult, MessageAck, extensions, extra='forbid')
- **state**: Task state machine transitions

## Programmatic Usage

```python
# Handshake validation (against live agent)
from asap_compliance import ComplianceConfig, validate_handshake

config = ComplianceConfig(agent_url="https://your-agent.example.com")
result = validate_handshake(config)
if result.passed:
    print("Agent is compliant")
else:
    for check in result.checks:
        if not check.passed:
            print(f"FAIL: {check.name} - {check.message}")

# Schema validation (static, for envelope/payload dicts)
from asap_compliance import validate_schema

envelope_dict = {"asap_version": "0.1", "sender": "urn:asap:agent:a", ...}
schema_result = validate_schema(envelope_dict)
if schema_result.passed:
    print("Envelope and payload schema valid")
```

## Development

```bash
cd asap-compliance
uv sync
uv run pytest
```
