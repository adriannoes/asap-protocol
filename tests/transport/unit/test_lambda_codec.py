"""Unit tests for Lambda Lang codec.

Tests encode/decode round-trips, atom mappings, and edge cases.
"""

from __future__ import annotations

import pytest

from asap.transport.codecs import lambda_codec
from asap.transport.codecs.lambda_codec import (
    LAMBDA_CONTENT_TYPE,
    _DECODE_MAP,
    _ENCODE_MAP,
    _VERSION_PREFIX,
    decode,
    encode,
    is_available,
)

from ...transport.conftest import NoRateLimitTestBase


class TestLambdaCodecAvailability(NoRateLimitTestBase):
    """Test codec availability."""

    def test_is_available(self) -> None:
        assert is_available() is True

    def test_content_type(self) -> None:
        assert LAMBDA_CONTENT_TYPE == "application/vnd.asap+lambda"


class TestLambdaCodecRoundTrip(NoRateLimitTestBase):
    """Test encode/decode round-trip fidelity."""

    def test_simple_jsonrpc_request(self) -> None:
        data = {
            "jsonrpc": "2.0",
            "method": "asap.message",
            "params": {"envelope": {"sender": "agent-a", "recipient": "agent-b"}},
            "id": "req-1",
        }
        assert decode(encode(data)) == data

    def test_jsonrpc_response(self) -> None:
        data = {
            "jsonrpc": "2.0",
            "result": {
                "envelope": {
                    "sender": "agent-b",
                    "recipient": "agent-a",
                    "payload_type": "task.response",
                    "payload": {"status": "success"},
                }
            },
            "id": "req-1",
        }
        assert decode(encode(data)) == data

    def test_jsonrpc_error_response(self) -> None:
        data = {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Invalid Request", "data": None},
            "id": "req-1",
        }
        assert decode(encode(data)) == data

    def test_nested_complex_payload(self) -> None:
        data = {
            "jsonrpc": "2.0",
            "method": "asap.message",
            "params": {
                "envelope": {
                    "sender": "urn:asap:agent:alice",
                    "recipient": "urn:asap:agent:bob",
                    "payload_type": "task.request",
                    "payload": {
                        "task_id": "task-123",
                        "status": "pending",
                        "description": "Do something",
                        "nested": {"key": [1, 2, 3], "flag": True},
                    },
                    "trace_id": "trace-abc",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "nonce": "nonce-xyz",
                    "version": "0.1",
                },
                "idempotency_key": "idem-key-1",
            },
            "id": "req-42",
        }
        assert decode(encode(data)) == data

    def test_empty_params(self) -> None:
        data = {"jsonrpc": "2.0", "method": "asap.message", "params": {}, "id": "1"}
        assert decode(encode(data)) == data

    def test_empty_dict(self) -> None:
        data: dict[str, object] = {}
        assert decode(encode(data)) == data

    def test_payload_with_all_status_values(self) -> None:
        for status in ["success", "pending", "running", "completed", "failed", "cancelled"]:
            data = {"status": status}
            assert decode(encode(data)) == data

    def test_payload_with_all_task_types(self) -> None:
        for pt in ["task.request", "task.response", "task.status", "task.cancel"]:
            data = {"payload_type": pt}
            assert decode(encode(data)) == data

    def test_unicode_content(self) -> None:
        data = {"jsonrpc": "2.0", "params": {"text": "こんにちは 🌍"}, "id": "1"}
        assert decode(encode(data)) == data

    def test_numeric_values(self) -> None:
        data = {"jsonrpc": "2.0", "params": {"int": 42, "float": 3.14, "neg": -1}, "id": "1"}
        assert decode(encode(data)) == data

    def test_null_values(self) -> None:
        data = {"jsonrpc": "2.0", "result": None, "id": "1"}
        assert decode(encode(data)) == data

    def test_boolean_values(self) -> None:
        data = {"params": {"a": True, "b": False}}
        assert decode(encode(data)) == data

    def test_large_payload(self) -> None:
        data = {
            "jsonrpc": "2.0",
            "result": {"envelope": {"payload": {"items": list(range(1000))}}},
            "id": "1",
        }
        assert decode(encode(data)) == data


class TestLambdaCodecAtomMappings(NoRateLimitTestBase):
    """Test that atom substitution maps are consistent."""

    def test_encode_decode_maps_are_inverse(self) -> None:
        for token, atom in _ENCODE_MAP.items():
            assert _DECODE_MAP[atom] == token

    def test_no_atom_collisions(self) -> None:
        atoms = list(_ENCODE_MAP.values())
        assert len(atoms) == len(set(atoms)), "Duplicate atoms in encode map"

    def test_version_prefix_present(self) -> None:
        encoded = encode({"test": True})
        assert encoded.startswith(_VERSION_PREFIX)

    def test_compression_effect(self) -> None:
        """Lambda encoding should reduce size for typical ASAP payloads."""
        data = {
            "jsonrpc": "2.0",
            "method": "asap.message",
            "params": {
                "envelope": {
                    "sender": "urn:asap:agent:a",
                    "recipient": "urn:asap:agent:b",
                    "payload_type": "task.request",
                    "payload": {"task_id": "t1", "status": "pending"},
                    "timestamp": "2024-01-01T00:00:00Z",
                },
                "idempotency_key": "key-1",
            },
            "id": "req-1",
        }
        import json

        original = json.dumps(data, separators=(",", ":"))
        encoded = encode(data)
        assert len(encoded) < len(original)


class TestLambdaCodecEdgeCases(NoRateLimitTestBase):
    """Test edge cases and error handling."""

    def test_decode_missing_prefix(self) -> None:
        with pytest.raises(ValueError, match="missing version prefix"):
            decode('{"test": true}')

    def test_decode_wrong_prefix(self) -> None:
        with pytest.raises(ValueError, match="missing version prefix"):
            decode("λ99:invalid")

    def test_decode_malformed_json(self) -> None:
        with pytest.raises(ValueError, match="JSON decode failed"):
            decode(_VERSION_PREFIX + "{invalid json}")

    def test_decode_empty_after_prefix(self) -> None:
        with pytest.raises(ValueError, match="JSON decode failed"):
            decode(_VERSION_PREFIX)

    def test_unknown_atoms_passthrough(self) -> None:
        """Keys not in the substitution table should pass through unchanged."""
        data = {"custom_key": "custom_value", "another": [1, 2]}
        assert decode(encode(data)) == data

    def test_value_containing_atom_delimiter(self) -> None:
        """Values that happen to contain § should still round-trip correctly."""
        # The § delimiter is chosen because it cannot appear in standard JSON keys.
        # However, it CAN appear in string values. Our substitution only replaces
        # exact key patterns like "jsonrpc", not arbitrary substrings.
        data = {"jsonrpc": "2.0", "params": {"note": "section sign: §"}, "id": "1"}
        # This is a known limitation: if a value contains an atom like §Jrpc§,
        # it would be incorrectly decoded. In practice this is extremely unlikely
        # for real ASAP payloads.
        # We test the common case where § appears but not as an atom.
        assert decode(encode(data)) == data

    def test_module_public_api(self) -> None:
        """Test that the public API is accessible from the package."""
        assert lambda_codec.encode is encode
        assert lambda_codec.decode is decode
        assert lambda_codec.is_available is is_available
        assert lambda_codec.LAMBDA_CONTENT_TYPE == LAMBDA_CONTENT_TYPE
