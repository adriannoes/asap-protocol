"""Tests for CLI edge cases (export-schemas, validate-schema, trace, main)."""

from pathlib import Path

from typer.testing import CliRunner

from asap.cli import app, main


runner = CliRunner()


class TestExportSchemasVerbose:
    """Tests for export-schemas verbose output."""

    def test_export_schemas_verbose_lists_files(self, tmp_path: Path) -> None:
        """Verbose flag lists all exported schema files."""
        result = runner.invoke(app, ["--verbose", "export-schemas", "--output-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "Exported" in result.output
        assert "  - " in result.output

    def test_export_schemas_non_verbose_compact(self, tmp_path: Path) -> None:
        """Non-verbose does not list individual files."""
        result = runner.invoke(app, ["export-schemas", "--output-dir", str(tmp_path)])

        assert result.exit_code == 0
        assert "Exported" in result.output
        lines_with_dash = [
            line for line in result.output.split("\n") if line.strip().startswith("-")
        ]
        assert len(lines_with_dash) == 0


class TestValidateSchemaEdgeCases:
    """Tests for validate-schema edge cases."""

    def test_json_array_root_rejected(self, tmp_path: Path) -> None:
        """JSON arrays are rejected."""
        json_file = tmp_path / "array.json"
        json_file.write_text("[]")

        result = runner.invoke(
            app, ["validate-schema", str(json_file), "--schema-type", "envelope"]
        )

        assert result.exit_code != 0
        assert "must be an object" in result.output.lower()

    def test_json_string_root_rejected(self, tmp_path: Path) -> None:
        """JSON primitive values should be rejected."""
        json_file = tmp_path / "string.json"
        json_file.write_text('"just a string"')

        result = runner.invoke(
            app, ["validate-schema", str(json_file), "--schema-type", "envelope"]
        )

        assert result.exit_code != 0
        assert "must be an object" in result.output.lower()

    def test_json_number_root_rejected(self, tmp_path: Path) -> None:
        """JSON number values should be rejected."""
        json_file = tmp_path / "number.json"
        json_file.write_text("42")

        result = runner.invoke(
            app, ["validate-schema", str(json_file), "--schema-type", "envelope"]
        )

        assert result.exit_code != 0
        assert "must be an object" in result.output.lower()


class TestCliMain:
    """Tests for CLI main() and help."""

    def test_help_shows_usage(self) -> None:
        """--help shows usage and exits 0."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "ASAP Protocol CLI" in result.output or "Usage" in result.output

    def test_main_function_callable(self) -> None:
        """main() is callable."""
        assert callable(main)


class TestVersionFlag:
    """Tests for --version flag."""

    def test_version_flag_shows_version(self) -> None:
        """--version should display version and exit."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        # Should output a version string
        assert result.output.strip()  # Should have some output


class TestTraceEdgeCases:
    """Tests for trace command edge cases."""

    def test_trace_empty_trace_id_fails(self) -> None:
        """Empty trace_id fails with error."""
        result = runner.invoke(app, ["trace", "   "])
        assert result.exit_code != 0
        assert "trace_id is required" in result.output.lower()

    def test_trace_reads_from_stdin(self) -> None:
        """Trace reads from stdin when no log file given."""
        log_lines = (
            '{"event": "asap.request.received", "envelope_id": "e1", "trace_id": "stdin-trace", '
            '"sender": "urn:asap:agent:client", "recipient": "urn:asap:agent:echo", '
            '"timestamp": "2026-01-31T12:00:00Z"}\n'
            '{"event": "asap.request.processed", "envelope_id": "e1", "trace_id": "stdin-trace", '
            '"duration_ms": 10}\n'
        )
        result = runner.invoke(app, ["trace", "stdin-trace"], input=log_lines)
        assert result.exit_code == 0
        assert "client -> echo" in result.output

    def test_trace_oserror_reading_file(self, tmp_path: Path) -> None:
        """Trace command fails when log file cannot be read."""
        from unittest.mock import patch

        log_file = tmp_path / "asap.log"
        log_file.write_text("test content", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            result = runner.invoke(app, ["trace", "test-trace", "--log-file", str(log_file)])

        assert result.exit_code != 0
        assert "cannot read" in result.output.lower() or "permission" in result.output.lower()


class TestMainEntryPoint:
    """Tests for main() and __main__ block."""

    def test_main_invokes_app(self) -> None:
        """main() invokes the app."""
        from unittest.mock import MagicMock, patch

        mock_app = MagicMock()
        with patch("asap.cli.app", mock_app):
            main()
            mock_app.assert_called_once()

    def test_main_module_invocation(self) -> None:
        """main is defined and callable."""
        from asap import cli as cli_module

        assert hasattr(cli_module, "main")
        assert callable(cli_module.main)
