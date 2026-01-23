"""Tests for ASAP CLI."""

import json
from pathlib import Path

from typer.testing import CliRunner

from asap import __version__
from asap.cli import app


def test_cli_version_flag() -> None:
    """Ensure --version prints the package version."""
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_cli_export_schemas(tmp_path: Path) -> None:
    """Ensure export-schemas writes schema files."""
    runner = CliRunner()
    result = runner.invoke(app, ["export-schemas", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "entities" / "agent.schema.json").exists()
    assert (tmp_path / "payloads" / "task_request.schema.json").exists()
    assert (tmp_path / "envelope.schema.json").exists()


def test_cli_list_schemas() -> None:
    """Ensure list-schemas prints known schema names."""
    runner = CliRunner()
    result = runner.invoke(app, ["list-schemas"])

    assert result.exit_code == 0
    assert "agent\tentities/agent.schema.json" in result.stdout


def test_cli_show_schema() -> None:
    """Ensure show-schema prints valid JSON."""
    runner = CliRunner()
    result = runner.invoke(app, ["show-schema", "agent"])

    assert result.exit_code == 0
    schema = json.loads(result.stdout)
    assert schema["title"] == "Agent"


def test_cli_show_schema_unknown_name() -> None:
    """Ensure show-schema rejects unknown schema names."""
    runner = CliRunner()
    result = runner.invoke(app, ["show-schema", "not-a-schema"])

    assert result.exit_code != 0
