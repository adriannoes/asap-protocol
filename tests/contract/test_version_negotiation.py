"""Contract tests for ASAP-Version negotiation (v2.1 / v2.2 interoperability)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.models.constants import ASAP_DEFAULT_TRANSPORT_VERSION, ASAP_VERSION_HEADER
from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.jsonrpc import VERSION_INCOMPATIBLE
from asap.transport.server import create_app

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter


def _post_asap_json(
    client: TestClient,
    *,
    asap_version_header: str | None,
    rpc_id: str,
    conv_id: str,
) -> object:
    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:contract-client",
        recipient="urn:asap:agent:test-server",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id=conv_id,
            skill_id="echo",
            input={"message": "negotiate"},
        ).model_dump(),
    )
    body = {
        "jsonrpc": "2.0",
        "method": "asap.send",
        "params": {"envelope": envelope.model_dump(mode="json")},
        "id": rpc_id,
    }
    headers: dict[str, str] = {}
    if asap_version_header is not None:
        headers[ASAP_VERSION_HEADER] = asap_version_header
    return client.post("/asap", json=body, headers=headers)


@pytest.fixture
def full_version_server_app(
    sample_manifest: Manifest,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> FastAPI:
    """Server that supports both transport wire versions (v2.1 and v2.2)."""
    app = create_app(sample_manifest, rate_limit="999999/minute")
    if isolated_rate_limiter is not None:
        app.state.limiter = isolated_rate_limiter
    return app


@pytest.fixture
def v21_only_server_app(
    sample_manifest: Manifest,
    monkeypatch: pytest.MonkeyPatch,
    isolated_rate_limiter: ASAPRateLimiter | None,
) -> FastAPI:
    """Server that only advertises support for wire version 2.1 (legacy peer)."""
    import asap.transport.middleware as middleware_module

    monkeypatch.setattr(
        middleware_module,
        "ASAP_SUPPORTED_TRANSPORT_VERSIONS",
        frozenset({"2.1"}),
    )
    monkeypatch.setattr(middleware_module, "ASAP_DEFAULT_TRANSPORT_VERSION", "2.1")
    app = create_app(sample_manifest, rate_limit="999999/minute")
    if isolated_rate_limiter is not None:
        app.state.limiter = isolated_rate_limiter
    return app


def test_v21_client_against_v22_capable_server(
    full_version_server_app: FastAPI,
) -> None:
    """v2.1-only request header succeeds; v2.2-capable server echoes negotiated 2.1."""
    with TestClient(full_version_server_app) as client:
        response = _post_asap_json(
            client,
            asap_version_header="2.1",
            rpc_id="contract-v21",
            conv_id="conv-v21",
        )
    assert response.status_code == 200
    assert response.headers.get("ASAP-Version") == "2.1"
    assert "result" in response.json()


def test_v22_first_client_against_v21_only_server(
    v21_only_server_app: FastAPI,
) -> None:
    """Client offers ``2.2, 2.1``; v2.1-only server falls through to 2.1."""
    with TestClient(v21_only_server_app) as client:
        response = _post_asap_json(
            client,
            asap_version_header="2.2, 2.1",
            rpc_id="contract-v22-fallback",
            conv_id="conv-v22-fallback",
        )
    assert response.status_code == 200
    assert response.headers.get("ASAP-Version") == "2.1"
    assert "result" in response.json()


def test_incompatible_asap_version_returns_version_negotiation_error(
    full_version_server_app: FastAPI,
) -> None:
    """Wire version outside server support yields JSON-RPC -32000."""
    with TestClient(full_version_server_app) as client:
        response = _post_asap_json(
            client,
            asap_version_header="9.9",
            rpc_id="contract-bad-version",
            conv_id="conv-bad",
        )
    assert response.status_code == 200
    assert response.headers.get("ASAP-Version") == ASAP_DEFAULT_TRANSPORT_VERSION
    payload = response.json()
    assert payload.get("error", {}).get("code") == VERSION_INCOMPATIBLE
    assert payload.get("error", {}).get("data", {}).get("requested") == "9.9"
