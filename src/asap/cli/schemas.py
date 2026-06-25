"""`asap export-schemas` / `list-schemas` / `show-schema` / `validate-schema` commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import ValidationError

from asap.schemas import SCHEMA_REGISTRY, export_all_schemas, get_schema_json, list_schema_entries

# Default directory for schema operations
DEFAULT_SCHEMAS_DIR = Path("schemas")

# Verbose flag toggled by the root CLI callback (set from ``cli/__init__.py``).
_verbose: bool = False


def _detect_schema_type(data: dict[str, object]) -> str | None:
    """Attempt to auto-detect schema type from JSON data.

    Auto-detects envelope type if payload_type field is present.

    Args:
        data: Parsed JSON data.

    Returns:
        Detected schema type name or None if not detectable.
    """
    if "payload_type" in data and "asap_version" in data:
        return "envelope"
    return None


def _validate_against_schema(data: dict[str, object], schema_type: str) -> list[str]:
    """Validate JSON data against a registered schema.

    Args:
        data: Parsed JSON data to validate.
        schema_type: Schema type name from SCHEMA_REGISTRY.

    Returns:
        List of validation error messages (empty if valid).

    Raises:
        ValueError: If schema_type is not registered.
    """
    if schema_type not in SCHEMA_REGISTRY:
        raise ValueError(f"Unknown schema type: {schema_type}")

    model_class = SCHEMA_REGISTRY[schema_type]
    try:
        model_class.model_validate(data)
        return []
    except ValidationError as exc:
        errors: list[str] = []
        for error in exc.errors():
            loc = ".".join(str(part) for part in error["loc"])
            msg = error["msg"]
            errors.append(f"  - {loc}: {msg}")
        return errors


def register_schemas_commands(root: typer.Typer) -> None:
    """Register the schema commands (export/list/show/validate) on *root*."""

    @root.command("export-schemas")
    def export_schemas(
        output_dir: Annotated[
            Path,
            typer.Option("--output-dir", help="Directory where JSON schemas will be written."),
        ] = DEFAULT_SCHEMAS_DIR,
    ) -> None:
        """Export all ASAP JSON schemas to the output directory."""
        try:
            written_paths = export_all_schemas(output_dir)
            typer.echo(f"Exported {len(written_paths)} schemas to {output_dir}")
            if _verbose:
                for path in sorted(written_paths):
                    typer.echo(f"  - {path.relative_to(output_dir)}")
        except PermissionError as exc:
            raise typer.BadParameter(f"Cannot write to directory: {output_dir}") from exc
        except OSError as exc:
            raise typer.BadParameter(f"Failed to export schemas: {exc}") from exc

    @root.command("list-schemas")
    def list_schemas(
        output_dir: Annotated[
            Path,
            typer.Option("--output-dir", help="Directory where JSON schemas are written."),
        ] = DEFAULT_SCHEMAS_DIR,
    ) -> None:
        """List available schema names and output paths."""
        entries = list_schema_entries(output_dir)
        for name, path in entries:
            typer.echo(f"{name}\t{path.relative_to(output_dir)}")

    @root.command("show-schema")
    def show_schema(
        schema_name: Annotated[str, typer.Argument(help="Name of the schema to print.")],
    ) -> None:
        """Print the JSON schema for a named model."""
        try:
            schema = get_schema_json(schema_name)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

        typer.echo(json.dumps(schema, indent=2))

    @root.command("validate-schema")
    def validate_schema(
        file: Annotated[Path, typer.Argument(help="Path to JSON file to validate.")],
        schema_type: Annotated[
            Optional[str],
            typer.Option(
                "--schema-type",
                help="Schema type to validate against (e.g., agent, envelope, task_request).",
            ),
        ] = None,
    ) -> None:
        """Validate a JSON file against an ASAP schema.

        The schema type can be auto-detected for envelope files (those containing
        payload_type and asap_version fields). For other schema types, use the
        --schema-type option.
        """
        if not file.exists():
            raise typer.BadParameter(f"File not found: {file}")

        try:
            content = file.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise typer.BadParameter("JSON root must be an object")

        effective_schema_type = schema_type
        if effective_schema_type is None:
            effective_schema_type = _detect_schema_type(data)
            if effective_schema_type is None:
                raise typer.BadParameter(
                    "Cannot auto-detect schema type. Use --schema-type to specify."
                )

        try:
            errors = _validate_against_schema(data, effective_schema_type)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

        if errors:
            error_details = "\n".join(errors)
            raise typer.BadParameter(f"Validation error:\n{error_details}")

        typer.echo(f"Valid {effective_schema_type} schema: {file}")
