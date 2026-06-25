"""SmolAgents integration: SmolAgentsAsapTool wraps an ASAP agent as a SmolAgents Tool (INT-001)."""

from __future__ import annotations

import asyncio
from typing import Any

from asap.client.market import MarketClient
from asap.integrations._base import (
    DEFAULT_SMOLAGENTS_INPUTS as _DEFAULT_INPUTS,  # noqa: F401 (test API)
    build_smolagents_inputs_from_manifest as _build_inputs_from_manifest,  # noqa: F401 (test API)
    eager_resolve_or_defer,
    invoke_skill_async,
    json_schema_to_smolagents_inputs as _json_schema_to_smolagents_inputs,  # noqa: F401 (test API)
    sanitize_tool_name as _sanitize_tool_name,  # noqa: F401 (test API)
    to_str_result as _to_str_result,  # noqa: F401 (test API)
)

# Lazy import to avoid requiring smolagents when not used.
try:
    from smolagents import Tool
except ImportError as _import_error:
    _import_error_smolagents = _import_error
    Tool = None


class SmolAgentsAsapTool(Tool if Tool is not None else object):  # type: ignore[misc]
    """SmolAgents Tool that invokes an ASAP agent by URN; name, description, inputs, forward() from manifest."""

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
        self._resolved = None
        self._skill_id = ""
        resolved, skill_id = eager_resolve_or_defer(self._client, urn)
        if resolved is not None:
            self._resolved = resolved
            self._skill_id = skill_id
            self.name = _sanitize_tool_name(name or resolved.manifest.name or urn)
            self.description = (
                description or resolved.manifest.description or f"Invoke ASAP agent {urn}."
            )
            self.inputs = _build_inputs_from_manifest(resolved.manifest)
        else:
            self.name = _sanitize_tool_name(name or urn or "asap_agent")
            self.description = description or f"Invoke ASAP agent {urn}."
            self.inputs = _DEFAULT_INPUTS.copy()
        super().__init__()

    def forward(self, **kwargs: Any) -> str:
        return _to_str_result(asyncio.run(self._invoke_async(kwargs)))

    async def _invoke_async(self, tool_input: dict[str, Any]) -> str | dict[str, Any]:
        return await invoke_skill_async(self._client, self._urn, self, tool_input)
