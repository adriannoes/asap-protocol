"""Command-line interface for ASAP Protocol utilities."""

import json
from pathlib import Path

import typer

from asap import __version__
from asap.schemas import export_all_schemas, get_schema_json, list_schema_entries

app = typer.Typer(help="ASAP Protocol CLI.")


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
OUTPUT_DIR_OPTION = typer.Option(
    Path("schemas"),
    "--output-dir",
    help="Directory where JSON schemas will be written.",
)
OUTPUT_DIR_LIST_OPTION = typer.Option(
    Path("schemas"),
    "--output-dir",
    help="Directory where JSON schemas are written.",
)


@app.callback()
def cli(version: bool = VERSION_OPTION) -> None:
    """ASAP Protocol CLI entrypoint."""


@app.command("export-schemas")
def export_schemas(
    output_dir: Path = OUTPUT_DIR_OPTION,
) -> None:
    """Export all ASAP JSON schemas to the output directory."""
    written_paths = export_all_schemas(output_dir)
    typer.echo(f"Exported {len(written_paths)} schemas to {output_dir}")


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
