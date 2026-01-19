"""Tests for ASAPBaseModel configuration."""

import pytest
from pydantic import Field, ValidationError

from asap.models.base import ASAPBaseModel


class SampleModel(ASAPBaseModel):
    """Sample model for testing base configuration."""

    name: str
    count: int = Field(default=0, ge=0)
    optional_field: str | None = None


class TestASAPBaseModel:
    """Test suite for ASAPBaseModel configuration."""

    def test_model_creation(self):
        """Test that models can be created with valid data."""
        model = SampleModel(name="test", count=5)

        assert model.name == "test"
        assert model.count == 5
        assert model.optional_field is None

    def test_model_is_frozen(self):
        """Test that models are immutable (frozen)."""
        model = SampleModel(name="test", count=5)

        # Attempting to modify should raise ValidationError
        with pytest.raises(ValidationError, match="frozen"):
            model.name = "new_name"  # type: ignore[misc]

        with pytest.raises(ValidationError, match="frozen"):
            model.count = 10  # type: ignore[misc]

    def test_extra_fields_forbidden(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SampleModel(
                name="test",
                count=5,
                extra_field="should_fail",  # type: ignore[call-arg]
            )

    def test_default_values_validated(self):
        """Test that default values are validated."""
        # Valid default
        model = SampleModel(name="test")
        assert model.count == 0

        # Invalid value should fail validation
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            SampleModel(name="test", count=-1)

    def test_json_serialization(self):
        """Test that models can be serialized to JSON."""
        model = SampleModel(name="test", count=5, optional_field="value")

        json_data = model.model_dump()
        assert json_data == {"name": "test", "count": 5, "optional_field": "value"}

        # JSON string
        json_str = model.model_dump_json()
        assert '"name":"test"' in json_str
        assert '"count":5' in json_str

    def test_json_deserialization(self):
        """Test that models can be deserialized from JSON."""
        json_data = {"name": "test", "count": 5}
        model = SampleModel.model_validate(json_data)

        assert model.name == "test"
        assert model.count == 5

    def test_json_schema_generation(self):
        """Test that JSON Schema is generated correctly."""
        schema = SampleModel.model_json_schema()

        # Check basic schema structure
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "count" in schema["properties"]
        assert "optional_field" in schema["properties"]

        # Check required fields
        assert "required" in schema
        assert "name" in schema["required"]
        assert "count" not in schema["required"]  # has default

        # Check additionalProperties is false (from config)
        assert schema.get("additionalProperties") is False

    def test_model_equality(self):
        """Test that models with same data are equal."""
        model1 = SampleModel(name="test", count=5)
        model2 = SampleModel(name="test", count=5)
        model3 = SampleModel(name="test", count=10)

        assert model1 == model2
        assert model1 != model3

    def test_model_copy(self):
        """Test that models can be copied with modifications."""
        original = SampleModel(name="test", count=5)

        # Create a copy with modifications
        modified = original.model_copy(update={"count": 10})

        assert original.count == 5  # Original unchanged
        assert modified.count == 10  # Copy modified
        assert modified.name == "test"  # Other fields preserved
