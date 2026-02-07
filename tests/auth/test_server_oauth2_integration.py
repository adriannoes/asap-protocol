"""Integration tests: create_app with and without OAuth2 config."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient
from joserfc import jwk, jwt as jose_jwt

from asap.auth import OAuth2Config
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.handlers import create_default_registry
from asap.transport.jsonrpc import JsonRpcRequest
from asap.transport.server import create_app


def _minimal_manifest() -> Manifest:
    """Minimal manifest for server tests (no auth in manifest)."""
    return Manifest(
        id="urn:asap:agent:test-server",
        name="Test Server",
        version="1.0.0",
        description="Test",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


def _minimal_asap_request() -> dict:
    """Minimal valid JSON-RPC ASAP request body."""
    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:test-server",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="c1",
            skill_id="echo",
            input={"message": "hi"},
        ).model_dump(),
    )
    return JsonRpcRequest(
        method="asap.send",
        params={"envelope": envelope.model_dump(mode="json")},
        id="req-1",
    ).model_dump()


def test_server_without_oauth2_config_accepts_asap_requests() -> None:
    """Verify create_app without oauth2_config allows unauthenticated /asap (backward compat)."""
    app = create_app(
        _minimal_manifest(),
        registry=create_default_registry(),
        rate_limit="100000/minute",
    )
    with TestClient(app) as client:
        response = client.post("/asap", json=_minimal_asap_request())

    assert response.status_code == 200
    data = response.json()
    assert "result" in data or "error" in data
    assert data.get("jsonrpc") == "2.0"


def test_server_with_oauth2_config_rejects_asap_without_token() -> None:
    """Verify create_app with oauth2_config returns 401 for /asap without Bearer token."""

    async def mock_jwks(_uri: str) -> jwk.KeySet:
        key = jwk.RSAKey.generate_key(2048, private=True)
        return jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})

    app = create_app(
        _minimal_manifest(),
        registry=create_default_registry(),
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=mock_jwks,
        ),
        rate_limit="100000/minute",
    )
    with TestClient(app) as client:
        response = client.post("/asap", json=_minimal_asap_request())

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_server_with_oauth2_config_accepts_asap_with_valid_jwt() -> None:
    """Verify create_app with oauth2_config accepts /asap when valid Bearer JWT is sent."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    key_set = jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})

    async def mock_jwks(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        _minimal_manifest(),
        registry=create_default_registry(),
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=mock_jwks,
        ),
        rate_limit="100000/minute",
    )

    now = int(time.time())
    token = jose_jwt.encode(
        {"alg": "RS256", "typ": "JWT"},
        {"sub": "urn:asap:agent:client", "scope": "asap:execute", "exp": now + 3600},
        key,
    )

    with TestClient(app) as client:
        response = client.post(
            "/asap",
            json=_minimal_asap_request(),
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data.get("jsonrpc") == "2.0"
