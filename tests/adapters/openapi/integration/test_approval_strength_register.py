"""Integration: OpenAPI-derived DELETE capability + approval strength + WebAuthn gate."""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from openapi_pydantic import parse_obj

from asap.adapters.openapi.approval import collect_webauthn_required_capability_names
from asap.adapters.openapi.capability_mapper import map_openapi_to_capabilities
from asap.auth.agent_jwt import create_host_jwt
from asap.auth.capabilities import CapabilityDefinition, CapabilityRegistry
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
from asap.auth.self_auth import FreshSessionConfig, reset_default_webauthn_verifier_cache
from asap.models.entities import Manifest
from asap.transport.server import create_app
from tests.crypto.jwk_helpers import ed25519_public_jwk
from tests.transport.conftest import NoRateLimitTestBase

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter

_HOST_JWT_AUDIENCE = "urn:asap:agent:test-server"


def _openapi_with_delete() -> dict[str, object]:
    return {
        "openapi": "3.0.3",
        "info": {"title": "Delete API", "version": "1.0.0"},
        "paths": {
            "/widgets/{widgetId}": {
                "delete": {
                    "operationId": "removeWidget",
                    "summary": "Remove a widget",
                    "parameters": [
                        {
                            "name": "widgetId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {"204": {"description": "deleted"}},
                },
            },
        },
    }


class TestOpenAPIApprovalStrengthRegister(NoRateLimitTestBase):
    """Register path respects WebAuthn policy derived from OpenAPI HTTP method mapping."""

    def test_delete_capability_triggers_403_webauthn_when_agent_controls_browser(
        self,
        sample_manifest: Manifest,
        isolated_rate_limiter: ASAPRateLimiter | None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """DELETE mapped to webauthn + browser flag + real verifier → 403 without assertion."""
        if importlib.util.find_spec("webauthn") is None:
            pytest.skip("webauthn extra not installed in this environment")

        monkeypatch.setenv("ASAP_WEBAUTHN_RP_ID", "localhost")
        monkeypatch.setenv("ASAP_WEBAUTHN_ORIGIN", "http://127.0.0.1")
        reset_default_webauthn_verifier_cache()

        doc = parse_obj(_openapi_with_delete())
        caps = map_openapi_to_capabilities(doc)
        webauthn_caps = collect_webauthn_required_capability_names(
            caps,
            {"DELETE": "webauthn"},
        )
        assert "removeWidget" in webauthn_caps

        agent_store = InMemoryAgentStore()
        host_store = InMemoryHostStore(agent_store=agent_store)
        cap_registry = CapabilityRegistry()
        for cap in caps:
            cap_registry.register(
                CapabilityDefinition(
                    name=cap.skill.id,
                    description=cap.skill.description,
                    input_schema=cap.skill.input_schema,
                    output_schema=cap.skill.output_schema,
                ),
            )

        app = create_app(
            sample_manifest,
            rate_limit="999999/minute",
            identity_host_store=host_store,
            identity_agent_store=agent_store,
            identity_rate_limit="999999/minute",
            identity_jwt_audience=_HOST_JWT_AUDIENCE,
            identity_fresh_session_config=FreshSessionConfig(
                window_seconds=300,
                require_webauthn_for=webauthn_caps,
            ),
        )
        if isolated_rate_limiter is not None:
            app.state.limiter = isolated_rate_limiter
        app.state.capability_registry = cap_registry

        host_sk = Ed25519PrivateKey.generate()
        agent_sk = Ed25519PrivateKey.generate()
        agent_jwk = ed25519_public_jwk(agent_sk)
        token = create_host_jwt(
            host_sk,
            aud=_HOST_JWT_AUDIENCE,
            agent_public_key=agent_jwk,
            ttl_seconds=120,
        )
        client = TestClient(app)
        response = client.post(
            "/asap/agent/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "capabilities": ["removeWidget"],
                "agent_controls_browser": True,
            },
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "webauthn_required"}
