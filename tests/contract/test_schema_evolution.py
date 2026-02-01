"""Contract tests for schema evolution and compatibility.

These tests verify that ASAP protocol schemas maintain backward and forward
compatibility across versions, ensuring smooth protocol evolution.

Schema evolution principles:
1. Backward compatibility: New schemas validate old data
2. Forward compatibility: Old schemas validate new data (with unknown fields)
3. Required fields: Only add required fields with defaults in new versions
4. Optional fields: New optional fields are safely ignored by old clients

Test scenarios:
1. v0.1.0 data → current schema (backward compatibility)
2. v0.5.0 data → current schema (backward compatibility)
3. Current data → simulated old schema (forward compatibility)
4. Field additions are handled gracefully
5. Type constraints are preserved across versions
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# Try to import jsonschema for validation
try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    Draft7Validator = None
    ValidationError = Exception


# Note: Rate limiting is automatically disabled for all tests in this package
# via the autouse fixture in conftest.py (following testing-standards.mdc)


# Path to schemas directory
SCHEMAS_DIR = Path(__file__).parent.parent.parent / "schemas"


def load_schema(schema_path: str) -> dict[str, Any]:
    """Load a JSON schema from file.

    Args:
        schema_path: Relative path from schemas directory

    Returns:
        Parsed JSON schema

    Raises:
        FileNotFoundError: If schema file doesn't exist
    """
    full_path = SCHEMAS_DIR / schema_path
    with open(full_path) as f:
        result: dict[str, Any] = json.load(f)
        return result


def validate_data(data: dict[str, Any], schema: dict[str, Any]) -> bool:
    """Validate data against a JSON schema.

    Args:
        data: Data to validate
        schema: JSON schema to validate against

    Returns:
        True if valid, raises ValidationError if invalid
    """
    if not HAS_JSONSCHEMA:
        pytest.skip("jsonschema not installed")
    jsonschema.validate(data, schema)
    return True


def is_valid(data: dict[str, Any], schema: dict[str, Any]) -> bool:
    """Check if data is valid against schema without raising.

    Args:
        data: Data to validate
        schema: JSON schema

    Returns:
        True if valid, False if invalid
    """
    if not HAS_JSONSCHEMA:
        pytest.skip("jsonschema not installed")
    validator = Draft7Validator(schema)
    result: bool = validator.is_valid(data)
    return result


# Sample data representing different protocol versions
V010_ENVELOPE_DATA = {
    "asap_version": "0.1",
    "sender": "urn:asap:agent:v010-client",
    "recipient": "urn:asap:agent:server",
    "payload_type": "task.request",
    "payload": {
        "conversation_id": "conv_001",
        "skill_id": "echo",
        "input": {"message": "hello"},
    },
}

V050_ENVELOPE_DATA = {
    "asap_version": "0.5",
    "sender": "urn:asap:agent:v050-client",
    "recipient": "urn:asap:agent:server",
    "payload_type": "task.request",
    "payload": {
        "conversation_id": "conv_002",
        "skill_id": "echo",
        "input": {"message": "hello from v0.5.0"},
    },
    "extensions": {"nonce": "unique-nonce-001"},
    "trace_id": "trace-v050-001",
}

V100_ENVELOPE_DATA = {
    "asap_version": "1.0",
    "sender": "urn:asap:agent:v100-client",
    "recipient": "urn:asap:agent:server",
    "payload_type": "task.request",
    "payload": {
        "conversation_id": "conv_003",
        "skill_id": "echo",
        "input": {"message": "hello from v1.0.0"},
    },
    "extensions": {
        "nonce": "unique-nonce-002",
        "client_version": "1.0.0",
        "v100_feature": "enhanced_tracing",
    },
    "trace_id": "trace-v100-001",
    "correlation_id": "req-001",
}

V010_TASK_REQUEST_DATA = {
    "conversation_id": "conv_task_001",
    "skill_id": "research",
    "input": {"query": "test query"},
}

V050_TASK_REQUEST_DATA = {
    "conversation_id": "conv_task_002",
    "skill_id": "research",
    "input": {"query": "test query from v0.5.0"},
    "parent_task_id": "parent_001",
    "config": {"timeout_seconds": 60},
}

V100_TASK_REQUEST_DATA = {
    "conversation_id": "conv_task_003",
    "skill_id": "research",
    "input": {"query": "test query from v1.0.0"},
    "parent_task_id": "parent_002",
    "config": {"timeout_seconds": 120, "priority": "high", "streaming": True},
}

V010_TASK_RESPONSE_DATA = {
    "task_id": "task_001",
    "status": "completed",
}

V050_TASK_RESPONSE_DATA = {
    "task_id": "task_002",
    "status": "completed",
    "result": {"summary": "Task completed successfully"},
    "metrics": {"duration_ms": 1500},
}

V100_TASK_RESPONSE_DATA = {
    "task_id": "task_003",
    "status": "completed",
    "result": {"summary": "Task completed with v1.0.0 features"},
    "final_state": {"step": "final", "progress": 100},
    "metrics": {"duration_ms": 2000, "tokens_used": 1500},
}

V010_MANIFEST_DATA = {
    "id": "urn:asap:agent:v010-agent",
    "name": "v0.1.0 Agent",
    "version": "0.1.0",
    "description": "Basic agent from v0.1.0",
    "capabilities": {
        "asap_version": "0.1",
        "skills": [{"id": "echo", "description": "Echo skill"}],
    },
    "endpoints": {"asap": "http://localhost:8000/asap"},
}

V050_MANIFEST_DATA = {
    "id": "urn:asap:agent:v050-agent",
    "name": "v0.5.0 Agent",
    "version": "0.5.0",
    "description": "Security-enhanced agent from v0.5.0",
    "capabilities": {
        "asap_version": "0.5",
        "skills": [
            {"id": "echo", "description": "Echo skill"},
            {"id": "secure", "description": "Secure processing"},
        ],
        "state_persistence": True,
    },
    "endpoints": {"asap": "http://localhost:8000/asap"},
    "auth": {"schemes": ["bearer"]},
}

V100_MANIFEST_DATA = {
    "id": "urn:asap:agent:v100-agent",
    "name": "v1.0.0 Agent",
    "version": "1.0.0",
    "description": "Full-featured agent from v1.0.0",
    "capabilities": {
        "asap_version": "1.0",
        "skills": [
            {
                "id": "echo",
                "description": "Echo skill",
                "input_schema": {"type": "object"},
            },
            {
                "id": "advanced",
                "description": "Advanced processing",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
            },
        ],
        "state_persistence": True,
        "streaming": True,
        "mcp_tools": ["web_search", "file_read"],
    },
    "endpoints": {"asap": "http://localhost:8000/asap", "events": "ws://localhost:8000/events"},
    "auth": {"schemes": ["bearer"], "oauth2": {"token_url": "https://auth.example.com/token"}},
}


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestEnvelopeSchemaBackwardCompatibility:
    """Tests for envelope schema backward compatibility."""

    def test_v010_envelope_validates_against_current_schema(self) -> None:
        """Test that v0.1.0 envelope data validates against current schema."""
        schema = load_schema("envelope.schema.json")
        assert validate_data(V010_ENVELOPE_DATA, schema)

    def test_v050_envelope_validates_against_current_schema(self) -> None:
        """Test that v0.5.0 envelope data validates against current schema."""
        schema = load_schema("envelope.schema.json")
        assert validate_data(V050_ENVELOPE_DATA, schema)

    def test_v100_envelope_validates_against_current_schema(self) -> None:
        """Test that v1.0.0 envelope data validates against current schema."""
        schema = load_schema("envelope.schema.json")
        assert validate_data(V100_ENVELOPE_DATA, schema)

    def test_minimal_envelope_validates(self) -> None:
        """Test that minimal envelope with only required fields validates."""
        schema = load_schema("envelope.schema.json")
        minimal_envelope = {
            "asap_version": "0.1",
            "sender": "urn:asap:agent:sender",
            "recipient": "urn:asap:agent:recipient",
            "payload_type": "task.request",
            "payload": {},
        }
        assert validate_data(minimal_envelope, schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestTaskRequestSchemaBackwardCompatibility:
    """Tests for TaskRequest schema backward compatibility."""

    def test_v010_task_request_validates(self) -> None:
        """Test that v0.1.0 TaskRequest validates against current schema."""
        schema = load_schema("payloads/task_request.schema.json")
        assert validate_data(V010_TASK_REQUEST_DATA, schema)

    def test_v050_task_request_validates(self) -> None:
        """Test that v0.5.0 TaskRequest validates against current schema."""
        schema = load_schema("payloads/task_request.schema.json")
        assert validate_data(V050_TASK_REQUEST_DATA, schema)

    def test_v100_task_request_validates(self) -> None:
        """Test that v1.0.0 TaskRequest validates against current schema."""
        schema = load_schema("payloads/task_request.schema.json")
        assert validate_data(V100_TASK_REQUEST_DATA, schema)

    def test_minimal_task_request_validates(self) -> None:
        """Test that minimal TaskRequest with only required fields validates."""
        schema = load_schema("payloads/task_request.schema.json")
        minimal_request = {
            "conversation_id": "conv_min",
            "skill_id": "test",
            "input": {},
        }
        assert validate_data(minimal_request, schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestTaskResponseSchemaBackwardCompatibility:
    """Tests for TaskResponse schema backward compatibility."""

    def test_v010_task_response_validates(self) -> None:
        """Test that v0.1.0 TaskResponse validates against current schema."""
        schema = load_schema("payloads/task_response.schema.json")
        assert validate_data(V010_TASK_RESPONSE_DATA, schema)

    def test_v050_task_response_validates(self) -> None:
        """Test that v0.5.0 TaskResponse validates against current schema."""
        schema = load_schema("payloads/task_response.schema.json")
        assert validate_data(V050_TASK_RESPONSE_DATA, schema)

    def test_v100_task_response_validates(self) -> None:
        """Test that v1.0.0 TaskResponse validates against current schema."""
        schema = load_schema("payloads/task_response.schema.json")
        assert validate_data(V100_TASK_RESPONSE_DATA, schema)

    def test_all_status_values_valid(self) -> None:
        """Test that all TaskStatus enum values are valid."""
        schema = load_schema("payloads/task_response.schema.json")
        statuses = ["submitted", "working", "completed", "failed", "cancelled", "input_required"]

        for status in statuses:
            response = {"task_id": "task_status_test", "status": status}
            assert validate_data(response, schema), f"Status '{status}' should be valid"


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestManifestSchemaBackwardCompatibility:
    """Tests for Manifest schema backward compatibility."""

    def test_v010_manifest_validates(self) -> None:
        """Test that v0.1.0 Manifest validates against current schema."""
        schema = load_schema("entities/manifest.schema.json")
        assert validate_data(V010_MANIFEST_DATA, schema)

    def test_v050_manifest_validates(self) -> None:
        """Test that v0.5.0 Manifest validates against current schema."""
        schema = load_schema("entities/manifest.schema.json")
        assert validate_data(V050_MANIFEST_DATA, schema)

    def test_v100_manifest_validates(self) -> None:
        """Test that v1.0.0 Manifest validates against current schema."""
        schema = load_schema("entities/manifest.schema.json")
        assert validate_data(V100_MANIFEST_DATA, schema)

    def test_minimal_manifest_validates(self) -> None:
        """Test that minimal Manifest with only required fields validates."""
        schema = load_schema("entities/manifest.schema.json")
        minimal_manifest = {
            "id": "urn:asap:agent:minimal",
            "name": "Minimal Agent",
            "version": "1.0.0",
            "description": "Minimal agent",
            "capabilities": {"skills": [{"id": "test", "description": "Test"}]},
            "endpoints": {"asap": "http://localhost:8000/asap"},
        }
        assert validate_data(minimal_manifest, schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestSchemaForwardCompatibility:
    """Tests for forward compatibility (old clients reading new data)."""

    def test_unknown_envelope_fields_handled(self) -> None:
        """Test that unknown fields in envelope don't break validation.

        Note: With additionalProperties=false, unknown fields will fail.
        This test verifies the schema behavior is as expected.
        """
        schema = load_schema("envelope.schema.json")

        # Current schema has additionalProperties=false, so unknown fields fail
        envelope_with_unknown = {
            "asap_version": "2.0",  # Future version
            "sender": "urn:asap:agent:future-client",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
            "future_field": "some_value",  # Unknown field
        }

        # With strict schema, this should fail
        assert not is_valid(envelope_with_unknown, schema)

        # But valid data without unknown fields should work
        valid_envelope = {
            "asap_version": "2.0",
            "sender": "urn:asap:agent:future-client",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
        }
        assert is_valid(valid_envelope, schema)

    def test_extensions_allow_future_fields(self) -> None:
        """Test that extensions field allows arbitrary future data."""
        schema = load_schema("envelope.schema.json")

        # Extensions can contain any future fields
        envelope_with_future_extensions = {
            "asap_version": "1.0",
            "sender": "urn:asap:agent:client",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
            "extensions": {
                "v200_feature": "quantum_processing",
                "future_metadata": {"quantum_state": "entangled"},
                "nested": {"deep": {"data": True}},
            },
        }
        assert validate_data(envelope_with_future_extensions, schema)

    def test_payload_allows_arbitrary_content(self) -> None:
        """Test that payload field allows arbitrary content for future payloads."""
        schema = load_schema("envelope.schema.json")

        envelope_with_future_payload = {
            "asap_version": "1.0",
            "sender": "urn:asap:agent:client",
            "recipient": "urn:asap:agent:server",
            "payload_type": "future.payload.type",
            "payload": {
                "future_field_1": "value",
                "future_field_2": [1, 2, 3],
                "nested_future": {"deep": {"nested": True}},
            },
        }
        assert validate_data(envelope_with_future_payload, schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestSchemaEvolutionPatterns:
    """Tests for common schema evolution patterns."""

    def test_adding_optional_fields_is_safe(self) -> None:
        """Test that adding optional fields doesn't break old data."""
        schema = load_schema("envelope.schema.json")

        # Old data (v0.1.0 style) without optional fields
        old_data = {
            "asap_version": "0.1",
            "sender": "urn:asap:agent:old",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
            # No trace_id, correlation_id, extensions
        }
        assert validate_data(old_data, schema)

        # New data with optional fields
        new_data = {
            "asap_version": "1.0",
            "sender": "urn:asap:agent:new",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
            "trace_id": "trace-123",
            "correlation_id": "corr-456",
            "extensions": {"new_feature": True},
        }
        assert validate_data(new_data, schema)

    def test_null_optional_fields_valid(self) -> None:
        """Test that null values for optional fields are valid."""
        schema = load_schema("envelope.schema.json")

        envelope_with_nulls: dict[str, Any] = {
            "asap_version": "1.0",
            "sender": "urn:asap:agent:client",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
            "id": None,
            "timestamp": None,
            "correlation_id": None,
            "trace_id": None,
            "extensions": None,
        }
        assert validate_data(envelope_with_nulls, schema)

    def test_required_fields_must_be_present(self) -> None:
        """Test that required fields cannot be omitted."""
        schema = load_schema("envelope.schema.json")

        # Missing sender (required field)
        invalid_envelope = {
            "asap_version": "1.0",
            # "sender" missing
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
        }
        assert not is_valid(invalid_envelope, schema)

        # Missing payload_type (required field)
        invalid_envelope_2 = {
            "asap_version": "1.0",
            "sender": "urn:asap:agent:client",
            "recipient": "urn:asap:agent:server",
            # "payload_type" missing
            "payload": {},
        }
        assert not is_valid(invalid_envelope_2, schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestTypeConstraintPreservation:
    """Tests for type constraint preservation across versions."""

    def test_string_fields_reject_other_types(self) -> None:
        """Test that string fields reject non-string types."""
        schema = load_schema("envelope.schema.json")

        # asap_version must be string
        invalid_envelope = {
            "asap_version": 1.0,  # Should be string "1.0"
            "sender": "urn:asap:agent:client",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": {},
        }
        assert not is_valid(invalid_envelope, schema)

    def test_object_fields_reject_other_types(self) -> None:
        """Test that object fields reject non-object types."""
        schema = load_schema("envelope.schema.json")

        # payload must be object
        invalid_envelope = {
            "asap_version": "1.0",
            "sender": "urn:asap:agent:client",
            "recipient": "urn:asap:agent:server",
            "payload_type": "task.request",
            "payload": "not an object",
        }
        assert not is_valid(invalid_envelope, schema)

    def test_array_fields_in_manifest(self) -> None:
        """Test that array fields in manifest work correctly."""
        schema = load_schema("entities/manifest.schema.json")

        # skills must be array
        manifest_with_skills = {
            "id": "urn:asap:agent:test",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "Test",
            "capabilities": {
                "skills": [
                    {"id": "skill1", "description": "Skill 1"},
                    {"id": "skill2", "description": "Skill 2"},
                ]
            },
            "endpoints": {"asap": "http://localhost:8000/asap"},
        }
        assert validate_data(manifest_with_skills, schema)


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestCrossVersionDataExchange:
    """Tests for data exchange between different protocol versions."""

    def test_v010_client_data_usable_by_v100_server(self) -> None:
        """Test that v0.1.0 client data can be processed by v1.0.0 server schemas."""
        envelope_schema = load_schema("envelope.schema.json")
        task_request_schema = load_schema("payloads/task_request.schema.json")

        # v0.1.0 style complete message
        assert validate_data(V010_ENVELOPE_DATA, envelope_schema)
        assert validate_data(V010_TASK_REQUEST_DATA, task_request_schema)

    def test_v050_client_data_usable_by_v100_server(self) -> None:
        """Test that v0.5.0 client data can be processed by v1.0.0 server schemas."""
        envelope_schema = load_schema("envelope.schema.json")
        task_request_schema = load_schema("payloads/task_request.schema.json")

        assert validate_data(V050_ENVELOPE_DATA, envelope_schema)
        assert validate_data(V050_TASK_REQUEST_DATA, task_request_schema)

    def test_v100_client_data_usable_by_v050_server_schemas(self) -> None:
        """Test that v1.0.0 client data validates against current schemas.

        Since v0.5.0 and v1.0.0 use the same schema structure (just different
        version numbers), v1.0.0 data should validate against current schemas
        which represent the v0.5.0/v1.0.0 era schema.
        """
        envelope_schema = load_schema("envelope.schema.json")
        task_request_schema = load_schema("payloads/task_request.schema.json")

        assert validate_data(V100_ENVELOPE_DATA, envelope_schema)
        assert validate_data(V100_TASK_REQUEST_DATA, task_request_schema)
