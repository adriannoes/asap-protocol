"""Integration tests for server-side decompression.

Tests cover:
- Decompression of gzip-encoded requests
- Decompression of brotli-encoded requests (when available)
- Error handling for invalid compressed data
- Error handling for unsupported encodings
- Decompression bomb prevention
- Edge cases: threshold boundary, decompression failure recovery
"""

import gzip
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.transport.compression import (
    COMPRESSION_THRESHOLD,
    CompressionAlgorithm,
    compress_payload,
    decompress_payload,
    is_brotli_available,
)
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

from ..conftest import NoRateLimitTestBase


@pytest.fixture
def test_registry() -> HandlerRegistry:
    """Create a test handler registry."""
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    return registry


@pytest.fixture
def test_app(no_auth_manifest: Manifest, test_registry: HandlerRegistry) -> TestClient:
    """Create a test client for the ASAP server."""
    app = create_app(no_auth_manifest, test_registry)
    return TestClient(app)


@pytest.fixture
def sample_envelope(no_auth_manifest: Manifest) -> Envelope:
    """Create a sample envelope for testing."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient=no_auth_manifest.id,
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


class TestGzipDecompression(NoRateLimitTestBase):
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


class TestBrotliDecompression(NoRateLimitTestBase):
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

    # Runs only when brotli is NOT installed (verifies error path).
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


class TestCompressionErrorHandling(NoRateLimitTestBase):
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
        truncated = compressed[: len(compressed) // 2]

        response = test_app.post(
            "/asap",
            content=truncated,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )

        assert response.status_code == 400


class TestDecompressionBombPrevention(NoRateLimitTestBase):
    """Tests for decompression bomb prevention."""

    def test_decompressed_size_limit_enforced(
        self,
        no_auth_manifest: Manifest,
        test_registry: HandlerRegistry,
    ) -> None:
        """Verify decompressed size limit is enforced."""
        # Create app with small max request size
        small_max_size = 1024  # 1KB
        app = create_app(no_auth_manifest, test_registry, max_request_size=small_max_size)
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


class TestCompressionRoundTrip(NoRateLimitTestBase):
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


class TestCompressionThresholdBoundary(NoRateLimitTestBase):
    """Tests for payload size exactly at compression threshold boundary."""

    def test_payload_exactly_at_threshold_is_compressed(self) -> None:
        """Payload exactly at threshold IS compressed (threshold is exclusive)."""
        # Create payload exactly at threshold size
        data = b"x" * COMPRESSION_THRESHOLD

        compressed, algorithm = compress_payload(data)

        # Threshold check is "< threshold", so exactly at threshold IS compressed
        assert algorithm in (CompressionAlgorithm.GZIP, CompressionAlgorithm.BROTLI)
        assert len(compressed) < len(data)

    def test_payload_one_byte_below_threshold_not_compressed(self) -> None:
        """Payload one byte below threshold should NOT be compressed."""
        data = b"x" * (COMPRESSION_THRESHOLD - 1)

        compressed, algorithm = compress_payload(data)

        assert algorithm == CompressionAlgorithm.IDENTITY
        assert compressed == data

    def test_payload_one_byte_above_threshold_compressed(self) -> None:
        """Payload one byte above threshold should be compressed."""
        # Create compressible payload just above threshold
        data = b"x" * (COMPRESSION_THRESHOLD + 1)

        compressed, algorithm = compress_payload(data)

        # Should be compressed (gzip or brotli depending on availability)
        assert algorithm in (CompressionAlgorithm.GZIP, CompressionAlgorithm.BROTLI)
        assert len(compressed) < len(data)

    def test_server_handles_threshold_boundary_payload(
        self,
        test_app: TestClient,
        no_auth_manifest: Manifest,
    ) -> None:
        """Server should handle payload exactly at threshold boundary."""
        # Create minimal envelope that's just at the boundary
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient=no_auth_manifest.id,
            payload_type="task.request",
            payload={
                "conversation_id": "conv_boundary",
                "skill_id": "echo",
                "input": {"msg": "x"},
            },
        )

        request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": envelope.model_dump(mode="json")},
            "id": "boundary-test",
        }

        # Send as both compressed and uncompressed
        body_json = json.dumps(request).encode("utf-8")

        # Uncompressed
        response1 = test_app.post("/asap", content=body_json)
        assert response1.status_code == 200

        # Compressed (even small payload)
        compressed_body = gzip.compress(body_json)
        response2 = test_app.post(
            "/asap",
            content=compressed_body,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )
        assert response2.status_code == 200


class TestDecompressionFailureRecovery(NoRateLimitTestBase):
    """Tests for decompression failure recovery scenarios."""

    def test_decompress_corrupted_gzip_raises(self) -> None:
        """decompress_payload should raise on corrupted gzip data."""
        # Corrupt gzip data by modifying bytes
        valid_data = b'{"test": "data"}'
        compressed = gzip.compress(valid_data)
        corrupted = bytes([b ^ 0xFF for b in compressed[10:20]]) + compressed[20:]
        corrupted = compressed[:10] + corrupted

        with pytest.raises(Exception):  # noqa: B017
            decompress_payload(corrupted, "gzip")

    def test_decompress_wrong_encoding_raises(self) -> None:
        """decompress_payload with wrong encoding should raise."""
        # Gzip compressed data claimed as brotli
        data = b'{"test": "data"}'
        compressed = gzip.compress(data)

        # Should fail if trying to decompress as brotli
        if is_brotli_available():
            with pytest.raises(Exception):  # noqa: B017
                decompress_payload(compressed, "br")

    def test_decompress_empty_data_handling(self) -> None:
        """decompress_payload should handle empty or minimal data."""
        # Empty gzip stream
        empty_gzip = gzip.compress(b"")
        result = decompress_payload(empty_gzip, "gzip")
        assert result == b""

    def test_server_graceful_degradation_on_corrupt_data(
        self,
        test_app: TestClient,
    ) -> None:
        """Server should return proper error on corrupt compressed data."""
        # Create partially valid gzip header followed by garbage
        fake_gzip = bytes([0x1F, 0x8B, 0x08, 0x00]) + b"garbage data here"

        response = test_app.post(
            "/asap",
            content=fake_gzip,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )

        # Server returns 200 with JSON-RPC error for decompression failures
        # that are caught by error handling middleware, or 400 for direct HTTP error
        assert response.status_code in (200, 400)
        json_response = response.json()
        # Either HTTP error detail or JSON-RPC error
        assert "detail" in json_response or "error" in json_response


class TestCompressionIneffective(NoRateLimitTestBase):
    """Tests for when compression is ineffective (incompressible data)."""

    def test_random_data_compression_may_increase_size(self) -> None:
        """Random/already-compressed data may increase in size after compression."""
        import os

        # Random data is generally incompressible
        random_data = os.urandom(2048)

        compressed, algorithm = compress_payload(random_data)

        # The function should return original data if compression increases size
        # or return the compressed data (implementation may vary)
        if algorithm == CompressionAlgorithm.IDENTITY:
            assert compressed == random_data
        else:
            # If it did compress, verify it didn't grow significantly
            # Allow up to 10% growth for header overhead
            assert len(compressed) <= len(random_data) * 1.1

    def test_already_compressed_data_not_recompressed_effectively(self) -> None:
        """Already compressed data should not benefit from recompression."""
        # First compression
        original = b'{"data": "' + b"test " * 500 + b'"}'
        first_compressed, _ = compress_payload(
            original, preferred_algorithm=CompressionAlgorithm.GZIP
        )

        # Try to compress again - should use identity or minimal benefit
        second_compressed, algorithm = compress_payload(first_compressed)

        # Should either return identity or not reduce size significantly
        if algorithm != CompressionAlgorithm.IDENTITY:
            # Second compression shouldn't help much
            compression_ratio = len(second_compressed) / len(first_compressed)
            # Allow only minimal additional compression
            assert compression_ratio > 0.9


class TestMixedCompressionScenarios(NoRateLimitTestBase):
    """Tests for mixed compression scenarios in batch-like operations."""

    def test_multiple_payloads_different_sizes(
        self,
        test_app: TestClient,
        no_auth_manifest: Manifest,
    ) -> None:
        """Multiple payloads with different sizes should all be handled."""
        # Small payload (below threshold)
        small_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient=no_auth_manifest.id,
            payload_type="task.request",
            payload={
                "conversation_id": "small",
                "skill_id": "echo",
                "input": {"x": 1},
            },
        )

        # Large payload (above threshold)
        large_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient=no_auth_manifest.id,
            payload_type="task.request",
            payload={
                "conversation_id": "large",
                "skill_id": "echo",
                "input": {"data": "x" * 2000},
            },
        )

        # Send small uncompressed
        small_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": small_envelope.model_dump(mode="json")},
            "id": "small-1",
        }
        response1 = test_app.post("/asap", json=small_request)
        assert response1.status_code == 200

        # Send large compressed
        large_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": large_envelope.model_dump(mode="json")},
            "id": "large-1",
        }
        body_json = json.dumps(large_request).encode("utf-8")
        compressed_body = gzip.compress(body_json)
        response2 = test_app.post(
            "/asap",
            content=compressed_body,
            headers={
                "Content-Type": "application/json",
                "Content-Encoding": "gzip",
            },
        )
        assert response2.status_code == 200

    def test_compression_with_various_json_structures(
        self,
        test_app: TestClient,
        no_auth_manifest: Manifest,
    ) -> None:
        """Different JSON structures should compress and decompress correctly."""
        test_inputs = [
            {"simple": "string"},
            {"nested": {"deep": {"structure": [1, 2, 3]}}},
            {"array": [{"id": i} for i in range(100)]},
            {"unicode": "\u4e2d\u6587\u6587\u672c" * 100},  # Chinese text
            {"mixed": ["a", 1, True, None, {"key": "value"}]},
        ]

        for i, input_data in enumerate(test_inputs):
            envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:client",
                recipient=no_auth_manifest.id,
                payload_type="task.request",
                payload={
                    "conversation_id": f"structure-{i}",
                    "skill_id": "echo",
                    "input": input_data,
                },
            )

            request = {
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {"envelope": envelope.model_dump(mode="json")},
                "id": f"structure-test-{i}",
            }

            body_json = json.dumps(request).encode("utf-8")
            compressed_body = gzip.compress(body_json)

            response = test_app.post(
                "/asap",
                content=compressed_body,
                headers={
                    "Content-Type": "application/json",
                    "Content-Encoding": "gzip",
                },
            )

            assert response.status_code == 200, f"Failed for input {i}: {input_data}"
