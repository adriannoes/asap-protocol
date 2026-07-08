"""Opt-in OAuth2 protection for operator APIs (/usage, /sla, /audit) — #209."""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from joserfc import jwk, jwt as jose_jwt

from asap.auth import OAuth2Config
from asap.auth.middleware import DEFAULT_CUSTOM_CLAIM, OPERATOR_API_PATH_PREFIXES
from asap.economics import InMemoryMeteringStorage, InMemorySLAStorage
from asap.economics.audit import InMemoryAuditStore
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.server import create_app

_MANIFEST_ID = "urn:asap:agent:operator-api-test"


@pytest.fixture
def operator_manifest() -> Manifest:
    """Manifest used by operator API auth integration tests."""
    return Manifest(
        id=_MANIFEST_ID,
        name="Operator API Test",
        version="1.0.0",
        description="Operator API auth tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def oauth2_jwk_and_key() -> tuple[jwk.KeySet, jwk.RSAKey]:
    """RSA key and JWKS for OAuth2 token validation."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    key_set = jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})
    return key_set, key


def _bearer_token(
    oauth2_key: jwk.RSAKey,
    *,
    scope: str,
    agent_id: str | None = _MANIFEST_ID,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": "urn:asap:agent:operator",
        "scope": scope,
        "exp": now + 3600,
    }
    if agent_id is not None:
        claims[DEFAULT_CUSTOM_CLAIM] = agent_id
    return jose_jwt.encode({"alg": "RS256", "typ": "JWT"}, claims, oauth2_key)


def _protected_app(
    manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    *,
    require_operator_auth: bool = True,
) -> Any:
    key_set, _ = oauth2_jwk_and_key

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    return create_app(
        manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        metering_storage=InMemoryMeteringStorage(),
        sla_storage=InMemorySLAStorage(),
        audit_store=InMemoryAuditStore(),
        require_operator_auth=require_operator_auth,
        rate_limit="999999/minute",
    )


def test_require_operator_auth_without_oauth2_config_raises(
    operator_manifest: Manifest,
) -> None:
    """Flag True without oauth2_config must fail closed at create_app."""
    with pytest.raises(ValueError, match="require_operator_auth=True requires oauth2_config"):
        create_app(
            operator_manifest,
            metering_storage=InMemoryMeteringStorage(),
            require_operator_auth=True,
        )


def test_default_operator_apis_remain_open(
    operator_manifest: Manifest,
) -> None:
    """Default False keeps local/operator open access for GET surfaces."""
    app = create_app(
        operator_manifest,
        metering_storage=InMemoryMeteringStorage(),
        sla_storage=InMemorySLAStorage(),
        audit_store=InMemoryAuditStore(),
        rate_limit="999999/minute",
    )
    with TestClient(app) as client:
        assert client.get("/usage").status_code == 200
        assert client.get("/sla").status_code == 200
        assert client.get("/audit").status_code == 200


@pytest.mark.parametrize("path", ["/usage", "/sla", "/audit"])
def test_operator_apis_reject_missing_bearer_when_protected(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    path: str,
) -> None:
    """Protected operator paths return 401 without Authorization."""
    app = _protected_app(operator_manifest, oauth2_jwk_and_key)
    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


@pytest.mark.parametrize("path", ["/usage", "/sla", "/audit"])
def test_operator_apis_reject_insufficient_scope(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    path: str,
) -> None:
    """JWT without asap:admin yields 403 on operator APIs."""
    _, oauth2_key = oauth2_jwk_and_key
    app = _protected_app(operator_manifest, oauth2_jwk_and_key)
    token = _bearer_token(oauth2_key, scope="asap:execute")
    with TestClient(app) as client:
        response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient scope"}


@pytest.mark.parametrize("path", ["/usage", "/sla", "/audit"])
def test_operator_apis_accept_admin_scope(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    path: str,
) -> None:
    """JWT with asap:admin allows GET on all operator APIs."""
    _, oauth2_key = oauth2_jwk_and_key
    app = _protected_app(operator_manifest, oauth2_jwk_and_key)
    token = _bearer_token(oauth2_key, scope="asap:admin")
    with TestClient(app) as client:
        response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_usage_purge_requires_admin_scope(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
) -> None:
    """POST /usage/purge (write) is protected when require_operator_auth is True."""
    _, oauth2_key = oauth2_jwk_and_key
    app = _protected_app(operator_manifest, oauth2_jwk_and_key)
    admin = _bearer_token(oauth2_key, scope="asap:admin")
    execute_only = _bearer_token(oauth2_key, scope="asap:execute")
    with TestClient(app) as client:
        denied = client.post(
            "/usage/purge",
            headers={"Authorization": f"Bearer {execute_only}"},
        )
        allowed = client.post(
            "/usage/purge",
            headers={"Authorization": f"Bearer {admin}"},
        )
    assert denied.status_code == 403
    assert allowed.status_code == 200


def test_operator_auth_does_not_cover_health(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
) -> None:
    """Health remains open; operator prefixes stay narrow (#209)."""
    app = _protected_app(operator_manifest, oauth2_jwk_and_key)
    assert OPERATOR_API_PATH_PREFIXES == ("/usage", "/sla", "/audit")
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


@pytest.mark.parametrize("path", ["/usage", "/sla", "/audit"])
def test_operator_apis_reject_identity_mismatch(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    path: str,
) -> None:
    """Admin token without matching identity binding gets 403 (same rule as /asap)."""
    _, oauth2_key = oauth2_jwk_and_key
    app = _protected_app(operator_manifest, oauth2_jwk_and_key)
    token = _bearer_token(oauth2_key, scope="asap:admin", agent_id="urn:asap:agent:someone-else")
    with TestClient(app) as client:
        response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_operator_auth_does_not_break_jsonrpc(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
) -> None:
    """With the flag on, /asap still validates via path_prefix (not operator prefixes).

    A bare POST /asap without a Bearer token is rejected by the existing OAuth2
    middleware (401), proving operator wiring did not disable core-route auth.
    """
    app = _protected_app(operator_manifest, oauth2_jwk_and_key)
    with TestClient(app) as client:
        response = client.post("/asap", json={"jsonrpc": "2.0", "method": "asap.send", "id": "1"})
    assert response.status_code == 401


def test_global_required_scope_does_not_compound_with_operator_scope(
    operator_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
) -> None:
    """A global OAuth2Config.required_scope must not gate operator APIs (#209 M1).

    Operator routes enforce only ``asap:admin`` via Depends; the global
    ``required_scope`` (here ``asap:register``) applies to ``/asap`` paths only, so
    an admin-only token still passes on ``/usage``.
    """
    key_set, oauth2_key = oauth2_jwk_and_key

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        operator_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            required_scope="asap:register",
            jwks_fetcher=jwks_fetcher,
        ),
        metering_storage=InMemoryMeteringStorage(),
        require_operator_auth=True,
        rate_limit="999999/minute",
    )
    admin_only = _bearer_token(oauth2_key, scope="asap:admin")
    with TestClient(app) as client:
        response = client.get("/usage", headers={"Authorization": f"Bearer {admin_only}"})
    assert response.status_code == 200
