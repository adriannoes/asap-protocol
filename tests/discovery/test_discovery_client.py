"""Integration tests for ASAPClient manifest discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from asap.discovery.wellknown import WELLKNOWN_MANIFEST_PATH
from asap.transport.client import ASAPClient, ASAPConnectionError, ASAPTimeoutError
from asap.transport.server import create_app

if TYPE_CHECKING:
    from asap.models.entities import Manifest


VALID_MANIFEST_PAYLOAD = {
    "id": "urn:asap:agent:discovery-test",
    "name": "Discovery Test Agent",
    "version": "1.0.0",
    "description": "Agent for discovery client tests",
    "capabilities": {
        "asap_version": "0.1",
        "skills": [{"id": "test_skill", "description": "Test skill"}],
        "state_persistence": False,
    },
    "endpoints": {"asap": "https://example.com/asap"},
}


class TestDiscoverFromServer:
    """Client discovers manifest from (mocked) server."""

    @pytest.mark.asyncio
    async def test_client_discovers_manifest_from_server(self) -> None:
        """ASAPClient.discover(base_url) fetches and parses manifest from well-known URL."""
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if request.method == "GET" and request.url.path.endswith(WELLKNOWN_MANIFEST_PATH):
                return httpx.Response(status_code=200, json=VALID_MANIFEST_PAYLOAD)
            return httpx.Response(status_code=404, content=b"Not Found")

        async with ASAPClient(
            "https://other.example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            manifest = await client.discover("https://agent.example.com")

        assert call_count == 1
        assert manifest.id == "urn:asap:agent:discovery-test"
        assert manifest.name == "Discovery Test Agent"
        assert manifest.capabilities.asap_version == "0.1"
        assert any(s.id == "test_skill" for s in manifest.capabilities.skills)

    @pytest.mark.asyncio
    async def test_discover_requires_connected_client(self) -> None:
        """discover() raises ASAPConnectionError when client is not connected."""
        client = ASAPClient("https://example.com")
        assert not client.is_connected

        with pytest.raises(ASAPConnectionError, match="not connected"):
            await client.discover("https://agent.example.com")


class TestDiscoverCache:
    """Cache is used on subsequent discover() calls."""

    @pytest.mark.asyncio
    async def test_cache_used_on_second_request(self) -> None:
        """Second discover() for same base_url returns cached manifest without HTTP call."""
        call_count = 0

        def mock_transport(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(status_code=200, json=VALID_MANIFEST_PAYLOAD)

        async with ASAPClient(
            "https://gateway.example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            manifest1 = await client.discover("https://agent.example.com")
            manifest2 = await client.discover("https://agent.example.com")

        assert call_count == 1
        assert manifest1.id == manifest2.id
        assert manifest1.name == manifest2.name


class TestDiscoverSignedManifest:
    """discover() must reject or unwrap signed manifest wrappers (regression guard)."""

    @staticmethod
    def _signed_manifest_json() -> dict:
        from asap.crypto.keys import generate_keypair
        from asap.crypto.signing import sign_manifest
        from asap.models.entities import Capability, Endpoint, Manifest, Skill

        manifest = Manifest(
            id="urn:asap:agent:signed-discovery",
            name="Signed Discovery Agent",
            version="1.0.0",
            description="Signed well-known manifest",
            capabilities=Capability(
                asap_version="2.1.0",
                skills=[Skill(id="assistant", description="Assistant")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="https://signed.example/asap"),
        )
        private_key, _public_key = generate_keypair()
        signed = sign_manifest(manifest, private_key)
        return signed.model_dump(mode="json")

    @pytest.mark.asyncio
    async def test_discover_signed_manifest_wrapper_raises_validation_error(self) -> None:
        """Signed {manifest, signature} wrapper fails discover() schema validation today."""
        from asap.discovery.validation import ManifestValidationError

        payload = self._signed_manifest_json()

        def mock_transport(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and request.url.path.endswith(WELLKNOWN_MANIFEST_PATH):
                return httpx.Response(status_code=200, json=payload)
            return httpx.Response(status_code=404, content=b"Not Found")

        async with ASAPClient(
            "https://gateway.example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            with pytest.raises(ManifestValidationError):
                await client.discover("https://signed.example.com")


class TestInvalidManifest:
    """Invalid manifest raises clear, descriptive error."""

    @pytest.mark.asyncio
    async def test_invalid_manifest_raises_descriptive_error(self) -> None:
        """Invalid manifest (missing required fields or wrong schema) raises ManifestValidationError."""
        from asap.discovery.validation import ManifestValidationError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"foo": "bar"})

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            with pytest.raises(ManifestValidationError) as exc_info:
                await client.discover("https://bad-agent.example.com")

        msg = str(exc_info.value)
        assert "manifest" in msg.lower() or "schema" in msg.lower() or "required" in msg.lower()
        assert exc_info.value.field is not None or "schema" in msg.lower()

    @pytest.mark.asyncio
    async def test_missing_required_fields_raises_clear_error(self) -> None:
        """Manifest with only id (missing name, version, etc.) raises ManifestValidationError."""
        from asap.discovery.validation import ManifestValidationError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"id": "urn:asap:agent:incomplete"})

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            with pytest.raises(ManifestValidationError, match="required|missing|schema"):
                await client.discover("https://incomplete.example.com")


class TestNetworkErrors:
    """Network errors are handled gracefully."""

    @pytest.mark.asyncio
    async def test_timeout_raises_asap_timeout_error(self) -> None:
        """Request timeout raises ASAPTimeoutError."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Timeout fetching manifest")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            with pytest.raises(ASAPTimeoutError):
                await client.discover("https://slow-agent.example.com")

    @pytest.mark.asyncio
    async def test_connect_error_raises_asap_connection_error(self) -> None:
        """Connection error raises ASAPConnectionError."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            with pytest.raises(ASAPConnectionError):
                await client.discover("https://down-agent.example.com")

    @pytest.mark.asyncio
    async def test_http_error_raises_asap_connection_error(self) -> None:
        """HTTP 4xx/5xx on manifest URL raises ASAPConnectionError."""

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=404, content=b"Not Found")

        async with ASAPClient(
            "https://example.com",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            with pytest.raises(ASAPConnectionError, match="404"):
                await client.discover("https://missing.example.com")


class TestDiscoverAgainstRealApp:
    """Integration: client discovers manifest from app via ASGITransport."""

    @pytest.mark.asyncio
    async def test_discover_from_app_returns_manifest(self, sample_manifest: "Manifest") -> None:
        """ASAPClient.discover() against create_app() returns server manifest."""
        app = create_app(sample_manifest, rate_limit="999999/minute")
        transport = httpx.ASGITransport(app=app)
        async with ASAPClient(
            "http://testserver",
            transport=transport,
            require_https=False,
        ) as client:
            manifest = await client.discover("http://testserver")

        assert manifest.id == sample_manifest.id
        assert manifest.name == sample_manifest.name
        assert manifest.capabilities.asap_version == sample_manifest.capabilities.asap_version
        assert len(manifest.capabilities.skills) == len(sample_manifest.capabilities.skills)
