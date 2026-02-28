"""LangChain integration: LangChainAsapTool wraps an ASAP agent as a LangChain BaseTool (INT-001)."""

from __future__ import annotations

import asyncio
from typing import Any, Type, cast

from pydantic import BaseModel, Field, PrivateAttr, create_model

from asap.client.market import MarketClient, ResolvedAgent
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.entities import Manifest
from asap.models.ids import generate_id

# Lazy import to avoid requiring langchain-core when not used.
try:
    from langchain_core.tools import BaseTool
except ImportError as _import_error:
    _import_error_langchain = _import_error
    BaseTool = None  # type: ignore[misc, assignment]


def _default_input_schema() -> Type[BaseModel]:
    return create_model(
        "AsapToolInput",
        input=(dict[str, Any], Field(description="Skill input payload (key-value)")),
    )


def _json_schema_to_pydantic(
    schema: dict[str, Any], model_name: str = "AsapToolArgs"
) -> Type[BaseModel]:
    if not schema or schema.get("type") != "object":
        return _default_input_schema()
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    field_defs: dict[str, Any] = {}
    for key, prop in props.items():
        if not isinstance(prop, dict):
            continue
        typ = prop.get("type", "string")
        desc = prop.get("description") or key
        if typ == "string":
            field_defs[key] = (
                str,
                Field(default=None if key in required else "", description=desc),
            )
        elif typ == "integer":
            field_defs[key] = (int, Field(default=None if key in required else 0, description=desc))
        elif typ == "number":
            field_defs[key] = (
                float,
                Field(default=None if key in required else 0.0, description=desc),
            )
        elif typ == "boolean":
            field_defs[key] = (
                bool,
                Field(default=None if key in required else False, description=desc),
            )
        elif typ == "array":
            field_defs[key] = (list[Any], Field(default_factory=list, description=desc))
        else:
            field_defs[key] = (dict[str, Any], Field(default_factory=dict, description=desc))
    if not field_defs:
        return _default_input_schema()
    return cast(Type[BaseModel], create_model(model_name, **field_defs))


def _build_args_schema_from_manifest(manifest: Manifest) -> Type[BaseModel] | None:
    skills = getattr(manifest.capabilities, "skills", None) or []
    if not skills:
        return None
    first = skills[0]
    schema = getattr(first, "input_schema", None) if first else None
    if not schema or not isinstance(schema, dict):
        return None
    name = f"Asap_{getattr(first, 'id', 'input').replace('-', '_')}"
    return _json_schema_to_pydantic(schema, model_name=name)


class LangChainAsapTool(BaseTool if BaseTool is not None else object):  # type: ignore[misc]
    """LangChain BaseTool that invokes an ASAP agent by URN (resolve + run)."""

    name: str = "asap_agent"
    description: str = "Invoke an ASAP agent by URN (skill input as dict)."
    args_schema: Type[BaseModel] = _default_input_schema()

    _urn: str = PrivateAttr(default="")
    _client: MarketClient = PrivateAttr()
    _resolved: ResolvedAgent | None = PrivateAttr(default=None)
    _skill_id: str = PrivateAttr(default="")

    def __init__(
        self,
        urn: str,
        client: MarketClient | None = None,
        name: str | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        if BaseTool is None:
            raise RuntimeError(
                "langchain-core is required for LangChainAsapTool. "
                "Install with: pip install asap-protocol[langchain]"
            ) from _import_error_langchain
        client_instance = client or MarketClient()
        tool_name = name or urn or "asap_agent"
        tool_description = description or f"Invoke ASAP agent {urn} (input: skill payload dict)."
        schema_cls: Type[BaseModel] = _default_input_schema()
        resolved: ResolvedAgent | None = None
        skill_id = ""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                resolved = asyncio.run(client_instance.resolve(urn))
                skill_id = (
                    resolved.manifest.capabilities.skills[0].id
                    if resolved.manifest.capabilities.skills
                    else ""
                )
                built = _build_args_schema_from_manifest(resolved.manifest)
                if built is not None:
                    schema_cls = built
                if resolved.manifest.description:
                    tool_description = description or resolved.manifest.description
            except (OSError, ValueError, AgentRevokedException, SignatureVerificationError):
                pass
        super().__init__(
            name=tool_name,
            description=tool_description,
            args_schema=schema_cls,
            **kwargs,
        )
        object.__setattr__(self, "_urn", urn)
        object.__setattr__(self, "_client", client_instance)
        object.__setattr__(self, "_resolved", resolved)
        object.__setattr__(self, "_skill_id", skill_id)

    def _run(self, *args: Any, **kwargs: Any) -> str | dict[str, Any]:
        tool_input = dict(kwargs) if kwargs else (args[0] if args else {})
        if not isinstance(tool_input, dict):
            tool_input = {"input": {"raw": tool_input}}
        return asyncio.run(self._invoke_async(tool_input))

    async def _arun(self, *args: Any, **kwargs: Any) -> str | dict[str, Any]:
        tool_input = dict(kwargs) if kwargs else (args[0] if args else {})
        if not isinstance(tool_input, dict):
            tool_input = {"input": {"raw": tool_input}}
        return await self._invoke_async(tool_input)

    async def _invoke_async(self, tool_input: dict[str, Any]) -> str | dict[str, Any]:
        try:
            if self._resolved is None:
                resolved = await self._client.resolve(self._urn)
                object.__setattr__(self, "_resolved", resolved)
                skill_id = (
                    resolved.manifest.capabilities.skills[0].id
                    if resolved.manifest.capabilities.skills
                    else ""
                )
                object.__setattr__(self, "_skill_id", skill_id)
            if not self._skill_id:
                return "Error: Agent has no skills; cannot build task request."
            resolved_agent = self._resolved
            if resolved_agent is None:
                return "Error: Agent not resolved."
            # Tool input may be the raw dict for the skill, or wrapped in "input"
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
