"""Smoke/E2E: workflow OpenAPI fragment → ASAP skills (mocked upstream)."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest
from _pytest.capture import CaptureFixture

from asap.adapters.openapi import create_from_openapi
from asap.economics.audit import InMemoryAuditStore
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.client import ASAPClient
from asap.transport.rate_limit import create_test_limiter
from asap.transport.server import create_app

from tests.transport.conftest import NoRateLimitTestBase

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_DIR = _REPO_ROOT / "examples" / "workflow_asap_connector"
_FRAGMENT = _EXAMPLE_DIR / "openapi-fragment.json"
_MAIN_PATH = _EXAMPLE_DIR / "main.py"
_MOCK_PATH = _EXAMPLE_DIR / "mock_upstream.py"

_EXPECTED_SKILL_IDS = frozenset({"listWorkflows", "getWorkflow", "triggerWorkflow"})


def _load_example_module(module_name: str, path: Path) -> ModuleType:
    """Import an example module from its file path (mcp_auth_bridge pattern)."""
    example_dir = str(path.parent)
    if example_dir not in sys.path:
        sys.path.insert(0, example_dir)
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mock_workflow_upstream() -> Callable[[httpx.Request], httpx.Response]:
    """Load the shared example mock helper."""
    module = _load_example_module("workflow_asap_connector_mock", _MOCK_PATH)
    mock_fn = getattr(module, "mock_workflow_upstream", None)
    assert callable(mock_fn), "mock_upstream.py must export mock_workflow_upstream"
    return mock_fn


def _workflows_from_task_result(result: dict[str, Any] | None) -> list[Any]:
    """Extract a workflow list from an OpenAPI-proxied TaskResponse.result."""
    assert result is not None, "TaskResponse.result must be present for listWorkflows"
    for key in ("value", "data", "body", "items", "workflows", "response", "json", "_json"):
        payload = result.get(key)
        if isinstance(payload, list):
            return payload
    for _nested_key, val in result.items():
        if isinstance(val, list):
            return val
    raise AssertionError(
        f"Expected a list of workflows in TaskResponse.result, got keys {sorted(result.keys())}",
    )


def _list_workflows_envelope(recipient: str) -> Envelope:
    """Build a task.request envelope for the listWorkflows skill."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:workflow-test-client",
        recipient=recipient,
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-workflow-e2e",
            skill_id="listWorkflows",
            input={},
        ).model_dump(),
    )


class TestWorkflowAsapConnectorExample(NoRateLimitTestBase):
    """E2E coverage for examples/workflow_asap_connector OpenAPI → ASAP bridge."""

    @pytest.mark.asyncio
    async def test_fragment_maps_expected_skill_ids(self) -> None:
        """create_from_openapi exposes listWorkflows, getWorkflow, triggerWorkflow."""
        assert _FRAGMENT.is_file(), f"missing fixture: {_FRAGMENT}"
        mock_fn = _mock_workflow_upstream()
        transport = httpx.MockTransport(mock_fn)
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as http:
            bundle = await create_from_openapi(
                spec_path=_FRAGMENT,
                http_client=http,
                default_capabilities="all",
                manifest_id="urn:asap:agent:workflow-connector-test",
                asap_endpoint="http://test/asap",
            )

        skill_ids = {skill.id for skill in bundle.manifest.capabilities.skills}
        assert skill_ids >= _EXPECTED_SKILL_IDS
        mapped_ids = {cap.skill.id for cap in bundle.capabilities}
        assert mapped_ids >= _EXPECTED_SKILL_IDS

    @pytest.mark.asyncio
    async def test_list_workflows_skill_via_asap_app(self) -> None:
        """Invoke listWorkflows through create_app with mocked upstream."""
        assert _FRAGMENT.is_file(), f"missing fixture: {_FRAGMENT}"
        mock_fn = _mock_workflow_upstream()
        transport = httpx.MockTransport(mock_fn)
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as http:
            built = await create_from_openapi(
                spec_path=_FRAGMENT,
                http_client=http,
                default_capabilities="all",
                manifest_id="urn:asap:agent:workflow-connector-e2e",
                asap_endpoint="http://test/asap",
            )
            app = create_app(
                built.manifest,
                built.registry,
                audit_store=InMemoryAuditStore(),
                rate_limit="999999/minute",
            )
            app.state.limiter = create_test_limiter()
            async with ASAPClient(
                "http://testserver",
                transport=httpx.ASGITransport(app=app),
                require_https=False,
            ) as client:
                response = await client.send(_list_workflows_envelope(built.manifest.id))

        assert response.payload_type == "task.response"
        task_response = TaskResponse.model_validate(response.payload_dict)
        assert task_response.status == TaskStatus.COMPLETED
        workflows = _workflows_from_task_result(task_response.result)
        assert len(workflows) >= 1
        assert isinstance(workflows[0], dict)
        assert workflows[0].get("id") == "wf-demo"

    def test_example_main_is_importable(self) -> None:
        """examples/workflow_asap_connector/main.py must import without side effects."""
        assert _MAIN_PATH.is_file(), f"missing example entrypoint: {_MAIN_PATH}"
        module = _load_example_module("workflow_asap_connector_main", _MAIN_PATH)
        assert callable(getattr(module, "main", None))
        assert callable(getattr(module, "_run", None))

    @pytest.mark.asyncio
    async def test_example_run_prints_skills(
        self,
        capsys: CaptureFixture[str],
    ) -> None:
        """Await main._run(live_base_url=None) and confirm skills + completion."""
        assert _MAIN_PATH.is_file(), f"missing example entrypoint: {_MAIN_PATH}"
        module = _load_example_module("workflow_asap_connector_main_run", _MAIN_PATH)
        await module._run(live_base_url=None)
        captured = capsys.readouterr()
        assert "listWorkflows" in captured.out
        assert "skills:" in captured.out
        assert "listWorkflows:" in captured.out
