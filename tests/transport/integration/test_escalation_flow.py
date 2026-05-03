"""End-to-end escalation: request capability → approve → grants active."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from asap.auth.agent_jwt import create_agent_jwt, create_host_jwt
from asap.auth.capabilities import CapabilityDefinition
from asap.auth.identity import jwk_thumbprint_sha256
from tests.crypto.jwk_helpers import ed25519_public_jwk
from tests.transport.test_capability_routes import (
    _HOST_JWT_AUDIENCE,
    _register_and_activate,
    _setup,
)
from tests.transport.test_escalation_routes import _activate_host_with_defaults

if TYPE_CHECKING:
    from asap.models.entities import Manifest
    from asap.transport.rate_limit import ASAPRateLimiter


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
class TestEscalationFlowE2E:
    async def test_escalation_approve_then_active_grants(
        self,
        sample_manifest: Manifest,
        isolated_rate_limiter: ASAPRateLimiter | None,
    ) -> None:
        caps = [
            CapabilityDefinition(name="file:read", description="r"),
            CapabilityDefinition(name="admin:config", description="a"),
        ]
        app, agent_store, host_store, registry = _setup(
            sample_manifest, isolated_rate_limiter, capabilities=caps
        )
        host_sk = Ed25519PrivateKey.generate()
        agent_sk = Ed25519PrivateKey.generate()
        client = TestClient(app)
        aid = await _register_and_activate(client, app, agent_store, host_sk, agent_sk)
        await _activate_host_with_defaults(
            host_store,
            agent_store,
            aid,
            default_capabilities=["file:read"],
        )
        sess = await agent_store.get(aid)
        assert sess is not None
        registry.grant(aid, "file:read", granted_by=sess.host_id)

        host_tp = jwk_thumbprint_sha256(ed25519_public_jwk(host_sk))
        agent_tok = create_agent_jwt(
            agent_sk,
            host_thumbprint=host_tp,
            agent_id=aid,
            aud=_HOST_JWT_AUDIENCE,
            capabilities=["file:read"],
        )
        esc = client.post(
            "/asap/agent/request-capability",
            headers={"Authorization": f"Bearer {agent_tok}"},
            json={"capabilities": [{"name": "admin:config"}]},
        )
        assert esc.status_code == 200
        assert esc.json()["status"] == "pending"

        approval_store = app.state.identity_approval_store
        await approval_store.approve(aid, "e2e-user")

        host_jwt = create_host_jwt(host_sk, aud=_HOST_JWT_AUDIENCE, ttl_seconds=120)
        st = client.get(
            f"/asap/agent/status?agent_id={aid}",
            headers={"Authorization": f"Bearer {host_jwt}"},
        )
        assert st.status_code == 200
        body = st.json()
        assert body["status"] == "active"
        cap_names = {g.get("capability") for g in body.get("capabilities", [])}
        assert "admin:config" in cap_names
        assert "file:read" in cap_names
