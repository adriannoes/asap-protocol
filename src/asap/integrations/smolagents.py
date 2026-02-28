"""SmolAgents integration: SmolAgentsAsapTool wraps an ASAP agent as a SmolAgents Tool (INT-001)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from asap.client.market import MarketClient, ResolvedAgent
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.entities import Manifest
from asap.models.ids import generate_id

# Lazy import to avoid requiring smolagents when not used.
try:
    from smolagents import Tool
except ImportError as _import_error:
    _import_error_smolagents = _import_error
    Tool = None

# SmolAgents AUTHORIZED_TYPES for inputs and output_type.
_SMOLAGENTS_TYPES = frozenset(
    {"string", "boolean", "integer", "number", "image", "audio", "array", "object", "any", "null"}
)

_DEFAULT_INPUTS: dict[str, dict[str, str]] = {
    "input": {
        "type": "object",
        "description": "Skill input payload (key-value dict matching agent schema)",
    }
}


def _sanitize_tool_name(name: str) -> str:
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    sanitized = sanitized.strip("_") or "asap_agent"
    if sanitized[0].isdigit():
        sanitized = "asap_" + sanitized
    return sanitized


def _json_schema_to_smolagents_inputs(schema: dict[str, Any]) -> dict[str, dict[str, str]]:
    if not schema or schema.get("type") != "object":
        return _DEFAULT_INPUTS.copy()
    props = schema.get("properties") or {}
    result: dict[str, dict[str, str]] = {}
    for key, prop in props.items():
        if not isinstance(prop, dict):
            continue
        typ = prop.get("type", "string")
        desc = prop.get("description") or key
        smol_type = typ if typ in _SMOLAGENTS_TYPES else "string"
        result[key] = {"type": smol_type, "description": desc}
    return result if result else _DEFAULT_INPUTS.copy()


def _build_inputs_from_manifest(manifest: Manifest) -> dict[str, dict[str, str]]:
    skills = getattr(manifest.capabilities, "skills", None) or []
    if not skills:
        return _DEFAULT_INPUTS.copy()
    first = skills[0]
    schema = getattr(first, "input_schema", None) if first else None
    if not schema or not isinstance(schema, dict):
        return _DEFAULT_INPUTS.copy()
    return _json_schema_to_smolagents_inputs(schema)


def _to_str_result(value: str | dict[str, Any]) -> str:
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


class SmolAgentsAsapTool(Tool if Tool is not None else object):  # type: ignore[misc]
    """SmolAgents Tool that invokes an ASAP agent by URN; name, description, inputs, forward() from manifest."""

    # Class attributes required by smolagents.Tool (set per instance)
    # We set them dynamically per instance, so we use a base that passes validation.
    name: str = "asap_agent"
    description: str = "Invoke an ASAP agent (input: skill payload dict)."
    inputs: dict[str, dict[str, str]] = _DEFAULT_INPUTS.copy()
    output_type: str = "string"
    skip_forward_signature_validation: bool = True  # forward takes **kwargs for dynamic schema

    def __init__(
        self,
        urn: str,
        client: MarketClient | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        if Tool is None:
            raise RuntimeError(
                "smolagents is required for SmolAgentsAsapTool. "
                "Install with: pip install asap-protocol[smolagents]"
            ) from _import_error_smolagents

        self._urn = urn
        self._client = client or MarketClient()
        self._resolved: ResolvedAgent | None = None
        self._skill_id = ""

        try:
            resolved = asyncio.run(self._client.resolve(urn))
            self._resolved = resolved
            self._skill_id = (
                resolved.manifest.capabilities.skills[0].id
                if resolved.manifest.capabilities.skills
                else ""
            )
            raw_name = name or resolved.manifest.name or urn
            self.name = _sanitize_tool_name(raw_name)
            self.description = (
                description or resolved.manifest.description or f"Invoke ASAP agent {urn}."
            )
            self.inputs = _build_inputs_from_manifest(resolved.manifest)
        except (OSError, ValueError, AgentRevokedException, SignatureVerificationError):
            raw_name = name or urn or "asap_agent"
            self.name = _sanitize_tool_name(raw_name)
            self.description = description or f"Invoke ASAP agent {urn}."
            self.inputs = _DEFAULT_INPUTS.copy()

        super().__init__()

    def forward(self, **kwargs: Any) -> str:
        return _to_str_result(asyncio.run(self._invoke_async(kwargs)))

    async def _invoke_async(self, tool_input: dict[str, Any]) -> str | dict[str, Any]:
        try:
            if self._resolved is None:
                resolved = await self._client.resolve(self._urn)
                self._resolved = resolved
                self._skill_id = (
                    resolved.manifest.capabilities.skills[0].id
                    if resolved.manifest.capabilities.skills
                    else ""
                )
            if not self._skill_id:
                return "Error: Agent has no skills; cannot build task request."
            resolved_agent = self._resolved
            if resolved_agent is None:
                return "Error: Agent not resolved."
            input_payload = tool_input.get("input", tool_input)
            if not isinstance(input_payload, dict):
                input_payload = {"value": input_payload}
            payload = {
                "conversation_id": generate_id(),
                "skill_id": self._skill_id,
                "input": input_payload,
            }
            result = await resolved_agent.run(payload)
            if isinstance(result, dict):
                return result
            return str(result)
        except AgentRevokedException as e:
            return f"Error: Agent revoked or invalid input: {e!s}"
        except SignatureVerificationError as e:
            return f"Error: Agent revoked or invalid input: {e!s}"
        except ValueError as e:
            return f"Error: Agent revoked or invalid input: {e!s}"
