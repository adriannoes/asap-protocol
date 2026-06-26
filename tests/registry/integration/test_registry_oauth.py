"""OAuth scope enforcement for POST /registry/agents without test bypass."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi import FastAPI
from joserfc import jwk, jwt as jose_jwt
from starlette.testclient import TestClient

from asap.auth.middleware import OAuth2Middleware
from asap.discovery.registry import RegistryEntry
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.registry.auto_registration import (
    REGISTRY_REGISTER_SCOPE,
    AutoRegistrationConfig,
    create_auto_registration_router,
)
from asap.registry.bot_pr import BotPRResult
from asap.testing.compliance import CheckResult, ComplianceReport
from asap.transport.rate_limit import create_test_limiter, registration_token_key


@pytest.fixture
def manifest_https() -> Manifest:
    """Manifest whose ASAP endpoint maps to a public HTTPS harness base URL."""
    return Manifest(
        id="urn:asap:agent:ci:oauth-reg-test",
        name="OAuth Reg Test",
        version="1.0.0",
        description="OAuth registry integration fixture",
        capabilities=Capability(
            asap_version="2.2.0",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://example.com/asap"),
    )


def _passing_report() -> ComplianceReport:
    from datetime import datetime, timezone

    return ComplianceReport(
        timestamp=datetime.now(timezone.utc),
        categories_run=["sanity"],
        checks=[
            CheckResult(name="dummy", category="test", passed=True, message="ok"),
        ],
        score=1.0,
        summary="1/1 checks passed (100%)",
    )


@pytest.fixture
def registry_oauth_app(
    manifest_https: Manifest,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[FastAPI, jwk.RSAKey]:
    """Registry router behind real OAuth2Middleware (no oauth_claims_dependency bypass)."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    key_set = jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    async def _fake_fetch(_client: object, _url: str) -> Manifest:
        return manifest_https

    async def _fake_pr(_entry: RegistryEntry, _url: str) -> BotPRResult:
        return BotPRResult(pr_url="https://github.com/o/r/pull/1", branch_name="auto-reg/x")

    monkeypatch.setattr(
        "asap.registry.auto_registration.fetch_manifest_at_url",
        _fake_fetch,
    )

    cfg = AutoRegistrationConfig(
        run_compliance=lambda _base: _passing_report(),
        open_pull_request=_fake_pr,
    )
    app = FastAPI()
    app.state.registration_limiter = create_test_limiter(
        ["100000/hour"],
        key_func=registration_token_key,
    )
    app.state.registration_receipt_cache = {}
    app.include_router(create_auto_registration_router(cfg))
    app.add_middleware(
        OAuth2Middleware,
        jwks_uri="https://auth.example.com/jwks.json",
        path_prefix="/registry",
        jwks_fetcher=jwks_fetcher,
    )
    return app, key


def _encode_token(key: jwk.RSAKey, *, scope: str, exp_offset: int = 3600) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims: dict[str, Any] = {
        "sub": "urn:asap:agent:oauth-caller",
        "scope": scope,
        "exp": now + exp_offset,
    }
    return jose_jwt.encode(header, claims, key)


def test_registry_agents_401_without_bearer(registry_oauth_app: tuple[FastAPI, jwk.RSAKey]) -> None:
    """POST /registry/agents requires authentication when OAuth middleware is active."""
    app, _ = registry_oauth_app
    with TestClient(app) as client:
        response = client.post(
            "/registry/agents",
            json={"manifest_url": "https://example.com/m.json"},
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_registry_agents_403_wrong_scope(registry_oauth_app: tuple[FastAPI, jwk.RSAKey]) -> None:
    """POST /registry/agents rejects tokens that lack asap:registry scope."""
    app, key = registry_oauth_app
    token = _encode_token(key, scope="asap:read asap:execute")
    with TestClient(app) as client:
        response = client.post(
            "/registry/agents",
            json={"manifest_url": "https://example.com/m.json"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient scope"


def test_registry_agents_200_with_registry_scope(
    registry_oauth_app: tuple[FastAPI, jwk.RSAKey],
) -> None:
    """POST /registry/agents succeeds when the bearer token includes asap:registry."""
    app, key = registry_oauth_app
    token = _encode_token(key, scope=REGISTRY_REGISTER_SCOPE)
    with TestClient(app) as client:
        response = client.post(
            "/registry/agents",
            json={"manifest_url": "https://example.com/m.json"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["urn"] == "urn:asap:agent:ci:oauth-reg-test"
    assert body["status"] == "queued"
