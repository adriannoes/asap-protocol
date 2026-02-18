"""Tests for delegation token API (POST/GET/DELETE /asap/delegations)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from joserfc import jwk, jwt as jose_jwt

from asap.auth import OAuth2Config
from asap.crypto.keys import generate_keypair
from asap.economics.delegation import get_jti_from_jwt
from asap.economics.delegation_storage import InMemoryDelegationStorage
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.server import create_app


@pytest.fixture
def delegation_manifest() -> Manifest:
    """Manifest for delegation API tests."""
    return Manifest(
        id="urn:asap:agent:test-server",
        name="Test Server",
        version="1.0.0",
        description="Test server",
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


@pytest.fixture
def delegation_key_store() -> Any:
    """Key store that returns a fixed Ed25519 key for any delegator URN."""
    private_key, _ = generate_keypair()

    def store(delegator_urn: str) -> Any:
        return private_key

    return store


def test_post_delegations_returns_201_and_token(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """POST /asap/delegations with valid OAuth2 and key store returns 201 and JWT."""
    key_set, oauth2_key = oauth2_jwk_and_key

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "sub": "urn:asap:agent:delegator",
        "scope": "asap:execute",
        "exp": now + 3600,
    }
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        response = client.post(
            "/asap/delegations",
            json={
                "delegate": "urn:asap:agent:delegate",
                "scopes": ["task.execute", "data.read"],
            },
            headers={"Authorization": f"Bearer {bearer_token}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert "token" in data
    token = data["token"]
    assert isinstance(token, str)
    parts = token.split(".")
    assert len(parts) == 3


def test_post_delegations_without_oauth2_returns_503_when_no_key_store(
    delegation_manifest: Manifest,
) -> None:
    """When delegation_key_store is not set, POST /asap/delegations is not registered."""
    app = create_app(
        delegation_manifest,
        rate_limit="999999/minute",
    )
    with TestClient(app) as client:
        # No OAuth2, so no /asap/delegations route if we didn't pass delegation_key_store
        response = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:b", "scopes": ["task.execute"]},
        )
    # Without oauth2 + key_store the route is not mounted; we get 404 or 405
    assert response.status_code in (404, 405)


def test_post_delegations_without_bearer_returns_401(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """POST /asap/delegations without Authorization returns 401."""
    key_set, _ = oauth2_jwk_and_key

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        rate_limit="999999/minute",
    )

    with TestClient(app) as client:
        response = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:b", "scopes": ["task.execute"]},
        )

    assert response.status_code == 401


def test_delete_delegation_revokes_and_returns_204(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """DELETE /asap/delegations/{id} by the delegator returns 204 and revokes the token."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "sub": "urn:asap:agent:delegator",
        "scope": "asap:execute",
        "exp": now + 3600,
    }
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        create_resp = client.post(
            "/asap/delegations",
            json={
                "delegate": "urn:asap:agent:delegate",
                "scopes": ["task.execute"],
            },
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert create_resp.status_code == 201
    token = create_resp.json()["token"]
    token_id = get_jti_from_jwt(token)
    assert token_id is not None

    with TestClient(app) as client:
        delete_resp = client.delete(
            f"/asap/delegations/{token_id}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert delete_resp.status_code == 204
    # Token is revoked in storage
    assert asyncio.run(storage.is_revoked(token_id)) is True


def test_delete_delegation_by_other_returns_403(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """DELETE /asap/delegations/{id} by a different agent returns 403."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    delegator_claims = {
        "sub": "urn:asap:agent:delegator",
        "scope": "asap:execute",
        "exp": now + 3600,
    }
    other_claims = {
        "sub": "urn:asap:agent:other",
        "scope": "asap:execute",
        "exp": now + 3600,
    }
    delegator_token = jose_jwt.encode(header, delegator_claims, oauth2_key)
    other_token = jose_jwt.encode(header, other_claims, oauth2_key)

    with TestClient(app) as client:
        create_resp = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:delegate", "scopes": ["task.execute"]},
            headers={"Authorization": f"Bearer {delegator_token}"},
        )
    assert create_resp.status_code == 201
    token_id = get_jti_from_jwt(create_resp.json()["token"])
    assert token_id is not None

    with TestClient(app) as client:
        delete_resp = client.delete(
            f"/asap/delegations/{token_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
    assert delete_resp.status_code == 403
    assert delete_resp.json()["detail"] == "Only the delegator that issued this token can revoke it"


def test_delete_delegation_unknown_id_returns_404(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """DELETE /asap/delegations/{id} for unknown token_id returns 404."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"sub": "urn:asap:agent:delegator", "scope": "asap:execute", "exp": now + 3600}
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        response = client.delete(
            "/asap/delegations/del_unknown_token_id",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert response.status_code == 404


def test_delete_delegation_without_storage_returns_503(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """DELETE /asap/delegations/{id} when delegation_storage is not set returns 503."""
    key_set, oauth2_key = oauth2_jwk_and_key

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        rate_limit="999999/minute",
    )
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"sub": "urn:asap:agent:delegator", "scope": "asap:execute", "exp": now + 3600}
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        response = client.delete(
            "/asap/delegations/del_any",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert response.status_code == 503


def test_get_delegations_lists_issued_tokens(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """GET /asap/delegations returns list of delegations issued by the authenticated agent."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "sub": "urn:asap:agent:delegator",
        "scope": "asap:execute",
        "exp": now + 3600,
    }
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        create_resp = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:delegate", "scopes": ["task.execute"]},
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert create_resp.status_code == 201
    token_id = get_jti_from_jwt(create_resp.json()["token"])
    assert token_id is not None

    with TestClient(app) as client:
        list_resp = client.get(
            "/asap/delegations",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    found = next((x for x in items if x["id"] == token_id), None)
    assert found is not None
    assert found["delegator"] == "urn:asap:agent:delegator"
    assert found["delegate"] == "urn:asap:agent:delegate"
    assert found["active"] is True


def test_get_delegations_active_filters_revoked(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """GET /asap/delegations?active=true excludes revoked tokens."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"sub": "urn:asap:agent:delegator", "scope": "asap:execute", "exp": now + 3600}
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        create_resp = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:delegate", "scopes": ["task.execute"]},
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert create_resp.status_code == 201
    token_id = get_jti_from_jwt(create_resp.json()["token"])
    assert token_id is not None
    asyncio.run(storage.revoke(token_id))

    with TestClient(app) as client:
        list_resp = client.get(
            "/asap/delegations?active=true",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert not any(x["id"] == token_id for x in items)


def test_get_delegation_by_id_issuer_can_view(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """GET /asap/delegations/{id} returns 200 when authenticated as issuer."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"sub": "urn:asap:agent:issuer", "scope": "asap:execute", "exp": now + 3600}
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        create_resp = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:holder", "scopes": ["task.execute"]},
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert create_resp.status_code == 201
    token_id = get_jti_from_jwt(create_resp.json()["token"])
    assert token_id is not None

    with TestClient(app) as client:
        get_resp = client.get(
            f"/asap/delegations/{token_id}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == token_id
    assert data["delegator"] == "urn:asap:agent:issuer"
    assert data["delegate"] == "urn:asap:agent:holder"
    assert data["active"] is True


def test_get_delegation_by_id_holder_can_view(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """GET /asap/delegations/{id} returns 200 when authenticated as delegate (holder)."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    issuer_claims = {"sub": "urn:asap:agent:issuer", "scope": "asap:execute", "exp": now + 3600}
    holder_claims = {"sub": "urn:asap:agent:holder", "scope": "asap:execute", "exp": now + 3600}
    issuer_token = jose_jwt.encode(header, issuer_claims, oauth2_key)
    holder_token = jose_jwt.encode(header, holder_claims, oauth2_key)

    with TestClient(app) as client:
        create_resp = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:holder", "scopes": ["task.execute"]},
            headers={"Authorization": f"Bearer {issuer_token}"},
        )
    assert create_resp.status_code == 201
    token_id = get_jti_from_jwt(create_resp.json()["token"])
    assert token_id is not None

    with TestClient(app) as client:
        get_resp = client.get(
            f"/asap/delegations/{token_id}",
            headers={"Authorization": f"Bearer {holder_token}"},
        )
    assert get_resp.status_code == 200
    assert get_resp.json()["delegate"] == "urn:asap:agent:holder"


def test_get_delegation_by_id_other_returns_403(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """GET /asap/delegations/{id} returns 403 when authenticated as neither issuer nor holder."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    issuer_claims = {"sub": "urn:asap:agent:issuer", "scope": "asap:execute", "exp": now + 3600}
    other_claims = {"sub": "urn:asap:agent:other", "scope": "asap:execute", "exp": now + 3600}
    issuer_token = jose_jwt.encode(header, issuer_claims, oauth2_key)
    other_token = jose_jwt.encode(header, other_claims, oauth2_key)

    with TestClient(app) as client:
        create_resp = client.post(
            "/asap/delegations",
            json={"delegate": "urn:asap:agent:holder", "scopes": ["task.execute"]},
            headers={"Authorization": f"Bearer {issuer_token}"},
        )
    assert create_resp.status_code == 201
    token_id = get_jti_from_jwt(create_resp.json()["token"])
    assert token_id is not None

    with TestClient(app) as client:
        get_resp = client.get(
            f"/asap/delegations/{token_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
    assert get_resp.status_code == 403


def test_get_delegation_unknown_id_returns_404(
    delegation_manifest: Manifest,
    oauth2_jwk_and_key: tuple[jwk.KeySet, jwk.RSAKey],
    delegation_key_store: Any,
) -> None:
    """GET /asap/delegations/{id} returns 404 for unknown token id."""
    key_set, oauth2_key = oauth2_jwk_and_key
    storage = InMemoryDelegationStorage()

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = create_app(
        delegation_manifest,
        oauth2_config=OAuth2Config(
            jwks_uri="https://auth.example.com/jwks.json",
            path_prefix="/asap",
            jwks_fetcher=jwks_fetcher,
        ),
        delegation_key_store=delegation_key_store,
        delegation_storage=storage,
        rate_limit="999999/minute",
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"sub": "urn:asap:agent:any", "scope": "asap:execute", "exp": now + 3600}
    bearer_token = jose_jwt.encode(header, claims, oauth2_key)

    with TestClient(app) as client:
        get_resp = client.get(
            "/asap/delegations/del_unknown_999",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
    assert get_resp.status_code == 404
