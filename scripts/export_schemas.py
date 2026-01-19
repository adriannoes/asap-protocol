#!/usr/bin/env python3
"""Export JSON Schema files for all ASAP models.

This script generates JSON Schema files for all ASAP protocol models,
organizing them by category in the schemas/ directory.

Usage:
    python scripts/export_schemas.py
"""

import json
from pathlib import Path

from asap.models import (
    Agent,
    ArtifactNotify,
    Artifact,
    Conversation,
    DataPart,
    Envelope,
    FilePart,
    McpResourceData,
    McpResourceFetch,
    McpToolCall,
    McpToolResult,
    Manifest,
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


def export_schema(model_class, output_path: Path) -> None:
    """Export JSON Schema for a model to a file.
    
    Args:
        model_class: Pydantic model class
        output_path: Path to write the schema file
    """
    schema = model_class.model_json_schema()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
    
    print(f"✅ Exported {model_class.__name__} -> {output_path}")


def main():
    """Export all ASAP model schemas."""
    # Base schemas directory
    schemas_dir = Path("schemas")
    
    print("🚀 Exporting ASAP Protocol JSON Schemas...\n")
    
    # Entities
    print("📦 Entities:")
    entities_dir = schemas_dir / "entities"
    export_schema(Agent, entities_dir / "agent.schema.json")
    export_schema(Manifest, entities_dir / "manifest.schema.json")
    export_schema(Conversation, entities_dir / "conversation.schema.json")
    export_schema(Task, entities_dir / "task.schema.json")
    export_schema(Message, entities_dir / "message.schema.json")
    export_schema(Artifact, entities_dir / "artifact.schema.json")
    export_schema(StateSnapshot, entities_dir / "state_snapshot.schema.json")
    
    # Parts
    print("\n🧩 Parts:")
    parts_dir = schemas_dir / "parts"
    export_schema(TextPart, parts_dir / "text_part.schema.json")
    export_schema(DataPart, parts_dir / "data_part.schema.json")
    export_schema(FilePart, parts_dir / "file_part.schema.json")
    export_schema(ResourcePart, parts_dir / "resource_part.schema.json")
    export_schema(TemplatePart, parts_dir / "template_part.schema.json")
    
    # Payloads - Task
    print("\n📨 Payloads (Task):")
    payloads_dir = schemas_dir / "payloads"
    export_schema(TaskRequest, payloads_dir / "task_request.schema.json")
    export_schema(TaskResponse, payloads_dir / "task_response.schema.json")
    export_schema(TaskUpdate, payloads_dir / "task_update.schema.json")
    export_schema(TaskCancel, payloads_dir / "task_cancel.schema.json")
    
    # Payloads - State & Message
    print("\n📨 Payloads (State & Message):")
    export_schema(MessageSend, payloads_dir / "message_send.schema.json")
    export_schema(StateQuery, payloads_dir / "state_query.schema.json")
    export_schema(StateRestore, payloads_dir / "state_restore.schema.json")
    export_schema(ArtifactNotify, payloads_dir / "artifact_notify.schema.json")
    
    # Payloads - MCP
    print("\n📨 Payloads (MCP):")
    export_schema(McpToolCall, payloads_dir / "mcp_tool_call.schema.json")
    export_schema(McpToolResult, payloads_dir / "mcp_tool_result.schema.json")
    export_schema(McpResourceFetch, payloads_dir / "mcp_resource_fetch.schema.json")
    export_schema(McpResourceData, payloads_dir / "mcp_resource_data.schema.json")
    
    # Envelope
    print("\n✉️  Envelope:")
    export_schema(Envelope, schemas_dir / "envelope.schema.json")
    
    print(f"\n✨ Successfully exported all schemas to {schemas_dir}/")
    print(f"📊 Total schemas: {len(list(schemas_dir.rglob('*.schema.json')))}")


if __name__ == "__main__":
    main()
