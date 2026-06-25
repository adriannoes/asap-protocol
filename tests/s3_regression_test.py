"""Sprint S3 regression guards for security-critical behaviors introduced by the
v2.5.1 thermo-nuclear patch.

Each test pins a behavior that a prior PR (S0 #237, S2 #240) flagged as a
landmine or that the S3 refactor newly introduced, so a future refactor cannot
silently regress it:

* ``test_oauth2_http_and_ws_share_one_jwks_validator`` — the S0 #237 deferred
  landmine: two ``OAuth2Middleware`` instances (HTTP stack + WS ``app.state``)
  must share ONE ``JWKSValidator`` so their JWKS caches cannot diverge.
* ``test_jwt_verify_result_capabilities_accessor_edge_cases`` — the additive
  ``JwtVerifyResult.capabilities`` accessor (S3 4.1) must return ``[]`` for
  absent/non-list claims and a filtered ``list[str]`` otherwise.
* ``test_adapters_mcp_shim_identity_with_mcp_auth`` — the S3 4.2 fold's
  deprecation shim must re-export the SAME objects as ``asap.mcp.auth``
  (``is`` identity), so the public surface did not fork.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from asap.auth import OAuth2Config
from asap.auth.agent_jwt import JwtVerifyResult
from asap.auth.middleware import OAuth2Middleware
from asap.models.entities import Capability, Endpoint, Manifest, Skill


def _oauth2_only_manifest() -> Manifest:
    """Manifest with no ``auth`` block — OAuth2 is the sole auth path."""
    return Manifest(
        id="urn:asap:agent:s3-shared-jwks",
        name="S3 Shared JWKS Server",
        version="1.0.0",
        description="OAuth2-only server asserting one shared JWKSValidator",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


def test_oauth2_http_and_ws_share_one_jwks_validator() -> None:
    """S0 #237 deferred landmine: HTTP stack + WS ``app.state`` share ONE validator.

    ``_wire_middleware`` constructs a single ``shared_validator`` and passes it
    via ``validator=`` to BOTH the ``app.state.oauth2_middleware`` instance
    (read by the WS path) and the ``add_middleware(OAuth2Middleware, ...)``
    stack instance (HTTP). If a future refactor re-introduces two independent
    caches, the WS accept-time validation and the HTTP per-request validation
    can disagree on key-set freshness — the exact B4/C-2 security property S0
    closed. This test fails the moment the two instances stop sharing.
    """
    from asap.transport.server import create_app

    app = create_app(
        _oauth2_only_manifest(),
        oauth2_config=OAuth2Config(
            jwks_uri="https://issuer.example/.well-known/jwks.json",
            required_scope="asap:read",
        ),
    )
    # Force the middleware stack to materialize so user_middleware is populated.
    _ = TestClient(app)

    ws_middleware = getattr(app.state, "oauth2_middleware", None)
    assert isinstance(ws_middleware, OAuth2Middleware), (
        "app.state.oauth2_middleware must be an OAuth2Middleware instance "
        "(the WS path reads it for accept-time enforcement)"
    )

    stack_mw = [m for m in app.user_middleware if m.cls is OAuth2Middleware]
    assert stack_mw, "OAuth2Middleware must be registered on the HTTP stack"
    stack_validator = stack_mw[0].kwargs.get("validator")
    assert stack_validator is not None, (
        "the stack OAuth2Middleware must be wired with the shared validator"
    )

    # The security invariant: ONE JWKSValidator object reachable from both paths.
    assert ws_middleware._validator is stack_validator, (
        "WS app.state instance and HTTP stack instance must share the SAME "
        "JWKSValidator object — divergent caches are the S0 #237 landmine"
    )


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        (None, []),
        ({}, []),
        ({"sub": "host-1"}, []),
        ({"capabilities": "not-a-list"}, []),
        ({"capabilities": 42}, []),
        ({"capabilities": []}, []),
        ({"capabilities": ["web_search"]}, ["web_search"]),
        ({"capabilities": ["web_search", "code_exec"]}, ["web_search", "code_exec"]),
        # Non-string entries are filtered out (defensive typing).
        ({"capabilities": ["web_search", 7, None, "code_exec"]}, ["web_search", "code_exec"]),
    ],
)
def test_jwt_verify_result_capabilities_accessor_edge_cases(
    claims: dict[str, Any] | None, expected: list[str]
) -> None:
    """``JwtVerifyResult.capabilities`` (S3 4.1) returns a typed ``list[str]``.

    Absent / non-list / mixed-type claims collapse to a filtered ``list[str]``
    so the MCP Auth Bridge grant gate reads one typed shape instead of
    re-deriving the claim with ``isinstance`` at every call site.
    """
    result = JwtVerifyResult(ok=True, claims=claims)
    assert result.capabilities == expected


def test_adapters_mcp_shim_identity_with_mcp_auth() -> None:
    """S3 4.2 fold: ``asap.adapters.mcp`` re-exports the SAME objects as ``asap.mcp.auth``.

    The deprecation shim must not fork the public surface — ``protect_server``,
    ``MCPAuthConfig``, ``ProtectedMCPServer``, and ``resolve_jwt_extractor``
    resolved through the legacy path must BE the objects in ``asap.mcp.auth``
    (``is`` identity), so a caller mixing the two import paths cannot observe
    two divergent implementations.
    """
    import asap.adapters.mcp as legacy
    import asap.mcp.auth as canonical

    assert legacy.protect_server is canonical.protect_server
    assert legacy.MCPAuthConfig is canonical.MCPAuthConfig
    assert legacy.ProtectedMCPServer is canonical.ProtectedMCPServer
    assert legacy.resolve_jwt_extractor is canonical.resolve_jwt_extractor
