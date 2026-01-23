"""Schema export helpers for ASAP models.

This module provides utilities for exporting JSON schemas from ASAP
Pydantic models, enabling schema validation and tooling integration.

Example:
    >>> from asap.schemas import get_schema_json, list_schema_entries
    >>> schema = get_schema_json("agent")
    >>> schema["title"]
    'Agent'
"""

import json
from pathlib import Path

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

# Schema registry mapping names to model classes
SCHEMA_REGISTRY: dict[str, type[ASAPBaseModel]] = {
    "agent": Agent,
    "manifest": Manifest,
    "conversation": Conversation,
    "task": Task,
    "message": Message,
    "artifact": Artifact,
    "state_snapshot": StateSnapshot,
    "text_part": TextPart,
    "data_part": DataPart,
    "file_part": FilePart,
    "resource_part": ResourcePart,
    "template_part": TemplatePart,
    "task_request": TaskRequest,
    "task_response": TaskResponse,
    "task_update": TaskUpdate,
    "task_cancel": TaskCancel,
    "message_send": MessageSend,
    "state_query": StateQuery,
    "state_restore": StateRestore,
    "artifact_notify": ArtifactNotify,
    "mcp_tool_call": McpToolCall,
    "mcp_tool_result": McpToolResult,
    "mcp_resource_fetch": McpResourceFetch,
    "mcp_resource_data": McpResourceData,
    "envelope": Envelope,
}

# Total number of schemas in the registry
TOTAL_SCHEMA_COUNT = len(SCHEMA_REGISTRY)

# Schema output path mapping for directory organization
_SCHEMA_PATHS: dict[str, str] = {
    # Entities
    "agent": "entities/agent.schema.json",
    "manifest": "entities/manifest.schema.json",
    "conversation": "entities/conversation.schema.json",
    "task": "entities/task.schema.json",
    "message": "entities/message.schema.json",
    "artifact": "entities/artifact.schema.json",
    "state_snapshot": "entities/state_snapshot.schema.json",
    # Parts
    "text_part": "parts/text_part.schema.json",
    "data_part": "parts/data_part.schema.json",
    "file_part": "parts/file_part.schema.json",
    "resource_part": "parts/resource_part.schema.json",
    "template_part": "parts/template_part.schema.json",
    # Payloads
    "task_request": "payloads/task_request.schema.json",
    "task_response": "payloads/task_response.schema.json",
    "task_update": "payloads/task_update.schema.json",
    "task_cancel": "payloads/task_cancel.schema.json",
    "message_send": "payloads/message_send.schema.json",
    "state_query": "payloads/state_query.schema.json",
    "state_restore": "payloads/state_restore.schema.json",
    "artifact_notify": "payloads/artifact_notify.schema.json",
    "mcp_tool_call": "payloads/mcp_tool_call.schema.json",
    "mcp_tool_result": "payloads/mcp_tool_result.schema.json",
    "mcp_resource_fetch": "payloads/mcp_resource_fetch.schema.json",
    "mcp_resource_data": "payloads/mcp_resource_data.schema.json",
    # Envelope (root level)
    "envelope": "envelope.schema.json",
}


def list_schema_entries(output_dir: Path) -> list[tuple[str, Path]]:
    """List all available schema names and their output paths.

    Args:
        output_dir: Base directory where schemas are written.

    Returns:
        List of (schema_name, output_path) tuples.

    Example:
        >>> from pathlib import Path
        >>> entries = list_schema_entries(Path("schemas"))
        >>> any(name == "agent" for name, _ in entries)
        True
    """
    return [(name, output_dir / rel_path) for name, rel_path in _SCHEMA_PATHS.items()]


def get_schema_json(schema_name: str) -> dict[str, object]:
    """Return the JSON schema for a named model.

    Args:
        schema_name: Schema identifier (e.g., "agent", "task_request").

    Returns:
        JSON schema dictionary for the model.

    Raises:
        ValueError: If the schema name is not recognized.

    Example:
        >>> schema = get_schema_json("agent")
        >>> schema["title"]
        'Agent'
        >>> "properties" in schema
        True
    """
    if schema_name not in SCHEMA_REGISTRY:
        raise ValueError(f"Unknown schema name: {schema_name}")
    return SCHEMA_REGISTRY[schema_name].model_json_schema()


def export_schema(model_class: type[ASAPBaseModel], output_path: Path) -> Path:
    """Export JSON Schema for a model to a file.

    Creates parent directories if they don't exist. Overwrites existing files.

    Args:
        model_class: Pydantic model class to export.
        output_path: Path to write the schema file.

    Returns:
        The path that was written.

    Example:
        >>> from pathlib import Path
        >>> from asap.models import Agent
        >>> path = export_schema(Agent, Path("/tmp/agent.schema.json"))
        >>> path.exists()
        True
    """
    schema = model_class.model_json_schema()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return output_path


def export_all_schemas(output_dir: Path) -> list[Path]:
    """Export all ASAP model schemas to the given directory.

    Creates the directory structure (entities/, parts/, payloads/) and
    writes all schema files.

    Args:
        output_dir: Base directory to write schemas into.

    Returns:
        List of schema file paths that were written.

    Example:
        >>> from pathlib import Path
        >>> paths = export_all_schemas(Path("/tmp/schemas"))
        >>> len(paths) == 24
        True
    """
    written_paths: list[Path] = []

    for name, rel_path in _SCHEMA_PATHS.items():
        model_class = SCHEMA_REGISTRY[name]
        output_path = output_dir / rel_path
        written_paths.append(export_schema(model_class, output_path))

    return written_paths
