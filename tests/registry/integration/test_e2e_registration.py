"""End-to-end style tests for auto-registration (mocked GitHub + mirror)."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.testclient import TestClient

from asap.auth.middleware import OAuth2Claims
from asap.discovery.registry import DEFAULT_REGISTRY_URL, LiteRegistry, RegistryEntry
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.registry.auto_registration import AutoRegistrationConfig, create_auto_registration_router
from asap.registry.bot_pr import BotPRResult
from asap.testing.compliance import CheckResult, ComplianceReport
from asap.transport.rate_limit import create_test_limiter, registration_token_key


async def _oauth(request: Request) -> OAuth2Claims:
    return OAuth2Claims(sub="urn:asap:agent:e2e", scope=["asap:registry"], exp=9999999999)


@pytest.fixture
def e2e_manifest() -> Manifest:
    return Manifest(
        id="urn:asap:agent:e2e:mirror-test",
        name="Mirror Test",
        version="1.0.0",
        description="E2E mirror polling fixture",
        capabilities=Capability(
            asap_version="2.2.0",
            skills=[Skill(id="echo", description="e")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://example.com/asap"),
    )


def test_e2e_registration_mocked_pr_and_mirror_poll(
    e2e_manifest: Manifest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Submit registration, assert PR hook ran, then poll mirror until URN appears (mocked)."""
    harness_calls: list[str] = []

    async def _fetch(_client: object, url: str) -> Manifest:
        assert "example.com" in url
        return e2e_manifest

    async def _harness(base_url: str) -> ComplianceReport:
        harness_calls.append(base_url)
        return ComplianceReport(
            timestamp=datetime.now(timezone.utc),
            categories_run=["e2e"],
            checks=[CheckResult(name="ok", category="t", passed=True, message="ok")],
            score=1.0,
            summary="pass",
        )

    async def _pr(entry: RegistryEntry, manifest_url: str) -> BotPRResult:
        assert entry.id == e2e_manifest.id
        return BotPRResult(
            pr_url="https://github.com/asap-protocol/asap-protocol/pull/999",
            branch_name="auto-reg/e2e",
        )

    monkeypatch.setattr(
        "asap.registry.auto_registration.fetch_manifest_at_url",
        _fetch,
    )

    cfg = AutoRegistrationConfig(
        oauth_claims_dependency=_oauth,
        run_compliance=_harness,
        open_pull_request=_pr,
    )
    app = FastAPI()
    app.state.registration_limiter = create_test_limiter(
        ["100000/hour"],
        key_func=registration_token_key,
    )
    app.state.registration_receipt_cache = {}
    app.include_router(create_auto_registration_router(cfg))

    client = TestClient(app)
    manifest_url = "https://example.com/.well-known/asap/e2e.json"
    reg = client.post(
        "/registry/agents",
        json={"manifest_url": manifest_url},
        headers={"Authorization": "Bearer e2e-token"},
    )
    assert reg.status_code == 200
    payload = reg.json()
    assert payload["urn"] == e2e_manifest.id
    assert payload["harness_score"] == 1.0
    assert "pull/999" in (payload.get("pr_url") or "")
    assert harness_calls == ["https://example.com"]

    seen = {"attempts": 0}

    def mirror_handler(request: httpx.Request) -> httpx.Response:
        seen["attempts"] += 1
        if seen["attempts"] < 3:
            lr = LiteRegistry(
                version="1.0",
                updated_at=datetime.now(timezone.utc),
                agents=[],
            )
        else:
            lr = LiteRegistry(
                version="1.0",
                updated_at=datetime.now(timezone.utc),
                agents=[
                    RegistryEntry(
                        id=e2e_manifest.id,
                        name=e2e_manifest.name,
                        description=e2e_manifest.description,
                        endpoints={"http": "https://example.com/asap", "manifest": manifest_url},
                        skills=["echo"],
                        asap_version="2.2.0",
                    )
                ],
            )
        return httpx.Response(200, json=lr.model_dump(mode="json"))

    transport = httpx.MockTransport(mirror_handler)
    ids: list[str | None] = []
    with httpx.Client(transport=transport, timeout=httpx.Timeout(5.0)) as http_client:
        for _ in range(10):
            resp = http_client.get(DEFAULT_REGISTRY_URL)
            assert resp.status_code == 200
            data = resp.json()
            agents = data.get("agents", []) if isinstance(data, dict) else []
            ids = [a.get("id") for a in agents if isinstance(a, dict)]
            if e2e_manifest.id in ids:
                break
        assert e2e_manifest.id in ids
    assert seen["attempts"] >= 3
