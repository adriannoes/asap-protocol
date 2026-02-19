"""Part models for ASAP protocol content types.

Parts are atomic content units used within messages and artifacts.
They support different content types including text, structured data,
files, MCP resources, and parameterized templates.
"""

from __future__ import annotations

import base64
import re
from typing import Annotated, Any, Literal, Union

from pydantic import Discriminator, Field, TypeAdapter, field_validator

from asap.models.base import ASAPBaseModel
from asap.models.types import MIMEType

# Security: reject URIs that could lead to path traversal or local file access
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.")
FILE_URI_PREFIX = "file://"


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
        uri: File URI (asap://, https://, or data:; file:// and path traversal rejected)
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
    uri: str = Field(
        ...,
        description="File URI (asap://, https://, data:; file:// and .. rejected)",
    )
    mime_type: MIMEType = Field(..., description="MIME type (e.g., application/pdf)")
    inline_data: str | None = Field(
        default=None, description="Optional base64-encoded inline file data"
    )

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        """Validate URI: reject path traversal and suspicious file:// URIs.

        Rejects URIs containing '..' (path traversal) and file:// URIs
        to prevent reading arbitrary server paths from user-supplied input.

        Args:
            v: URI string to validate

        Returns:
            The same URI if valid

        Raises:
            ValueError: If URI contains path traversal or is a file:// URI
        """
        if PATH_TRAVERSAL_PATTERN.search(v):
            raise ValueError(f"URI must not contain path traversal (..): {v!r}")
        if v.strip().lower().startswith(FILE_URI_PREFIX):
            raise ValueError("file:// URIs are not allowed for security (path traversal risk)")
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        """Validate MIME type format (type/subtype)."""
        # Pattern: type/subtype where both parts can contain alphanumeric, dots, plus, and hyphens
        if not re.match(r"^[a-z0-9-]+/[a-z0-9.+\-]+$", v.lower()):
            raise ValueError(f"Invalid MIME type format: {v}")
        return v

    @field_validator("inline_data")
    @classmethod
    def validate_base64(cls, v: str | None) -> str | None:
        """Validate that inline_data is valid base64 when provided.

        Args:
            v: Base64 string or None

        Returns:
            Base64 string after validation

        Raises:
            ValueError: If inline_data is not valid base64
        """
        if v is not None:
            try:
                base64.b64decode(v, validate=True)
            except Exception as e:
                raise ValueError(f"inline_data must be valid base64: {e}") from e
        return v


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
    ...     "uri": "https://example.com/doc.pdf",
    ...     "mime_type": "application/pdf"
    ... })
"""
