"""ASAP framework integrations (LangChain, CrewAI, PydanticAI, etc.).

Exports are lazy (PEP 562 __getattr__) to avoid ModuleNotFoundError when
optional dependencies are not installed.

Usage:
    from asap.integrations import LangChainAsapTool   # requires [langchain]
    from asap.integrations import CrewAIAsapTool      # requires [crewai]
    from asap.integrations import asap_tool_for_urn   # requires [pydanticai]
    from asap.integrations import LlamaIndexAsapTool  # requires [llamaindex]
    from asap.integrations import SmolAgentsAsapTool  # requires [smolagents]
    from asap.integrations import OpenClawAsapBridge, get_result, is_error_result  # requires [openclaw]
    from asap.integrations import create_asap_tools_router  # FastAPI; deps in package
"""

from __future__ import annotations

__all__ = [
    "LangChainAsapTool",
    "CrewAIAsapTool",
    "asap_tool_for_urn",
    "LlamaIndexAsapTool",
    "SmolAgentsAsapTool",
    "OpenClawAsapBridge",
    "is_error_result",
    "get_result",
    "create_asap_tools_router",
]


def __getattr__(name: str) -> object:
    if name == "LangChainAsapTool":
        from asap.integrations.langchain import LangChainAsapTool

        return LangChainAsapTool
    if name == "CrewAIAsapTool":
        from asap.integrations.crewai import CrewAIAsapTool

        return CrewAIAsapTool
    if name == "asap_tool_for_urn":
        from asap.integrations.pydanticai import asap_tool_for_urn

        return asap_tool_for_urn
    if name == "LlamaIndexAsapTool":
        from asap.integrations.llamaindex import LlamaIndexAsapTool

        return LlamaIndexAsapTool
    if name == "SmolAgentsAsapTool":
        from asap.integrations.smolagents import SmolAgentsAsapTool

        return SmolAgentsAsapTool
    if name == "OpenClawAsapBridge":
        from asap.integrations.openclaw import OpenClawAsapBridge

        return OpenClawAsapBridge
    if name == "is_error_result":
        from asap.integrations.openclaw import is_error_result

        return is_error_result
    if name == "get_result":
        from asap.integrations.openclaw import get_result

        return get_result
    if name == "create_asap_tools_router":
        from asap.integrations.vercel_ai import create_asap_tools_router

        return create_asap_tools_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
