"""SLA validation - timeout and progress update compliance."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import httpx
from pydantic import ValidationError

from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest, TaskResponse, TaskUpdate

from asap_compliance.config import ComplianceConfig
from asap_compliance.validators.handshake import CheckResult

ASAP_METHOD = "asap.send"


@dataclass
class SlaResult:
    """Aggregated result of SLA validation."""

    timeout_ok: bool
    progress_schema_ok: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.timeout_ok and self.progress_schema_ok


def _asap_url(config: ComplianceConfig) -> str:
    base = config.agent_url.rstrip("/")
    return f"{base}/asap"


def _build_task_request_envelope() -> dict:
    payload = TaskRequest(
        conversation_id="conv_compliance_sla_01",
        skill_id="echo",
        input={"compliance": "sla_test"},
    )
    return {
        "asap_version": "0.1",
        "sender": "urn:asap:agent:compliance-harness",
        "recipient": "urn:asap:agent:under-test",
        "payload_type": "task.request",
        "payload": payload.model_dump(mode="json"),
    }


def _build_jsonrpc_request(envelope: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": ASAP_METHOD,
        "params": {
            "envelope": envelope,
            "idempotency_key": generate_id(),
        },
        "id": f"req-{generate_id()}",
    }


def _parse_task_response(response_body: dict) -> TaskResponse | None:
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


async def _check_task_completes_within_timeout(
    config: ComplianceConfig,
    client: httpx.AsyncClient,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    url = _asap_url(config)
    envelope = _build_task_request_envelope()
    body = _build_jsonrpc_request(envelope)

    start = time.perf_counter()
    try:
        response = await client.post(
            url,
            json=body,
            timeout=config.timeout_seconds,
        )
        elapsed = time.perf_counter() - start
    except httpx.RequestError as e:
        results.append(
            CheckResult(
                name="sla_task_timeout",
                passed=False,
                message=f"Request failed: {e}",
            )
        )
        return results

    if response.status_code != 200:
        results.append(
            CheckResult(
                name="sla_task_timeout",
                passed=False,
                message=f"ASAP endpoint returned {response.status_code}",
            )
        )
        return results

    try:
        data = response.json()
    except Exception as e:
        results.append(
            CheckResult(
                name="sla_task_timeout",
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
                name="sla_task_timeout",
                passed=False,
                message=f"No TaskResponse in response: {msg}",
            )
        )
        return results

    within_timeout = elapsed <= config.timeout_seconds
    results.append(
        CheckResult(
            name="sla_task_timeout",
            passed=within_timeout,
            message=f"Task completed in {elapsed:.2f}s (timeout={config.timeout_seconds}s)"
            if within_timeout
            else f"Task exceeded timeout: {elapsed:.2f}s > {config.timeout_seconds}s",
        )
    )

    status_ok = task_response.status.value in ("completed", "failed", "cancelled")
    results.append(
        CheckResult(
            name="sla_task_terminal_status",
            passed=status_ok,
            message=f"Task reached terminal status: {task_response.status.value}"
            if status_ok
            else f"Task status not terminal: {task_response.status.value}",
        )
    )

    return results


def _check_progress_schema() -> list[CheckResult]:
    results: list[CheckResult] = []
    progress_update = {
        "task_id": "task_01HX5K4N0000000000000000",
        "update_type": "progress",
        "status": "working",
        "progress": {"percent": 50, "message": "Processing...", "eta_seconds": 10},
    }
    try:
        TaskUpdate.model_validate(progress_update)
        results.append(
            CheckResult(
                name="sla_progress_schema",
                passed=True,
                message="TaskUpdate progress schema valid",
            )
        )
    except ValidationError as err:
        results.append(
            CheckResult(
                name="sla_progress_schema",
                passed=False,
                message=f"Invalid TaskUpdate schema: {err}",
            )
        )
    return results


async def validate_sla_async(
    config: ComplianceConfig,
    *,
    client: httpx.AsyncClient | None = None,
) -> SlaResult:
    checks: list[CheckResult] = []
    timeout_ok = False
    progress_schema_ok = False

    progress_results = _check_progress_schema()
    checks.extend(progress_results)
    progress_schema_ok = all(r.passed for r in progress_results)

    if client is not None:
        timeout_results = await _check_task_completes_within_timeout(config, client)
    else:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as c:
            timeout_results = await _check_task_completes_within_timeout(config, c)
    checks.extend(timeout_results)
    timeout_check = next((r for r in timeout_results if r.name == "sla_task_timeout"), None)
    timeout_ok = timeout_check.passed if timeout_check else False

    return SlaResult(
        timeout_ok=timeout_ok,
        progress_schema_ok=progress_schema_ok,
        checks=checks,
    )


def validate_sla(
    config: ComplianceConfig,
    *,
    client: httpx.AsyncClient | None = None,
) -> SlaResult:
    return asyncio.run(validate_sla_async(config, client=client))
