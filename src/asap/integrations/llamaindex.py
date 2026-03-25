"""LlamaIndex integration: LlamaIndexAsapTool wraps an ASAP agent as a LlamaIndex FunctionTool (INT-001)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Type, cast

from pydantic import BaseModel, Field, create_model

from asap.client.market import MarketClient, ResolvedAgent
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.entities import Manifest
from asap.models.ids import generate_id

# Lazy import to avoid requiring llama-index-core when not used.
# Use ``Any`` so optional ``None`` fallback type-checks when the extra is absent.
FunctionTool: Any = None
ToolMetadata: Any = None
_import_error_llamaindex: ImportError | None = None
try:
    from llama_index.core.tools import FunctionTool as _FunctionTool
    from llama_index.core.tools.types import ToolMetadata as _ToolMetadata

    FunctionTool = _FunctionTool
    ToolMetadata = _ToolMetadata
except ImportError as _import_error:
    _import_error_llamaindex = _import_error


def _default_input_schema() -> Type[BaseModel]:
    return create_model(
        "LlamaIndexAsapToolInput",
        input=(dict[str, Any], Field(description="Skill input payload (key-value)")),
    )


def _json_schema_to_pydantic(
    schema: dict[str, Any], model_name: str = "LlamaIndexAsapToolArgs"
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
            field_defs[key] = (
                int,
                Field(default=None if key in required else 0, description=desc),
            )
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
            field_defs[key] = (
                dict[str, Any],
                Field(default_factory=dict, description=desc),
            )
    if not field_defs:
        return _default_input_schema()
    return cast(Type[BaseModel], create_model(model_name, **field_defs))


def _build_fn_schema_from_manifest(manifest: Manifest) -> Type[BaseModel]:
    skills = getattr(manifest.capabilities, "skills", None) or []
    if not skills:
        return _default_input_schema()
    first = skills[0]
    schema = getattr(first, "input_schema", None) if first else None
    if not schema or not isinstance(schema, dict):
        return _default_input_schema()
    name = f"LlamaIndexAsap_{getattr(first, 'id', 'input').replace('-', '_')}"
    return _json_schema_to_pydantic(schema, model_name=name)


class LlamaIndexAsapTool:
    """LlamaIndex FunctionTool wrapper that invokes an ASAP agent by URN; exposes call(), acall(), metadata."""

    def __init__(
        self,
        urn: str,
        client: MarketClient | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        if FunctionTool is None or ToolMetadata is None:
            assert _import_error_llamaindex is not None
            raise RuntimeError(
                "llama-index-core is required for LlamaIndexAsapTool. "
                "Install with: pip install asap-protocol[llamaindex]"
            ) from _import_error_llamaindex

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
        tool_description = (
            description or resolved.manifest.description or f"Invoke ASAP agent {urn}."
        )
        fn_schema = _build_fn_schema_from_manifest(resolved.manifest)
        agent = resolved

        async def _invoke(**kwargs: Any) -> str:
            input_payload = kwargs.get("input", kwargs)
            if not isinstance(input_payload, dict):
                input_payload = {"value": input_payload}
            if not skill_id:
                return "Error: Agent has no skills; cannot build task request."
            payload = {
                "conversation_id": generate_id(),
                "skill_id": skill_id,
                "input": input_payload,
            }
            try:
                result = await agent.run(payload)
                return json.dumps(result) if isinstance(result, dict) else str(result)
            except AgentRevokedException as e:
                return f"Error: Agent revoked or invalid input: {e!s}"
            except SignatureVerificationError as e:
                return f"Error: Agent revoked or invalid input: {e!s}"
            except ValueError as e:
                return f"Error: Agent revoked or invalid input: {e!s}"

        self._tool = FunctionTool.from_defaults(
            async_fn=_invoke,
            name=tool_name,
            description=tool_description,
            fn_schema=fn_schema,
        )

    @property
    def metadata(self) -> Any:
        return self._tool.metadata

    def call(self, *args: Any, **kwargs: Any) -> Any:
        return self._tool.call(*args, **kwargs)

    async def acall(self, *args: Any, **kwargs: Any) -> Any:
        return await self._tool.acall(*args, **kwargs)
