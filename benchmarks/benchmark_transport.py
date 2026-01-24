"""Benchmarks for ASAP HTTP transport layer.

These benchmarks measure the performance of:
- JSON-RPC request handling
- Full HTTP round-trip times
- Manifest discovery endpoint
- Metrics endpoint

Performance targets:
- JSON-RPC processing: < 5ms (excluding network)
- Manifest GET: < 1ms
- Metrics GET: < 2ms
- Full round-trip (local): < 10ms

Run with: uv run pytest benchmarks/benchmark_transport.py --benchmark-only -v
"""

from typing import Any

from fastapi.testclient import TestClient

from asap.models.envelope import Envelope
from asap.transport.jsonrpc import JsonRpcRequest, JsonRpcResponse


class TestJsonRpcProcessing:
    """Benchmarks for JSON-RPC message processing."""

    def test_jsonrpc_request_creation(self, benchmark: Any, sample_envelope: Envelope) -> None:
        """Benchmark JSON-RPC request creation."""

        def create_request() -> JsonRpcRequest:
            return JsonRpcRequest(
                method="asap.send",
                params={"envelope": sample_envelope.model_dump(mode="json")},
                id="request-001",
            )

        result = benchmark(create_request)
        assert result.method == "asap.send"

    def test_jsonrpc_response_creation(self, benchmark: Any, sample_envelope: Envelope) -> None:
        """Benchmark JSON-RPC response creation."""

        def create_response() -> JsonRpcResponse:
            return JsonRpcResponse(
                result=sample_envelope.model_dump(mode="json"),
                id="request-001",
            )

        result = benchmark(create_response)
        assert result.id == "request-001"

    def test_jsonrpc_request_serialization(self, benchmark: Any, sample_envelope: Envelope) -> None:
        """Benchmark JSON-RPC request serialization."""
        request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": sample_envelope.model_dump(mode="json")},
            id="request-001",
        )

        result = benchmark(request.model_dump_json)
        assert "asap.send" in result


class TestHttpEndpoints:
    """Benchmarks for HTTP endpoint performance."""

    def test_manifest_endpoint(self, benchmark: Any, benchmark_app: TestClient) -> None:
        """Benchmark manifest discovery endpoint."""

        def get_manifest() -> dict[str, Any]:
            response = benchmark_app.get("/.well-known/asap/manifest.json")
            return response.json()

        result = benchmark(get_manifest)
        assert "id" in result
        assert "capabilities" in result

    def test_metrics_endpoint(self, benchmark: Any, benchmark_app: TestClient) -> None:
        """Benchmark metrics endpoint."""

        def get_metrics() -> str:
            response = benchmark_app.get("/asap/metrics")
            return response.text

        result = benchmark(get_metrics)
        assert "asap_" in result

    def test_asap_endpoint_success(
        self, benchmark: Any, benchmark_app: TestClient, sample_jsonrpc_request: dict[str, Any]
    ) -> None:
        """Benchmark successful ASAP message processing."""

        def send_message() -> dict[str, Any]:
            response = benchmark_app.post("/asap", json=sample_jsonrpc_request)
            return response.json()

        result = benchmark(send_message)
        assert "result" in result or "error" in result

    def test_asap_endpoint_invalid_request(self, benchmark: Any, benchmark_app: TestClient) -> None:
        """Benchmark error handling for invalid requests."""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "invalid.method",
            "params": {},
            "id": "error-test",
        }

        def send_invalid() -> dict[str, Any]:
            response = benchmark_app.post("/asap", json=invalid_request)
            return response.json()

        result = benchmark(send_invalid)
        assert "error" in result


class TestThroughput:
    """Benchmarks for throughput measurement."""

    def test_sequential_requests(
        self, benchmark: Any, benchmark_app: TestClient, sample_jsonrpc_request: dict[str, Any]
    ) -> None:
        """Benchmark sequential request throughput (10 requests)."""

        def send_batch() -> int:
            success_count = 0
            for i in range(10):
                request = sample_jsonrpc_request.copy()
                request["id"] = f"batch-{i}"
                response = benchmark_app.post("/asap", json=request)
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(send_batch)
        assert result == 10

    def test_manifest_throughput(self, benchmark: Any, benchmark_app: TestClient) -> None:
        """Benchmark manifest endpoint throughput (50 requests)."""

        def get_manifests() -> int:
            success_count = 0
            for _ in range(50):
                response = benchmark_app.get("/.well-known/asap/manifest.json")
                if response.status_code == 200:
                    success_count += 1
            return success_count

        result = benchmark(get_manifests)
        assert result == 50


class TestPayloadSizes:
    """Benchmarks for different payload sizes."""

    def test_small_payload(self, benchmark: Any, benchmark_app: TestClient) -> None:
        """Benchmark small payload processing (~100 bytes)."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload={"id": "small"},
        )
        request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": envelope.model_dump(mode="json")},
            "id": "small-payload",
        }

        def send_small() -> int:
            return benchmark_app.post("/asap", json=request).status_code

        result = benchmark(send_small)
        assert result == 200

    def test_medium_payload(self, benchmark: Any, benchmark_app: TestClient) -> None:
        """Benchmark medium payload processing (~1KB)."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload={
                "conversation_id": "conv_001",
                "skill_id": "research",
                "input": {
                    "query": "ASAP protocol" * 20,  # ~300 chars
                    "options": {f"option_{i}": f"value_{i}" for i in range(10)},
                    "tags": [f"tag_{i}" for i in range(20)],
                },
            },
        )
        request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": envelope.model_dump(mode="json")},
            "id": "medium-payload",
        }

        def send_medium() -> int:
            return benchmark_app.post("/asap", json=request).status_code

        result = benchmark(send_medium)
        assert result == 200

    def test_large_payload(self, benchmark: Any, benchmark_app: TestClient) -> None:
        """Benchmark large payload processing (~10KB)."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload={
                "conversation_id": "conv_001",
                "skill_id": "research",
                "input": {
                    "query": "ASAP protocol benchmark test " * 100,  # ~3KB
                    "items": [
                        {"id": i, "name": f"item_{i}", "data": "x" * 50} for i in range(100)
                    ],  # ~7KB
                },
            },
        )
        request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": envelope.model_dump(mode="json")},
            "id": "large-payload",
        }

        def send_large() -> int:
            return benchmark_app.post("/asap", json=request).status_code

        result = benchmark(send_large)
        assert result == 200
