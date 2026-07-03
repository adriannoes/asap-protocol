"""Regression guards: identity routes 503 when ``identity_limiter`` is missing.

v2.5.1 migrated nine identity endpoints from inline
``request.app.state.identity_limiter.check(request)`` to
``Depends(require_identity_limiter)``. A misconfigured server must return
503 with a typed message, not ``AttributeError`` → HTTP 500.

This module covers the seven routes not already guarded in
``test_capability_routes.py`` (``GET /asap/capability/list``) and
``s3_regression_test.py`` (``POST /asap/agent/register``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from tests.crypto.jwk_helpers import make_ed25519_jwk
from tests.transport.test_capability_routes import _setup

if TYPE_CHECKING:
    from asap.models.entities import Manifest
    from asap.transport.rate_limit import ASAPRateLimiter

_IDENTITY_LIMITER_503_DETAIL = "identity_limiter not set"

# Minimal request shapes so FastAPI reaches ``require_identity_limiter``.
_IDENTITY_ROUTE_CASES: list[tuple[str, str, dict[str, Any] | None]] = [
    ("GET", "/asap/capability/describe?name=file:read", None),
    ("POST", "/asap/capability/execute", {}),
    ("POST", "/asap/agent/reactivate", {"agent_id": "agent-placeholder"}),
    ("GET", "/asap/agent/status?agent_id=agent-placeholder", None),
    ("POST", "/asap/agent/revoke", {"agent_id": "agent-placeholder"}),
    (
        "POST",
        "/asap/agent/rotate-key",
        {"agent_id": "agent-placeholder", "new_public_key": make_ed25519_jwk()},
    ),
    ("POST", "/asap/agent/request-capability", {"capabilities": [{"name": "file:read"}]}),
]


@pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")
class TestIdentityLimiterMissingReturns503Extended:
    """Remaining identity routes must 503 cleanly when the limiter is unconfigured."""

    @pytest.mark.parametrize(("method", "path", "json_body"), _IDENTITY_ROUTE_CASES)
    def test_identity_route_returns_503_when_limiter_missing(
        self,
        sample_manifest: Manifest,
        isolated_rate_limiter: ASAPRateLimiter | None,
        method: str,
        path: str,
        json_body: dict[str, Any] | None,
    ) -> None:
        app, _, _, _ = _setup(sample_manifest, isolated_rate_limiter)
        if hasattr(app.state, "identity_limiter"):
            delattr(app.state, "identity_limiter")
        client = TestClient(app)

        response = client.get(path) if method == "GET" else client.post(path, json=json_body)

        assert response.status_code == 503
        assert _IDENTITY_LIMITER_503_DETAIL in response.json()["detail"]
