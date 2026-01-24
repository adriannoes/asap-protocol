"""Tests for ASAP CLI."""

import json
import re
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from asap import __version__
from asap.cli import DEFAULT_SCHEMAS_DIR, app
from asap.schemas import TOTAL_SCHEMA_COUNT

# ANSI escape sequence pattern for stripping colors from output
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_PATTERN.sub("", text)


class TestCliVersion:
    """Tests for CLI version command."""

    def test_version_flag(self) -> None:
        """Ensure --version prints the package version."""
        runner = CliRunner()
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert result.stdout.strip() == __version__


class TestCliHelp:
    """Tests for CLI help output."""

    def test_help_displays_commands(self) -> None:
        """Ensure --help shows available commands."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "export-schemas" in output
        assert "list-schemas" in output
        assert "show-schema" in output

    def test_export_schemas_help(self) -> None:
        """Ensure export-schemas --help shows options."""
        runner = CliRunner()
        result = runner.invoke(app, ["export-schemas", "--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--output-dir" in output


class TestCliExportSchemas:
    """Tests for export-schemas command."""

    def test_writes_schema_files(self, tmp_path: Path) -> None:
        """Ensure export-schemas writes schema files."""
        runner = CliRunner()
        result = runner.invoke(app, ["export-schemas", "--output-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / "entities" / "agent.schema.json").exists()
        assert (tmp_path / "payloads" / "task_request.schema.json").exists()
        assert (tmp_path / "envelope.schema.json").exists()

    def test_reports_count(self, tmp_path: Path) -> None:
        """Ensure export-schemas reports the number of exported schemas."""
        runner = CliRunner()
        result = runner.invoke(app, ["export-schemas", "--output-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert f"Exported {TOTAL_SCHEMA_COUNT} schemas" in result.stdout

    def test_handles_permission_error(self, tmp_path: Path) -> None:
        """Ensure export-schemas handles permission errors gracefully."""
        with patch("asap.cli.export_all_schemas") as mock_export:
            mock_export.side_effect = PermissionError("Access denied")
            runner = CliRunner()
            result = runner.invoke(app, ["export-schemas", "--output-dir", str(tmp_path)])

            assert result.exit_code != 0
            # Typer outputs error messages to stdout via echo
            assert "Cannot write to directory" in result.output

    def test_handles_os_error(self, tmp_path: Path) -> None:
        """Ensure export-schemas handles OS errors gracefully."""
        with patch("asap.cli.export_all_schemas") as mock_export:
            mock_export.side_effect = OSError("Disk full")
            runner = CliRunner()
            result = runner.invoke(app, ["export-schemas", "--output-dir", str(tmp_path)])

            assert result.exit_code != 0
            # Typer outputs error messages to stdout via echo
            assert "Failed to export schemas" in result.output

    def test_validates_exported_content(self, tmp_path: Path) -> None:
        """Ensure exported schemas contain expected structure."""
        runner = CliRunner()
        result = runner.invoke(app, ["export-schemas", "--output-dir", str(tmp_path)])

        assert result.exit_code == 0

        # Spot check a few schemas
        agent_schema = json.loads((tmp_path / "entities" / "agent.schema.json").read_text())
        assert "id" in agent_schema.get("properties", {})

        envelope_schema = json.loads((tmp_path / "envelope.schema.json").read_text())
        assert "asap_version" in envelope_schema.get("properties", {})


class TestCliListSchemas:
    """Tests for list-schemas command."""

    def test_prints_known_schema_names(self) -> None:
        """Ensure list-schemas prints known schema names."""
        runner = CliRunner()
        result = runner.invoke(app, ["list-schemas"])

        assert result.exit_code == 0
        assert "agent\tentities/agent.schema.json" in result.stdout

    def test_lists_all_schemas(self) -> None:
        """Ensure list-schemas lists all registered schemas."""
        runner = CliRunner()
        result = runner.invoke(app, ["list-schemas"])

        assert result.exit_code == 0
        assert "envelope" in result.stdout
        assert "task_request" in result.stdout
        assert "manifest" in result.stdout


class TestCliShowSchema:
    """Tests for show-schema command."""

    def test_prints_valid_json(self) -> None:
        """Ensure show-schema prints valid JSON."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-schema", "agent"])

        assert result.exit_code == 0
        schema = json.loads(result.stdout)
        assert schema["title"] == "Agent"

    def test_rejects_unknown_name(self) -> None:
        """Ensure show-schema rejects unknown schema names."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-schema", "not-a-schema"])

        assert result.exit_code != 0

    def test_envelope_schema(self) -> None:
        """Ensure show-schema works for envelope."""
        runner = CliRunner()
        result = runner.invoke(app, ["show-schema", "envelope"])

        assert result.exit_code == 0
        schema = json.loads(result.stdout)
        assert schema["title"] == "Envelope"


class TestCliDefaults:
    """Tests for CLI default values."""

    def test_default_schemas_dir_exists(self) -> None:
        """Ensure DEFAULT_SCHEMAS_DIR is defined."""
        assert Path("schemas") == DEFAULT_SCHEMAS_DIR


class TestCliValidateSchema:
    """Tests for validate-schema command."""

    def test_help_shows_validate_schema(self) -> None:
        """Ensure --help shows validate-schema command."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "validate-schema" in output

    def test_validate_schema_help(self) -> None:
        """Ensure validate-schema --help shows options."""
        runner = CliRunner()
        result = runner.invoke(app, ["validate-schema", "--help"])

        assert result.exit_code == 0
        output = strip_ansi(result.stdout)
        assert "--schema-type" in output
        assert "FILE" in output

    def test_validates_valid_agent_json(self, tmp_path: Path) -> None:
        """Ensure validate-schema accepts valid agent JSON."""
        agent_json = {
            "id": "urn:asap:agent:test-agent",
            "manifest_uri": "https://example.com/.well-known/asap/manifest.json",
            "capabilities": ["task.execute"],
        }
        json_file = tmp_path / "agent.json"
        json_file.write_text(json.dumps(agent_json), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(app, ["validate-schema", str(json_file), "--schema-type", "agent"])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_validates_valid_envelope_json(self, tmp_path: Path) -> None:
        """Ensure validate-schema accepts valid envelope JSON."""
        envelope_json = {
            "asap_version": "0.1",
            "sender": "urn:asap:agent:test-agent",
            "recipient": "urn:asap:agent:target-agent",
            "payload_type": "TaskRequest",
            "payload": {"task_id": "01JGQXYZ1234567890123456"},
        }
        json_file = tmp_path / "envelope.json"
        json_file.write_text(json.dumps(envelope_json), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            app, ["validate-schema", str(json_file), "--schema-type", "envelope"]
        )

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_rejects_invalid_json(self, tmp_path: Path) -> None:
        """Ensure validate-schema rejects invalid JSON syntax."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{invalid json}", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(app, ["validate-schema", str(json_file), "--schema-type", "agent"])

        assert result.exit_code != 0
        assert "Invalid JSON" in result.output

    def test_rejects_invalid_agent_data(self, tmp_path: Path) -> None:
        """Ensure validate-schema rejects data not matching agent schema."""
        invalid_agent = {
            "name": "Missing required id field",
        }
        json_file = tmp_path / "invalid_agent.json"
        json_file.write_text(json.dumps(invalid_agent), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(app, ["validate-schema", str(json_file), "--schema-type", "agent"])

        assert result.exit_code != 0
        assert "Validation error" in result.output

    def test_rejects_unknown_schema_type(self, tmp_path: Path) -> None:
        """Ensure validate-schema rejects unknown schema types."""
        json_file = tmp_path / "test.json"
        json_file.write_text("{}", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            app, ["validate-schema", str(json_file), "--schema-type", "unknown_type"]
        )

        assert result.exit_code != 0
        assert "Unknown schema type" in result.output

    def test_handles_missing_file(self) -> None:
        """Ensure validate-schema handles missing files gracefully."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate-schema", "/nonexistent/file.json", "--schema-type", "agent"]
        )

        assert result.exit_code != 0
        assert "File not found" in result.output

    def test_auto_detects_envelope_schema(self, tmp_path: Path) -> None:
        """Ensure validate-schema can auto-detect envelope schema from payload_type."""
        envelope_json = {
            "asap_version": "0.1",
            "sender": "urn:asap:agent:test-agent",
            "recipient": "urn:asap:agent:target-agent",
            "payload_type": "TaskRequest",
            "payload": {"task_id": "01JGQXYZ1234567890123456"},
        }
        json_file = tmp_path / "envelope.json"
        json_file.write_text(json.dumps(envelope_json), encoding="utf-8")

        runner = CliRunner()
        # No --schema-type provided, should auto-detect as envelope
        result = runner.invoke(app, ["validate-schema", str(json_file)])

        assert result.exit_code == 0
        assert "Valid" in result.stdout

    def test_requires_schema_type_for_non_envelope(self, tmp_path: Path) -> None:
        """Ensure validate-schema requires schema-type for non-envelope JSON."""
        agent_json = {
            "id": "urn:asap:agent:test-agent",
            "manifest_uri": "https://example.com/manifest.json",
            "capabilities": [],
        }
        json_file = tmp_path / "agent.json"
        json_file.write_text(json.dumps(agent_json), encoding="utf-8")

        runner = CliRunner()
        # No --schema-type provided, not auto-detectable
        result = runner.invoke(app, ["validate-schema", str(json_file)])

        assert result.exit_code != 0
        # Strip ANSI codes before checking output
        clean_output = strip_ansi(result.output).lower()
        assert "schema-type" in clean_output

    def test_displays_validation_error_details(self, tmp_path: Path) -> None:
        """Ensure validate-schema shows detailed validation errors."""
        invalid_agent = {
            "id": "invalid-ulid-format",  # Invalid ULID format
            "name": "Test Agent",
        }
        json_file = tmp_path / "invalid_agent.json"
        json_file.write_text(json.dumps(invalid_agent), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(app, ["validate-schema", str(json_file), "--schema-type", "agent"])

        assert result.exit_code != 0
        # Should contain some field information in the error
        assert "id" in result.output.lower() or "validation" in result.output.lower()
