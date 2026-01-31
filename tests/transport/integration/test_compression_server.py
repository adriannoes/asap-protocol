"""Integration tests for server-side decompression.

Tests cover:
- Decompression of gzip-encoded requests
- Decompression of brotli-encoded requests (when available)
- Error handling for invalid compressed data
- Error handling for unsupported encodings
- Decompression bomb prevention
"""

import gzip
import json
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.transport.compression import is_brotli_available
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

if TYPE_CHECKING:
    pass


@pytest.fixture
def test_manifest() -> Manifest:
    """Create a test manifest."""
    return Manifest(
        id="urn:asap:agent:compression-test",
        name="Compression Test Agent",
        version="1.0.0",
        description="Test agent for compression",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo back input")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def test_registry() -> HandlerRegistry:
    """Create a test handler registry."""
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    return registry


@pytest.fixture
def test_app(test_manifest: Manifest, test_registry: HandlerRegistry) -> TestClient:
    """Create a test client for the ASAP server."""
    app = create_app(test_manifest, test_registry)
    return TestClient(app)


@pytest.fixture
def sample_envelope() -> Envelope:
    """Create a sample envelope for testing."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:compression-test",
        payload_type="task.request",
        payload={
            "conversation_id": "conv_001",
            "skill_id": "echo",
            "input": {"message": "Hello, compressed world!"},
        },
    )


@pytest.fixture
def sample_jsonrpc_request(sample_envelope: Envelope) -> dict[str, Any]:
    """Create a sample JSON-RPC request."""
    return {
        "jsonrpc": "2.0",
        "method": "asap.send",
        "params": {"envelope": sample_envelope.model_dump(mode="json")},
        "id": "test-request-001",
    }


class TestGzipDecompression:
    """Tests for gzip decompression on server."""

    def test_gzip_compressed_request_succeeds(
        self,
        test_app: TestClient,
        sample_jsonrpc_request: dict[str, Any],
    ) -> None:
        """Verify server can decompress and process gzip request."""
        # Compress the request body
        body_json = json.dumps(sample_jsonrpc_request).encode("utf-8")
        compressed_body = gzip.compress(body_json)

        # Send compressed request
        response = test_app.post(
            "/asap",
            content=compressed_body,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )

        assert response.status_code == 200
        json_response = response.json()
        assert "result" in json_response
        assert "envelope" in json_response["result"]

    def test_gzip_case_insensitive_encoding(
        self,
        test_app: TestClient,
        sample_jsonrpc_request: dict[str, Any],
    ) -> None:
        """Verify Content-Encoding is case-insensitive."""
        body_json = json.dumps(sample_jsonrpc_request).encode("utf-8")
        compressed_body = gzip.compress(body_json)

        # Test uppercase
        response = test_app.post(
            "/asap",
            content=compressed_body,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "GZIP",
            },
        )

        assert response.status_code == 200

    def test_identity_encoding_passthrough(
        self,
        test_app: TestClient,
        sample_jsonrpc_request: dict[str, Any],
    ) -> None:
        """Verify identity encoding passes data unchanged."""
        body_json = json.dumps(sample_jsonrpc_request).encode("utf-8")

        response = test_app.post(
            "/asap",
            content=body_json,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "identity",
            },
        )

        assert response.status_code == 200

    def test_no_encoding_header_works(
        self,
        test_app: TestClient,
        sample_jsonrpc_request: dict[str, Any],
    ) -> None:
        """Verify requests without Content-Encoding work normally."""
        response = test_app.post(
            "/asap",
            json=sample_jsonrpc_request,
        )

        assert response.status_code == 200


class TestBrotliDecompression:
    """Tests for brotli decompression on server."""

    @pytest.mark.skipif(not is_brotli_available(), reason="brotli not installed")
    def test_brotli_compressed_request_succeeds(
        self,
        test_app: TestClient,
        sample_jsonrpc_request: dict[str, Any],
    ) -> None:
        """Verify server can decompress and process brotli request."""
        import brotli

        body_json = json.dumps(sample_jsonrpc_request).encode("utf-8")
        compressed_body = brotli.compress(body_json)

        response = test_app.post(
            "/asap",
            content=compressed_body,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "br",
            },
        )

        assert response.status_code == 200
        json_response = response.json()
        assert "result" in json_response

    @pytest.mark.skipif(is_brotli_available(), reason="brotli is installed")
    def test_brotli_unavailable_returns_error(
        self,
        test_app: TestClient,
        sample_jsonrpc_request: dict[str, Any],
    ) -> None:
        """Verify proper error when brotli is requested but unavailable."""
        body_json = json.dumps(sample_jsonrpc_request).encode("utf-8")

        response = test_app.post(
            "/asap",
            content=body_json,  # Not actually brotli compressed
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "br",
            },
        )

        # Should return 415 Unsupported Media Type or 400 Bad Request
        assert response.status_code in (400, 415)


class TestCompressionErrorHandling:
    """Tests for compression error handling."""

    def test_invalid_gzip_data_returns_error(
        self,
        test_app: TestClient,
    ) -> None:
        """Verify error on invalid gzip data."""
        response = test_app.post(
            "/asap",
            content=b"this is not gzip data",
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )

        assert response.status_code == 400
        assert "Invalid compressed data" in response.json()["detail"]

    def test_unsupported_encoding_returns_error(
        self,
        test_app: TestClient,
    ) -> None:
        """Verify error on unsupported Content-Encoding."""
        response = test_app.post(
            "/asap",
            content=b'{"test": "data"}',
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "deflate",  # Not supported
            },
        )

        assert response.status_code == 415
        assert "Unsupported Content-Encoding" in response.json()["detail"]

    def test_truncated_gzip_returns_error(
        self,
        test_app: TestClient,
        sample_jsonrpc_request: dict[str, Any],
    ) -> None:
        """Verify error on truncated gzip data."""
        body_json = json.dumps(sample_jsonrpc_request).encode("utf-8")
        compressed = gzip.compress(body_json)
        # Truncate the compressed data
        truncated = compressed[:len(compressed) // 2]

        response = test_app.post(
            "/asap",
            content=truncated,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )

        assert response.status_code == 400


class TestDecompressionBombPrevention:
    """Tests for decompression bomb prevention."""

    def test_decompressed_size_limit_enforced(
        self,
        test_manifest: Manifest,
        test_registry: HandlerRegistry,
    ) -> None:
        """Verify decompressed size limit is enforced."""
        # Create app with small max request size
        small_max_size = 1024  # 1KB
        app = create_app(test_manifest, test_registry, max_request_size=small_max_size)
        client = TestClient(app)

        # Create a request that compresses well but exceeds limit when decompressed
        # Use a large repetitive string that compresses very well
        large_payload = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": {
                    "asap_version": "0.1",
                    "sender": "urn:asap:agent:client",
                    "recipient": "urn:asap:agent:server",
                    "payload_type": "task.request",
                    "payload": {"data": "x" * 5000},  # > 1KB when decompressed
                }
            },
            "id": "bomb-test",
        }

        body_json = json.dumps(large_payload).encode("utf-8")
        # Verify the uncompressed size exceeds limit
        assert len(body_json) > small_max_size

        compressed_body = gzip.compress(body_json)
        # Verify the compressed size is under limit (compression bomb pattern)
        assert len(compressed_body) < small_max_size

        response = client.post(
            "/asap",
            content=compressed_body,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )

        # Should reject due to decompressed size exceeding limit
        assert response.status_code == 413
        assert "Decompressed request size" in response.json()["detail"]


class TestCompressionRoundTrip:
    """End-to-end tests for compression round trip."""

    def test_large_payload_compression_round_trip(
        self,
        test_app: TestClient,
    ) -> None:
        """Verify large compressed payload is processed correctly."""
        # Create a large envelope
        large_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:compression-test",
            payload_type="task.request",
            payload={
                "conversation_id": "conv_large",
                "skill_id": "echo",
                "input": {
                    "message": "Large payload test " * 100,
                    "items": [{"id": i, "value": f"item_{i}"} for i in range(50)],
                },
            },
        )

        request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": large_envelope.model_dump(mode="json")},
            "id": "large-test",
        }

        # Compress and send
        body_json = json.dumps(request).encode("utf-8")
        compressed_body = gzip.compress(body_json)

        # Verify compression is effective
        assert len(compressed_body) < len(body_json) * 0.5

        response = test_app.post(
            "/asap",
            content=compressed_body,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )

        assert response.status_code == 200
        json_response = response.json()
        assert "result" in json_response
        assert "envelope" in json_response["result"]
