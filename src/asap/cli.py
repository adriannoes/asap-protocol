"""Command-line interface for ASAP Protocol utilities.

This module provides CLI commands for schema export and inspection.

Example:
    >>> # From terminal:
    >>> # asap --version
    >>> # asap export-schemas --output-dir ./schemas
    >>> # asap list-schemas
    >>> # asap show-schema agent
"""

import json
from pathlib import Path

import typer

from asap import __version__
from asap.schemas import export_all_schemas, get_schema_json, list_schema_entries

app = typer.Typer(help="ASAP Protocol CLI.")

# Default directory for schema operations
DEFAULT_SCHEMAS_DIR = Path("schemas")


def _version_callback(value: bool) -> None:
    """Print the version and exit when requested."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


VERSION_OPTION = typer.Option(
    False,
    "--version",
    help="Show ASAP Protocol version and exit.",
    callback=_version_callback,
    is_eager=True,
)

# Module-level singleton options to avoid B008 linting errors
OUTPUT_DIR_EXPORT_OPTION = typer.Option(
    DEFAULT_SCHEMAS_DIR,
    "--output-dir",
    help="Directory where JSON schemas will be written.",
)
OUTPUT_DIR_LIST_OPTION = typer.Option(
    DEFAULT_SCHEMAS_DIR,
    "--output-dir",
    help="Directory where JSON schemas are written.",
)


@app.callback()
def cli(version: bool = VERSION_OPTION) -> None:
    """ASAP Protocol CLI entrypoint."""


@app.command("export-schemas")
def export_schemas(
    output_dir: Path = OUTPUT_DIR_EXPORT_OPTION,
) -> None:
    """Export all ASAP JSON schemas to the output directory."""
    try:
        written_paths = export_all_schemas(output_dir)
        typer.echo(f"Exported {len(written_paths)} schemas to {output_dir}")
    except PermissionError as exc:
        raise typer.BadParameter(f"Cannot write to directory: {output_dir}") from exc
    except OSError as exc:
        raise typer.BadParameter(f"Failed to export schemas: {exc}") from exc


@app.command("list-schemas")
def list_schemas(
    output_dir: Path = OUTPUT_DIR_LIST_OPTION,
) -> None:
    """List available schema names and output paths."""
    entries = list_schema_entries(output_dir)
    for name, path in entries:
        typer.echo(f"{name}\t{path.relative_to(output_dir)}")


@app.command("show-schema")
def show_schema(schema_name: str) -> None:
    """Print the JSON schema for a named model."""
    try:
        schema = get_schema_json(schema_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(json.dumps(schema, indent=2))


def main() -> None:
    """Run the ASAP Protocol CLI."""
    app()


if __name__ == "__main__":
    main()
