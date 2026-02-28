"""Tests for asap.integrations package __init__ (lazy exports, __all__)."""

from __future__ import annotations

import asap.integrations as intmod
import pytest


def test_integrations_module_has_getattr() -> None:
    """Package uses PEP 562 lazy loading."""
    assert hasattr(intmod, "__getattr__")


def test_integrations_all_list() -> None:
    """__all__ declares all public integration exports."""
    expected = {
        "LangChainAsapTool",
        "CrewAIAsapTool",
        "asap_tool_for_urn",
        "LlamaIndexAsapTool",
        "SmolAgentsAsapTool",
        "OpenClawAsapBridge",
        "is_error_result",
        "get_result",
        "create_asap_tools_router",
    }
    assert set(intmod.__all__) == expected
    assert len(intmod.__all__) == len(list(intmod.__all__))


@pytest.mark.parametrize("name", list(intmod.__all__))
def test_lazy_export_resolvable(name: str) -> None:
    """Each name in __all__ is resolvable via __getattr__ (may raise if optional dep missing)."""
    try:
        obj = getattr(intmod, name)
    except (ImportError, ModuleNotFoundError):
        pytest.skip(f"Optional dependency for {name} not installed")
    assert obj is not None
