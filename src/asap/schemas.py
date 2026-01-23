"""Schema export helpers for ASAP models."""

import json
from pathlib import Path
from typing import Iterable

from asap.models import (
    Agent,
    Artifact,
    ArtifactNotify,
    Conversation,
    DataPart,
    Envelope,
    FilePart,
    Manifest,
    McpResourceData,
    McpResourceFetch,
    McpToolCall,
    McpToolResult,
    Message,
    MessageSend,
    ResourcePart,
    StateQuery,
    StateRestore,
    StateSnapshot,
    Task,
    TaskCancel,
    TaskRequest,
    TaskResponse,
    TaskUpdate,
    TemplatePart,
    TextPart,
)
from asap.models.base import ASAPBaseModel


def list_schema_entries(output_dir: Path) -> list[tuple[str, Path]]:
    """List all available schema names and their output paths.

    Args:
        output_dir: Base directory where schemas are written.

    Returns:
        List of (schema_name, output_path) tuples.
    """
    return [(name, path) for name, _model, path in _schema_definitions(output_dir)]


def get_schema_json(schema_name: str) -> dict[str, object]:
    """Return the JSON schema for a named model.

    Args:
        schema_name: Schema identifier (e.g., "agent", "task_request").

    Returns:
        JSON schema dictionary for the model.

    Raises:
        ValueError: If the schema name is not recognized.
    """
    for name, model_class, _output_path in _schema_definitions(Path("schemas")):
        if name == schema_name:
            return model_class.model_json_schema()
    raise ValueError(f"Unknown schema name: {schema_name}")


def export_schema(model_class: type[ASAPBaseModel], output_path: Path) -> None:
    """Export JSON Schema for a model to a file.

    Args:
        model_class: Pydantic model class to export.
        output_path: Path to write the schema file.
    """
    schema = model_class.model_json_schema()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def export_all_schemas(output_dir: Path) -> list[Path]:
    """Export all ASAP model schemas to the given directory.

    Args:
        output_dir: Base directory to write schemas into.

    Returns:
        List of schema file paths that were written.
    """
    written_paths: list[Path] = []

    for _, model_class, output_path in _schema_definitions(output_dir):
        written_paths.append(_export_and_collect(model_class, output_path))

    return written_paths


def _export_and_collect(model_class: type[ASAPBaseModel], output_path: Path) -> Path:
    """Export schema and return the output path.

    Args:
        model_class: Pydantic model class to export.
        output_path: Path to write the schema file.

    Returns:
        The path that was written.
    """
    export_schema(model_class, output_path)
    return output_path


def _schema_definitions(output_dir: Path) -> Iterable[tuple[str, type[ASAPBaseModel], Path]]:
    """Return schema definitions with names, models, and output paths.

    Args:
        output_dir: Base directory where schemas are written.

    Returns:
        Iterable of (schema_name, model_class, output_path).
    """
    entities_dir = output_dir / "entities"
    parts_dir = output_dir / "parts"
    payloads_dir = output_dir / "payloads"

    return [
        ("agent", Agent, entities_dir / "agent.schema.json"),
        ("manifest", Manifest, entities_dir / "manifest.schema.json"),
        ("conversation", Conversation, entities_dir / "conversation.schema.json"),
        ("task", Task, entities_dir / "task.schema.json"),
        ("message", Message, entities_dir / "message.schema.json"),
        ("artifact", Artifact, entities_dir / "artifact.schema.json"),
        ("state_snapshot", StateSnapshot, entities_dir / "state_snapshot.schema.json"),
        ("text_part", TextPart, parts_dir / "text_part.schema.json"),
        ("data_part", DataPart, parts_dir / "data_part.schema.json"),
        ("file_part", FilePart, parts_dir / "file_part.schema.json"),
        ("resource_part", ResourcePart, parts_dir / "resource_part.schema.json"),
        ("template_part", TemplatePart, parts_dir / "template_part.schema.json"),
        ("task_request", TaskRequest, payloads_dir / "task_request.schema.json"),
        ("task_response", TaskResponse, payloads_dir / "task_response.schema.json"),
        ("task_update", TaskUpdate, payloads_dir / "task_update.schema.json"),
        ("task_cancel", TaskCancel, payloads_dir / "task_cancel.schema.json"),
        ("message_send", MessageSend, payloads_dir / "message_send.schema.json"),
        ("state_query", StateQuery, payloads_dir / "state_query.schema.json"),
        ("state_restore", StateRestore, payloads_dir / "state_restore.schema.json"),
        ("artifact_notify", ArtifactNotify, payloads_dir / "artifact_notify.schema.json"),
        ("mcp_tool_call", McpToolCall, payloads_dir / "mcp_tool_call.schema.json"),
        ("mcp_tool_result", McpToolResult, payloads_dir / "mcp_tool_result.schema.json"),
        ("mcp_resource_fetch", McpResourceFetch, payloads_dir / "mcp_resource_fetch.schema.json"),
        ("mcp_resource_data", McpResourceData, payloads_dir / "mcp_resource_data.schema.json"),
        ("envelope", Envelope, output_dir / "envelope.schema.json"),
    ]
