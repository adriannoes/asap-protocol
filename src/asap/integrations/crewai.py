"""CrewAI integration: CrewAIAsapTool wraps an ASAP agent as a CrewAI BaseTool (INT-001)."""

from __future__ import annotations

import asyncio
from typing import Any, Type

from pydantic import BaseModel, PrivateAttr

from asap.client.market import MarketClient, ResolvedAgent
from asap.integrations._base import (
    build_args_schema_from_manifest as _build_args_schema_from_manifest,  # noqa: F401 (test API)
    coerce_tool_input,
    default_input_schema as _default_input_schema,
    eager_resolve_or_defer,
    invoke_skill_json_async,
    json_schema_to_pydantic as _json_schema_to_pydantic,  # noqa: F401 (test API)
)

CrewAIBaseTool: Any = None  # ``Any`` so the ``None`` fallback type-checks when crewai is absent.
_import_error_crewai: ImportError | None = None
try:
    from crewai.tools import BaseTool as _CrewAIBaseTool

    CrewAIBaseTool = _CrewAIBaseTool
except ImportError as _import_error:
    _import_error_crewai = _import_error


class CrewAIAsapTool(CrewAIBaseTool if CrewAIBaseTool is not None else object):  # type: ignore[misc]
    """CrewAI BaseTool that invokes an ASAP agent by URN; returns str for agent use."""

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
        if CrewAIBaseTool is None:
            raise RuntimeError(
                "crewai is required for CrewAIAsapTool. Install with: pip install asap-protocol[crewai]"
            ) from (_import_error_crewai or ImportError("crewai is not installed"))
        client_instance = client or MarketClient()
        tool_description = description or f"Invoke ASAP agent {urn} (input: skill payload dict)."
        schema_cls: Type[BaseModel] = _default_input_schema()
        resolved, skill_id = eager_resolve_or_defer(client_instance, urn)
        if resolved is not None:
            built = _build_args_schema_from_manifest(resolved.manifest, model_prefix="CrewAIAsap")
            schema_cls = built or schema_cls
            tool_description = description or resolved.manifest.description or tool_description
        super().__init__(
            name=name or urn or "asap_agent",
            description=tool_description,
            args_schema=schema_cls,
            **kwargs,
        )
        object.__setattr__(self, "_urn", urn)
        object.__setattr__(self, "_client", client_instance)
        object.__setattr__(self, "_resolved", resolved)
        object.__setattr__(self, "_skill_id", skill_id)

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._invoke_async(coerce_tool_input(args, kwargs)))

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return await self._invoke_async(coerce_tool_input(args, kwargs))

    async def _invoke_async(self, tool_input: dict[str, Any]) -> str:
        return await invoke_skill_json_async(self._client, self._urn, self, tool_input)
