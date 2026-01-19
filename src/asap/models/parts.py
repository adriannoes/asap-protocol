"""Part models for ASAP protocol content types.

Parts are atomic content units used within messages and artifacts.
They support different content types including text, structured data,
files, MCP resources, and parameterized templates.
"""

from typing import Annotated, Any, Literal, Union

from pydantic import Discriminator, Field, TypeAdapter

from asap.models.base import ASAPBaseModel


class TextPart(ASAPBaseModel):
    """Plain text content part.

    TextPart represents simple text content, such as user messages,
    agent responses, or any textual information.

    Attributes:
        type: Discriminator field, always "text"
        content: The text content

    Example:
        >>> part = TextPart(
        ...     type="text",
        ...     content="Research Q3 market trends for AI infrastructure"
        ... )
    """

    type: Literal["text"] = Field(..., description="Part type discriminator")
    content: str = Field(..., description="Text content")


class DataPart(ASAPBaseModel):
    """Structured JSON data part.

    DataPart represents structured data in JSON format, optionally
    with a schema URI for validation.

    Attributes:
        type: Discriminator field, always "data"
        data: Arbitrary JSON-serializable data
        schema_uri: Optional URI to JSON Schema for validation

    Example:
        >>> part = DataPart(
        ...     type="data",
        ...     data={"query": "AI trends", "max_results": 10},
        ...     schema_uri="https://example.com/schemas/search.json"
        ... )
    """

    type: Literal["data"] = Field(..., description="Part type discriminator")
    data: dict[str, Any] = Field(..., description="Structured data (JSON-serializable)")
    schema_uri: str | None = Field(
        default=None, description="Optional JSON Schema URI for validation"
    )


class FilePart(ASAPBaseModel):
    """Binary or text file part.

    FilePart represents file content, either by reference (URI) or
    inline (base64-encoded data). Includes MIME type for proper handling.

    Attributes:
        type: Discriminator field, always "file"
        uri: File URI (can be asap://, file://, https://, or data: URI)
        mime_type: MIME type of the file (e.g., "application/pdf")
        inline_data: Optional base64-encoded inline file data

    Example:
        >>> part = FilePart(
        ...     type="file",
        ...     uri="asap://artifacts/task_123/report.pdf",
        ...     mime_type="application/pdf"
        ... )
        >>>
        >>> # With inline data
        >>> part_inline = FilePart(
        ...     type="file",
        ...     uri="data:text/plain;base64,SGVsbG8gV29ybGQ=",
        ...     mime_type="text/plain",
        ...     inline_data="SGVsbG8gV29ybGQ="
        ... )
    """

    type: Literal["file"] = Field(..., description="Part type discriminator")
    uri: str = Field(..., description="File URI (asap://, file://, https://, data:)")
    mime_type: str = Field(..., description="MIME type (e.g., application/pdf)")
    inline_data: str | None = Field(
        default=None, description="Optional base64-encoded inline file data"
    )


class ResourcePart(ASAPBaseModel):
    """Reference to an MCP resource.

    ResourcePart represents a reference to a resource provided by
    an MCP (Model Context Protocol) server, enabling integration
    with external tools and data sources.

    Attributes:
        type: Discriminator field, always "resource"
        resource_uri: URI of the MCP resource

    Example:
        >>> part = ResourcePart(
        ...     type="resource",
        ...     resource_uri="mcp://tools.example.com/web/search_results"
        ... )
    """

    type: Literal["resource"] = Field(..., description="Part type discriminator")
    resource_uri: str = Field(..., description="MCP resource URI")


class TemplatePart(ASAPBaseModel):
    """Parameterized prompt template.

    TemplatePart represents a template string with variable placeholders
    (using {{variable}} syntax) and their corresponding values.

    Attributes:
        type: Discriminator field, always "template"
        template: Template string with {{variable}} placeholders
        variables: Dictionary mapping variable names to their values

    Example:
        >>> part = TemplatePart(
        ...     type="template",
        ...     template="Research {{topic}} for {{timeframe}}",
        ...     variables={"topic": "AI trends", "timeframe": "Q3 2025"}
        ... )
    """

    type: Literal["template"] = Field(..., description="Part type discriminator")
    template: str = Field(..., description="Template string with {{variable}} syntax")
    variables: dict[str, Any] = Field(..., description="Variable name to value mapping")


# Discriminated union type for type hints
PartType = Annotated[
    Union[TextPart, DataPart, FilePart, ResourcePart, TemplatePart], Discriminator("type")
]

# TypeAdapter for validation and deserialization
Part: TypeAdapter[PartType] = TypeAdapter(PartType)
"""TypeAdapter for Part discriminated union.

Part is a TypeAdapter that can validate and deserialize any of the five
part types: TextPart, DataPart, FilePart, ResourcePart, or TemplatePart.

The 'type' field is used as a discriminator to automatically deserialize
JSON data into the correct Part subtype.

Example:
    >>> from asap.models.parts import Part
    >>> 
    >>> # Deserializes to TextPart
    >>> text_part = Part.validate_python({"type": "text", "content": "Hello"})
    >>> 
    >>> # Deserializes to DataPart
    >>> data_part = Part.validate_python({"type": "data", "data": {"key": "value"}})
    >>> 
    >>> # Deserializes to FilePart
    >>> file_part = Part.validate_python({
    ...     "type": "file",
    ...     "uri": "file://test.pdf",
    ...     "mime_type": "application/pdf"
    ... })
"""
