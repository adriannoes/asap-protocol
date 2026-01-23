"""Tests for ASAP schema utilities."""

import json
from pathlib import Path

import pytest

from asap.models import Agent, TaskRequest
from asap.schemas import (
    SCHEMA_REGISTRY,
    TOTAL_SCHEMA_COUNT,
    export_all_schemas,
    export_schema,
    get_schema_json,
    list_schema_entries,
)


class TestExportSchema:
    """Tests for export_schema function."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """Verify export_schema writes valid JSON schema."""
        output_path = tmp_path / "agent.schema.json"
        result = export_schema(Agent, output_path)

        assert output_path.exists()
        assert result == output_path
        schema = json.loads(output_path.read_text())
        assert schema["title"] == "Agent"
        assert "properties" in schema

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Verify nested directories are created automatically."""
        output_path = tmp_path / "nested" / "deep" / "agent.schema.json"
        export_schema(Agent, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Verify export_schema overwrites existing files."""
        output_path = tmp_path / "agent.schema.json"
        output_path.write_text('{"old": "content"}')

        export_schema(Agent, output_path)

        schema = json.loads(output_path.read_text())
        assert schema["title"] == "Agent"
        assert "old" not in schema

    def test_schema_has_valid_json_structure(self, tmp_path: Path) -> None:
        """Verify exported schema has expected JSON Schema structure."""
        output_path = tmp_path / "task_request.schema.json"
        export_schema(TaskRequest, output_path)

        schema = json.loads(output_path.read_text())
        assert "title" in schema
        assert "type" in schema
        assert schema["type"] == "object"


class TestGetSchemaJson:
    """Tests for get_schema_json function."""

    def test_returns_valid_schema_for_known_name(self) -> None:
        """Verify schema JSON is correctly generated for known names."""
        schema = get_schema_json("agent")

        assert schema["title"] == "Agent"
        assert "properties" in schema
        assert "id" in schema["properties"]

    def test_returns_envelope_schema(self) -> None:
        """Verify envelope schema is accessible."""
        schema = get_schema_json("envelope")

        assert schema["title"] == "Envelope"
        assert "asap_version" in schema["properties"]

    def test_returns_task_request_schema(self) -> None:
        """Verify task_request schema uses underscore naming."""
        schema = get_schema_json("task_request")

        assert schema["title"] == "TaskRequest"

    def test_raises_for_unknown_name(self) -> None:
        """Verify unknown schema name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown schema name"):
            get_schema_json("nonexistent_schema")

    def test_raises_for_empty_name(self) -> None:
        """Verify empty schema name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown schema name"):
            get_schema_json("")

    @pytest.mark.parametrize(
        "schema_name",
        ["agent", "manifest", "task", "envelope", "task_request", "message_send"],
    )
    def test_all_core_schemas_accessible(self, schema_name: str) -> None:
        """Verify core schemas are all accessible by name."""
        schema = get_schema_json(schema_name)
        assert "title" in schema
        assert "properties" in schema


class TestListSchemaEntries:
    """Tests for list_schema_entries function."""

    def test_returns_all_schemas(self, tmp_path: Path) -> None:
        """Verify all schema entries are listed."""
        entries = list_schema_entries(tmp_path)

        assert len(entries) == TOTAL_SCHEMA_COUNT

    def test_contains_expected_schema_names(self, tmp_path: Path) -> None:
        """Verify expected schema names are present."""
        entries = list_schema_entries(tmp_path)
        schema_names = [name for name, _path in entries]

        assert "agent" in schema_names
        assert "envelope" in schema_names
        assert "task_request" in schema_names
        assert "manifest" in schema_names

    def test_paths_use_correct_subdirectories(self, tmp_path: Path) -> None:
        """Verify paths are organized into correct subdirectories."""
        entries = list_schema_entries(tmp_path)
        entries_dict = dict(entries)

        assert "entities" in str(entries_dict["agent"])
        assert "payloads" in str(entries_dict["task_request"])
        assert "parts" in str(entries_dict["text_part"])

    def test_envelope_is_at_root(self, tmp_path: Path) -> None:
        """Verify envelope schema is at output directory root."""
        entries = list_schema_entries(tmp_path)
        entries_dict = dict(entries)

        envelope_path = entries_dict["envelope"]
        assert envelope_path.parent == tmp_path


class TestExportAllSchemas:
    """Tests for export_all_schemas function."""

    def test_writes_all_files(self, tmp_path: Path) -> None:
        """Verify all schemas are exported."""
        written_paths = export_all_schemas(tmp_path)

        assert len(written_paths) == TOTAL_SCHEMA_COUNT
        for path in written_paths:
            assert path.exists()
            assert path.suffix == ".json"

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        """Verify correct directory structure is created."""
        export_all_schemas(tmp_path)

        assert (tmp_path / "entities").is_dir()
        assert (tmp_path / "parts").is_dir()
        assert (tmp_path / "payloads").is_dir()

    def test_entities_directory_content(self, tmp_path: Path) -> None:
        """Verify entities directory has expected files."""
        export_all_schemas(tmp_path)

        entities_dir = tmp_path / "entities"
        assert (entities_dir / "agent.schema.json").exists()
        assert (entities_dir / "manifest.schema.json").exists()
        assert (entities_dir / "task.schema.json").exists()

    def test_exported_schemas_are_valid_json(self, tmp_path: Path) -> None:
        """Verify all exported files contain valid JSON."""
        written_paths = export_all_schemas(tmp_path)

        for path in written_paths:
            content = path.read_text()
            schema = json.loads(content)
            assert "title" in schema

    def test_idempotency(self, tmp_path: Path) -> None:
        """Verify export is idempotent (can be run multiple times)."""
        first_run = export_all_schemas(tmp_path)
        second_run = export_all_schemas(tmp_path)

        assert len(first_run) == len(second_run)
        for path in second_run:
            assert path.exists()


class TestSchemaRegistry:
    """Tests for SCHEMA_REGISTRY constant."""

    def test_registry_has_expected_count(self) -> None:
        """Verify registry contains expected number of schemas."""
        assert len(SCHEMA_REGISTRY) == TOTAL_SCHEMA_COUNT

    def test_registry_keys_are_strings(self) -> None:
        """Verify all registry keys are strings."""
        for key in SCHEMA_REGISTRY:
            assert isinstance(key, str)

    def test_registry_values_are_model_classes(self) -> None:
        """Verify all registry values are Pydantic model classes."""
        for model_class in SCHEMA_REGISTRY.values():
            assert hasattr(model_class, "model_json_schema")

    def test_registry_contains_core_models(self) -> None:
        """Verify registry contains core protocol models."""
        assert "agent" in SCHEMA_REGISTRY
        assert "envelope" in SCHEMA_REGISTRY
        assert "task_request" in SCHEMA_REGISTRY
