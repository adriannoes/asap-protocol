"""Tests for handshake validator against known-good and known-bad agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from asap_compliance.config import ComplianceConfig
from asap_compliance.validators.handshake import (
    CheckResult,
    HandshakeResult,
    validate_handshake,
    validate_handshake_async,
)

if TYPE_CHECKING:
    from fastapi import FastAPI


class TestHandshakeKnownGood:
    """Tests against a known-good ASAP agent."""

    @pytest.mark.asyncio
    async def test_validate_handshake_passes_against_good_agent(
        self, good_agent_app: "FastAPI"
    ) -> None:
        """Handshake validation passes when agent is compliant."""
        transport = httpx.ASGITransport(app=good_agent_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            config = ComplianceConfig(
                agent_url="http://testserver",
                timeout_seconds=5.0,
            )
            result = await validate_handshake_async(config, client=client)

        assert result.passed
        assert result.connection_ok
        assert result.manifest_ok
        assert result.version_ok
        assert all(c.passed for c in result.checks)

    @pytest.mark.asyncio
    async def test_connection_checks_pass(
        self,
        compliance_config_with_transport: tuple[ComplianceConfig, httpx.AsyncClient],
    ) -> None:
        """Health endpoint returns 200 and application/json."""
        config, client = compliance_config_with_transport
        result = await validate_handshake_async(config, client=client)
        conn_checks = [c for c in result.checks if "health" in c.name]
        assert len(conn_checks) >= 2
        assert all(c.passed for c in conn_checks)

    @pytest.mark.asyncio
    async def test_manifest_checks_pass(
        self,
        compliance_config_with_transport: tuple[ComplianceConfig, httpx.AsyncClient],
    ) -> None:
        """Manifest endpoint exists and schema is valid."""
        config, client = compliance_config_with_transport
        result = await validate_handshake_async(config, client=client)
        manifest_checks = [c for c in result.checks if "manifest" in c.name]
        assert len(manifest_checks) >= 2
        assert all(c.passed for c in manifest_checks)

    @pytest.mark.asyncio
    async def test_version_checks_pass(
        self,
        compliance_config_with_transport: tuple[ComplianceConfig, httpx.AsyncClient],
    ) -> None:
        """Agent reports asap_version and is compatible."""
        config, client = compliance_config_with_transport
        result = await validate_handshake_async(config, client=client)
        version_checks = [c for c in result.checks if "version" in c.name]
        assert len(version_checks) >= 1
        assert all(c.passed for c in version_checks)


class TestHandshakeKnownBad:
    """Tests that handshake validator detects non-compliant agents."""

    def test_fails_when_agent_unreachable(self) -> None:
        """Validation fails when agent URL is unreachable."""
        config = ComplianceConfig(
            agent_url="http://localhost:99999",
            timeout_seconds=0.5,
        )
        result = validate_handshake(config)
        assert not result.passed
        assert not result.connection_ok
        failed = [c for c in result.checks if not c.passed]
        assert len(failed) >= 1

    @pytest.mark.asyncio
    async def test_fails_on_wrong_health_content_type(self) -> None:
        """Validation fails when health returns wrong content-type."""
        health_json: dict[str, object] = {
            "status": "healthy",
            "agent_id": "urn:asap:agent:bad",
            "version": "1.0.0",
            "asap_version": "0.1",
            "uptime_seconds": 0,
        }
        manifest_json = {
            "id": "urn:asap:agent:bad",
            "name": "Bad",
            "version": "1.0.0",
            "description": "x",
            "capabilities": {
                "asap_version": "0.1",
                "skills": [{"id": "x", "description": "x"}],
                "state_persistence": False,
            },
            "endpoints": {"asap": "http://localhost:8000/asap"},
        }

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                url = str(request.url)
                if "/.well-known/asap/health" in url:
                    return httpx.Response(
                        200,
                        headers={"content-type": "text/plain; charset=utf-8"},
                        json=health_json,
                    )
                if "/.well-known/asap/manifest.json" in url:
                    return httpx.Response(
                        200,
                        headers={"content-type": "application/json"},
                        json=manifest_json,
                    )
                return httpx.Response(404)

        transport = MockTransport()
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            config = ComplianceConfig(
                agent_url="http://testserver",
                timeout_seconds=5.0,
            )
            result = await validate_handshake_async(config, client=client)

        content_type_check = next(
            (c for c in result.checks if c.name == "health_content_type"), None
        )
        assert content_type_check is not None
        assert not content_type_check.passed

    @pytest.mark.asyncio
    async def test_fails_on_invalid_manifest_schema(self) -> None:
        """Validation fails when manifest returns invalid JSON schema."""
        invalid_manifest = {"id": "urn:asap:agent:bad", "name": "Bad"}

        class MockTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                url = str(request.url)
                if "/.well-known/asap/health" in url:
                    return httpx.Response(
                        200,
                        headers={"content-type": "application/json"},
                        json={
                            "status": "healthy",
                            "agent_id": "urn:asap:agent:bad",
                            "version": "1.0.0",
                            "asap_version": "0.1",
                            "uptime_seconds": 0,
                        },
                    )
                if "/.well-known/asap/manifest.json" in url:
                    return httpx.Response(
                        200,
                        headers={"content-type": "application/json"},
                        json=invalid_manifest,
                    )
                return httpx.Response(404)

        transport = MockTransport()
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            config = ComplianceConfig(
                agent_url="http://testserver",
                timeout_seconds=5.0,
            )
            result = await validate_handshake_async(config, client=client)

        assert not result.manifest_ok
        failed = [c for c in result.checks if not c.passed and "manifest" in c.name]
        assert len(failed) >= 1


class TestHandshakeSyncWrapper:
    """Tests for sync wrapper behavior when event loop is running."""

    @pytest.mark.asyncio
    async def test_validate_handshake_raises_when_called_from_running_loop(
        self, compliance_config_with_transport: tuple[ComplianceConfig, httpx.AsyncClient]
    ) -> None:
        """Sync validate_handshake raises RuntimeError when called from async context."""
        config, client = compliance_config_with_transport

        with pytest.raises(RuntimeError, match="Cannot call sync validate_handshake"):
            validate_handshake(config, client=client)


class TestHandshakeResult:
    """Tests for HandshakeResult model."""

    def test_passed_true_when_all_ok(self) -> None:
        """passed is True when all categories pass."""
        result = HandshakeResult(
            connection_ok=True,
            manifest_ok=True,
            version_ok=True,
            checks=[CheckResult("x", True, "ok")],
        )
        assert result.passed

    def test_passed_false_when_any_fails(self) -> None:
        """passed is False when any category fails."""
        result = HandshakeResult(
            connection_ok=True,
            manifest_ok=False,
            version_ok=True,
            checks=[],
        )
        assert not result.passed
