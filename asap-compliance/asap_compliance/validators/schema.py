"""Schema validation - Pydantic model compliance for ASAP protocol."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional, Type

from pydantic import BaseModel, ValidationError

from asap.models.envelope import Envelope
from asap.models.payloads import (
    ArtifactNotify,
    McpResourceData,
    McpResourceFetch,
    McpToolCall,
    McpToolResult,
    MessageAck,
    MessageSend,
    StateQuery,
    StateRestore,
    TaskCancel,
    TaskRequest,
    TaskResponse,
    TaskUpdate,
)

from asap_compliance.validators.handshake import CheckResult

PAYLOAD_TYPE_TO_MODEL: dict[str, type] = {
    "taskrequest": TaskRequest,
    "task.request": TaskRequest,
    "task_response": TaskResponse,
    "taskresponse": TaskResponse,
    "task.response": TaskResponse,
    "task_update": TaskUpdate,
    "taskupdate": TaskUpdate,
    "task.update": TaskUpdate,
    "task_cancel": TaskCancel,
    "taskcancel": TaskCancel,
    "task.cancel": TaskCancel,
    "message_send": MessageSend,
    "messagesend": MessageSend,
    "message.send": MessageSend,
    "state_query": StateQuery,
    "statequery": StateQuery,
    "state.query": StateQuery,
    "state_restore": StateRestore,
    "staterestore": StateRestore,
    "state.restore": StateRestore,
    "artifact_notify": ArtifactNotify,
    "artifactnotify": ArtifactNotify,
    "artifact.notify": ArtifactNotify,
    "mcp_tool_call": McpToolCall,
    "mcptoolcall": McpToolCall,
    "mcp.tool_call": McpToolCall,
    "mcp_tool_result": McpToolResult,
    "mcptoolresult": McpToolResult,
    "mcp.tool_result": McpToolResult,
    "mcp_resource_fetch": McpResourceFetch,
    "mcpresourcefetch": McpResourceFetch,
    "mcp.resource_fetch": McpResourceFetch,
    "mcp_resource_data": McpResourceData,
    "mcpresourcedata": McpResourceData,
    "mcp.resource_data": McpResourceData,
    "message_ack": MessageAck,
    "messageack": MessageAck,
    "message.ack": MessageAck,
}


@dataclass
class SchemaResult:
    envelope_ok: bool
    payload_ok: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.envelope_ok and self.payload_ok


def _normalize_payload_type(payload_type: str) -> str:
    normalized = payload_type.lower().replace(".", "_").replace("-", "_")
    return re.sub(r"_+", "_", normalized).strip("_")


_NORMALIZED_LOOKUP: dict[str, type] = {
    _normalize_payload_type(k): v for k, v in PAYLOAD_TYPE_TO_MODEL.items()
}


def _get_payload_model(payload_type: str) -> Optional[Type[BaseModel]]:
    direct = PAYLOAD_TYPE_TO_MODEL.get(payload_type)
    if direct is not None:
        return direct
    normalized = _normalize_payload_type(payload_type)
    return _NORMALIZED_LOOKUP.get(normalized)


def validate_envelope(data: dict[str, Any]) -> tuple[bool, list[CheckResult]]:
    results: list[CheckResult] = []

    required = {"asap_version", "sender", "recipient", "payload_type", "payload"}
    missing = required - set(data.keys())
    if missing:
        results.append(
            CheckResult(
                name="envelope_required_fields",
                passed=False,
                message=f"Missing required fields: {sorted(missing)}",
            )
        )
        return False, results

    results.append(
        CheckResult(
            name="envelope_required_fields",
            passed=True,
            message="All required fields present",
        )
    )

    if not isinstance(data.get("payload"), dict):
        results.append(
            CheckResult(
                name="envelope_payload_type",
                passed=False,
                message="payload must be a dict",
            )
        )
        return False, results

    try:
        Envelope.model_validate(data)
        results.append(CheckResult(name="envelope_schema", passed=True, message="Envelope valid"))
        return True, results
    except ValidationError as e:
        results.append(
            CheckResult(
                name="envelope_schema",
                passed=False,
                message=f"Invalid envelope: {e}",
            )
        )
        return False, results


def validate_payload(payload: dict[str, Any], payload_type: str) -> tuple[bool, list[CheckResult]]:
    results: list[CheckResult] = []

    model = _get_payload_model(payload_type)
    if model is None:
        results.append(
            CheckResult(
                name="payload_type_known",
                passed=False,
                message=f"Unknown payload_type: {payload_type}",
            )
        )
        return False, results

    results.append(
        CheckResult(
            name="payload_type_known",
            passed=True,
            message=f"payload_type {payload_type} maps to {model.__name__}",
        )
    )

    try:
        model.model_validate(payload)
        results.append(
            CheckResult(
                name="payload_schema",
                passed=True,
                message=f"{model.__name__} schema valid",
            )
        )
        return True, results
    except ValidationError as e:
        results.append(
            CheckResult(
                name="payload_schema",
                passed=False,
                message=f"Invalid {model.__name__}: {e}",
            )
        )
        return False, results


def validate_extensions_passed_through(data: dict[str, Any]) -> list[CheckResult]:
    results: list[CheckResult] = []
    if "extensions" not in data:
        results.append(
            CheckResult(
                name="extensions_optional",
                passed=True,
                message="extensions is optional",
            )
        )
        return results

    try:
        Envelope.model_validate(data)
        results.append(
            CheckResult(
                name="extensions_passed_through",
                passed=True,
                message="extensions accepted",
            )
        )
    except ValidationError as e:
        results.append(
            CheckResult(
                name="extensions_passed_through",
                passed=False,
                message=f"extensions rejected: {e}",
            )
        )
    return results


def validate_unknown_fields_rejected(
    payload: dict[str, Any], payload_type: str
) -> list[CheckResult]:
    results: list[CheckResult] = []
    model = _get_payload_model(payload_type)
    if model is None:
        results.append(
            CheckResult(
                name="unknown_fields_rejected",
                passed=False,
                message=f"Cannot test: unknown payload_type {payload_type}",
            )
        )
        return results

    payload_with_extra = {**payload, "_unknown_field_compliance_test": "x"}
    try:
        model.model_validate(payload_with_extra)
        results.append(
            CheckResult(
                name="unknown_fields_rejected",
                passed=False,
                message="Expected extra fields to be rejected (extra='forbid')",
            )
        )
    except ValidationError:
        results.append(
            CheckResult(
                name="unknown_fields_rejected",
                passed=True,
                message="Unknown fields correctly rejected",
            )
        )
    return results


def validate_schema(data: dict[str, Any]) -> SchemaResult:
    checks: list[CheckResult] = []
    envelope_ok = False
    payload_ok = False

    env_passed, env_results = validate_envelope(data)
    checks.extend(env_results)
    envelope_ok = env_passed

    if envelope_ok and "payload_type" in data and "payload" in data:
        pld_passed, pld_results = validate_payload(data["payload"], data["payload_type"])
        checks.extend(pld_results)
        payload_ok = pld_passed

        if payload_ok:
            extra_results = validate_unknown_fields_rejected(data["payload"], data["payload_type"])
            checks.extend(extra_results)

    ext_results = validate_extensions_passed_through(data)
    checks.extend(ext_results)

    return SchemaResult(
        envelope_ok=envelope_ok,
        payload_ok=payload_ok,
        checks=checks,
    )
