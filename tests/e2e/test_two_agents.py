"""End-to-end tests for the two-agent demo flow."""

from pathlib import Path
from typing import Any

import httpx
import pytest

from asap.transport.client import ASAPClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_example(module_name: str) -> object:
    """Load an example module by path to avoid import path issues."""
    module_path = PROJECT_ROOT / "examples" / f"{module_name}.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Example module not found: {module_path}")
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module: {module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coordinator_module = _load_example("coordinator")
echo_module = _load_example("echo_agent")

build_task_envelope = coordinator_module.build_task_envelope
create_coordinator_app = coordinator_module.create_coordinator_app
create_echo_app = echo_module.create_echo_app


@pytest.mark.asyncio()
async def test_two_agents_echo_flow() -> None:
    """Send a TaskRequest from coordinator to echo agent."""
    payload: dict[str, Any] = {"message": "hello"}
    envelope = build_task_envelope(payload)

    coordinator_app = create_coordinator_app("http://coordinator/asap")
    echo_app = create_echo_app("http://echo-agent/asap")

    coordinator_transport = httpx.ASGITransport(app=coordinator_app)
    async with httpx.AsyncClient(
        transport=coordinator_transport,
        base_url="http://coordinator",
    ) as coordinator_client:
        manifest_response = await coordinator_client.get(
            "/.well-known/asap/manifest.json",
        )
    assert manifest_response.status_code == 200

    transport = httpx.ASGITransport(app=echo_app)

    async with ASAPClient("http://echo-agent", transport=transport) as client:
        response = await client.send(envelope)

    assert response.payload_type == "task.response"
    assert response.payload["status"] == "completed"
    assert response.payload["result"]["echoed"] == payload
    assert response.trace_id == envelope.trace_id
    assert response.correlation_id == envelope.id
