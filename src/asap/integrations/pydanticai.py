"""PydanticAI integration: wrap an ASAP agent as a PydanticAI Tool (INT-001)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, TypeVar, cast

from asap.client.market import MarketClient, ResolvedAgent
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.entities import Manifest
from asap.models.ids import generate_id

# Lazy import to avoid requiring pydantic-ai when not used.
try:
    from pydantic_ai.tools import Tool as PydanticAITool
except ImportError as _import_error:
    _import_error_pydantic_ai = _import_error
    PydanticAITool = None  # type: ignore[misc, assignment]

T = TypeVar("T")

# Default JSON schema when agent schema is unavailable (generic object input).
DEFAULT_PARAMETERS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "input": {
            "type": "object",
            "description": "Skill input payload (key-value)",
        },
    },
}


def _parameters_schema_from_manifest(manifest: Manifest) -> dict[str, Any]:
    skills = getattr(manifest.capabilities, "skills", None) or []
    if not skills:
        return DEFAULT_PARAMETERS_JSON_SCHEMA
    first = skills[0]
    schema = getattr(first, "input_schema", None) if first else None
    if not schema or not isinstance(schema, dict) or schema.get("type") != "object":
        return DEFAULT_PARAMETERS_JSON_SCHEMA
    return cast(dict[str, Any], schema)


def _to_str_result(value: str | dict[str, Any]) -> str:
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


def asap_tool_for_urn(
    urn: str,
    client: MarketClient | None = None,
    name: str | None = None,
    description: str | None = None,
) -> Any:
    """Create a PydanticAI Tool that invokes an ASAP agent by URN (resolve at build, run cached)."""
    if PydanticAITool is None:
        raise RuntimeError(
            "pydantic-ai is required for asap_tool_for_urn. "
            "Install with: pip install asap-protocol[pydanticai]"
        ) from _import_error_pydantic_ai

    client_instance = client or MarketClient()
    resolved: ResolvedAgent | None = None
    try:
        resolved = asyncio.run(client_instance.resolve(urn))
    except Exception as e:
        raise ValueError(f"Failed to resolve agent {urn}: {e}") from e

    skill_id = ""
    if resolved.manifest.capabilities.skills:
        skill_id = resolved.manifest.capabilities.skills[0].id
    tool_name = name or resolved.manifest.name or urn
    tool_description = description or resolved.manifest.description or f"Invoke ASAP agent {urn}."
    parameters_schema = _parameters_schema_from_manifest(resolved.manifest)
    agent = resolved

    async def _invoke(**kwargs: Any) -> str:
        input_payload = kwargs.get("input", kwargs)
        if not isinstance(input_payload, dict):
            input_payload = {"value": input_payload}
        if not skill_id:
            return _to_str_result("Error: Agent has no skills; cannot build task request.")
        payload = {
            "conversation_id": generate_id(),
            "skill_id": skill_id,
            "input": input_payload,
        }
        try:
            result = await agent.run(payload)
            return _to_str_result(result if isinstance(result, dict) else str(result))
        except AgentRevokedException as e:
            return _to_str_result(f"Error: Agent revoked or invalid input: {e!s}")
        except SignatureVerificationError as e:
            return _to_str_result(f"Error: Agent revoked or invalid input: {e!s}")
        except ValueError as e:
            return _to_str_result(f"Error: Agent revoked or invalid input: {e!s}")

    return PydanticAITool.from_schema(
        _invoke,
        name=tool_name,
        description=tool_description,
        json_schema=parameters_schema,
        takes_ctx=False,
    )
