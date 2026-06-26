"""LlamaIndex integration: LlamaIndexAsapTool wraps an ASAP agent as a LlamaIndex FunctionTool (INT-001)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Type

from pydantic import BaseModel

from asap.client.market import MarketClient
from asap.integrations._base import (
    build_fn_schema_from_manifest as _build_fn_schema_from_manifest,  # noqa: F401 (test API)
    eager_resolve_or_raise,
    invoke_skill_json_async,
)
from asap.integrations._base import default_input_schema as _default_input_schema
from asap.integrations._base import (
    json_schema_to_pydantic as _json_schema_to_pydantic,  # noqa: F401 (test API)
)

# Lazy import to avoid requiring llama-index-core when not used (``Any`` keeps ``None`` typed).
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
            raise RuntimeError(
                "llama-index-core is required for LlamaIndexAsapTool. "
                "Install with: pip install asap-protocol[llamaindex]"
            ) from (_import_error_llamaindex or ImportError("llama-index-core is not installed"))
        client_instance = client or MarketClient()
        default_desc = f"Invoke ASAP agent {urn}."
        tool_name = name or urn
        tool_description = description or default_desc
        fn_schema: Type[BaseModel] = _default_input_schema()
        resolved, skill_id = eager_resolve_or_raise(client_instance, urn)
        if resolved is not None:
            tool_name = name or resolved.manifest.name or urn
            tool_description = description or resolved.manifest.description or default_desc
            fn_schema = _build_fn_schema_from_manifest(
                resolved.manifest, model_prefix="LlamaIndexAsap"
            )
        cache = SimpleNamespace(_resolved=resolved, _skill_id=skill_id)

        async def _invoke(**kwargs: Any) -> str:
            return await invoke_skill_json_async(client_instance, urn, cache, kwargs)

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
