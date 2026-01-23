"""Tests for ASAP CLI."""

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from asap import __version__
from asap.cli import DEFAULT_SCHEMAS_DIR, app
from asap.schemas import TOTAL_SCHEMA_COUNT


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
        assert "export-schemas" in result.stdout
        assert "list-schemas" in result.stdout
        assert "show-schema" in result.stdout

    def test_export_schemas_help(self) -> None:
        """Ensure export-schemas --help shows options."""
        runner = CliRunner()
        result = runner.invoke(app, ["export-schemas", "--help"])

        assert result.exit_code == 0
        assert "--output-dir" in result.stdout


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
