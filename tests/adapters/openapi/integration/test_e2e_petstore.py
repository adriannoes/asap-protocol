"""E2E: PetStore-shaped OpenAPI fragment → ASAP agent (mocked upstream)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from asap.adapters.openapi import create_from_openapi
from asap.economics.audit import InMemoryAuditStore
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.client import ASAPClient
from asap.transport.rate_limit import create_test_limiter
from asap.transport.server import create_app

from tests.transport.conftest import NoRateLimitTestBase

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PETSTORE_FRAGMENT = _REPO_ROOT / "examples" / "openapi_petstore" / "openapi-fragment.json"


def _pets_list_from_task_result(result: dict[str, Any] | None) -> list[Any]:
    assert result is not None, "TaskResponse.result must be present for findPetsByStatus"
    for key in ("value", "data", "body", "items", "response", "json", "_json"):
        payload = result.get(key)
        if isinstance(payload, list):
            return payload
    for _nested_key, val in result.items():
        if isinstance(val, list):
            return val
    raise AssertionError(
        f"Expected a list of pets in TaskResponse.result, got keys {sorted(result.keys())}",
    )


def _mock_petstore(request: httpx.Request) -> httpx.Response:
    if request.method == "GET" and "findByStatus" in request.url.path:
        return httpx.Response(
            200,
            json=[{"id": 42, "name": "MockPet", "status": "available"}],
        )
    return httpx.Response(404, text=f"unexpected: {request.method} {request.url}")


class TestPetstoreOpenAPIAdapterE2E(NoRateLimitTestBase):
    """E2E: PetStore-shaped fragment with mocked upstream."""

    @pytest.mark.asyncio
    async def test_find_pets_by_status_calls_upstream_and_returns_pet_list(self) -> None:
        assert _PETSTORE_FRAGMENT.is_file(), f"missing fixture: {_PETSTORE_FRAGMENT}"
        transport = httpx.MockTransport(_mock_petstore)
        async with httpx.AsyncClient(transport=transport, timeout=30.0) as http:
            built = await create_from_openapi(
                spec_path=_PETSTORE_FRAGMENT,
                http_client=http,
                default_capabilities="GET",
                manifest_id="urn:asap:agent:petstore-e2e",
                asap_endpoint="http://test/asap",
            )
            audit = InMemoryAuditStore()
            app = create_app(
                built.manifest,
                built.registry,
                audit_store=audit,
                rate_limit="999999/minute",
            )
            app.state.limiter = create_test_limiter()
            asgi = httpx.ASGITransport(app=app)

            envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:petstore-test-client",
                recipient=built.manifest.id,
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id="conv-petstore-e2e",
                    skill_id="findPetsByStatus",
                    input={"status": "available"},
                ).model_dump(),
            )

            async with ASAPClient(
                "http://testserver",
                transport=asgi,
                require_https=False,
            ) as client:
                response = await client.send(envelope)

        assert response.payload_type == "task.response"
        task_response = TaskResponse.model_validate(response.payload_dict)
        assert task_response.status == TaskStatus.COMPLETED
        pets = _pets_list_from_task_result(task_response.result)
        assert len(pets) >= 1
        assert isinstance(pets[0], dict)
        assert "id" in pets[0]
