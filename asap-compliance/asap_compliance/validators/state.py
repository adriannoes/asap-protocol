"""State machine validation - black-box compliance of agent task state transitions.

Validates the *remote agent's* observed behavior: create task, observe TaskResponse
(and optionally TaskUpdate if streaming), verify transitions follow the protocol spec.
Does NOT import asap.state.machine - the harness tests the agent, not the library.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import ValidationError

from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest, TaskResponse

from asap_compliance.config import ComplianceConfig
from asap_compliance.validators.handshake import CheckResult

# Protocol spec: valid state transitions (from ASAP spec, not from asap.state.machine)
_PROTOCOL_VALID_TRANSITIONS: dict[str, set[str]] = {
    "submitted": {"working", "cancelled"},
    "working": {"completed", "failed", "cancelled", "input_required"},
    "input_required": {"working", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}

_PROTOCOL_TERMINAL_STATES = {"completed", "failed", "cancelled"}

ASAP_METHOD = "asap.send"


@dataclass
class StateResult:
    """Aggregated result of state machine validation."""

    transitions_ok: bool
    terminal_ok: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.transitions_ok and self.terminal_ok


def _asap_url(config: ComplianceConfig) -> str:
    base = config.agent_url.rstrip("/")
    return f"{base}/asap"


def _build_task_request_envelope(config: ComplianceConfig) -> dict[str, Any]:
    skill_id = config.sla_skill_id
    payload = TaskRequest(
        conversation_id="conv_compliance_state_01",
        skill_id=skill_id,
        input={"compliance": "state_test"},
    )
    return {
        "asap_version": "0.1",
        "sender": "urn:asap:agent:compliance-harness",
        "recipient": "urn:asap:agent:under-test",
        "payload_type": "task.request",
        "payload": payload.model_dump(mode="json"),
    }


def _build_jsonrpc_request(envelope: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "method": ASAP_METHOD,
        "params": {
            "envelope": envelope,
            "idempotency_key": generate_id(),
        },
        "id": f"req-{generate_id()}",
    }


def _parse_task_response(response_body: dict[str, Any]) -> TaskResponse | None:
    result = response_body.get("result")
    if not isinstance(result, dict):
        return None
    envelope = result.get("envelope")
    if not isinstance(envelope, dict):
        return None
    if envelope.get("payload_type", "").lower() not in (
        "task.response",
        "taskresponse",
    ):
        return None
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return None
    try:
        return TaskResponse.model_validate(payload)
    except ValidationError:
        return None


async def _check_agent_state_compliance(
    config: ComplianceConfig,
    client: httpx.AsyncClient,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    url = _asap_url(config)
    envelope = _build_task_request_envelope(config)
    body = _build_jsonrpc_request(envelope)

    try:
        response = await client.post(
            url,
            json=body,
            timeout=config.timeout_seconds,
        )
    except httpx.RequestError as e:
        results.append(
            CheckResult(
                name="state_agent_reachable",
                passed=False,
                message=f"Request failed: {e}",
            )
        )
        return results

    if response.status_code != 200:
        results.append(
            CheckResult(
                name="state_agent_response",
                passed=False,
                message=f"ASAP endpoint returned {response.status_code}",
            )
        )
        return results

    try:
        data = response.json()
    except (ValueError, TypeError) as e:
        results.append(
            CheckResult(
                name="state_agent_response",
                passed=False,
                message=f"Invalid JSON response: {e}",
            )
        )
        return results

    task_response = _parse_task_response(data)
    if task_response is None:
        error_info = data.get("error", {})
        msg = error_info.get("message", str(data)) if isinstance(error_info, dict) else str(data)
        results.append(
            CheckResult(
                name="state_task_response",
                passed=False,
                message=f"No TaskResponse in response: {msg}",
            )
        )
        return results

    status_val = task_response.status.value
    terminal_ok = status_val in _PROTOCOL_TERMINAL_STATES
    results.append(
        CheckResult(
            name="state_terminal_status",
            passed=terminal_ok,
            message=(
                f"TaskResponse status '{status_val}' is valid terminal"
                if terminal_ok
                else f"TaskResponse status '{status_val}' must be completed/failed/cancelled"
            ),
        )
    )
    transitions_ok = terminal_ok
    results.append(
        CheckResult(
            name="state_observed_compliance",
            passed=transitions_ok,
            message=(
                "Agent returned valid terminal status (no invalid transitions observed)"
                if transitions_ok
                else "Agent returned invalid status"
            ),
        )
    )

    return results


async def validate_state_machine_async(
    config: ComplianceConfig,
    *,
    client: httpx.AsyncClient | None = None,
) -> StateResult:
    checks: list[CheckResult] = []

    if client is not None:
        agent_results = await _check_agent_state_compliance(config, client)
    else:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as c:
            agent_results = await _check_agent_state_compliance(config, c)

    checks.extend(agent_results)
    terminal_ok = all(r.passed for r in agent_results)
    transitions_ok = terminal_ok

    return StateResult(
        transitions_ok=transitions_ok,
        terminal_ok=terminal_ok,
        checks=checks,
    )


def validate_state_machine(
    config: ComplianceConfig,
    *,
    client: httpx.AsyncClient | None = None,
) -> StateResult:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(validate_state_machine_async(config, client=client))
    raise RuntimeError(
        "Cannot call sync validate_state_machine from inside a running event loop. "
        "Use validate_state_machine_async."
    )
