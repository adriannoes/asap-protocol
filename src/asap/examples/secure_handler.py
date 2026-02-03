"""Secure handler example for ASAP protocol.

This module demonstrates proper input validation and security practices
when implementing ASAP handlers: validated payloads, FilePart URI validation,
and sanitized logging. See docs/security.md (Handler Security) for the full guide.
"""

from __future__ import annotations

from pydantic import ValidationError

from asap.errors import MalformedEnvelopeError
from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.parts import FilePart
from asap.models.payloads import TaskRequest, TaskResponse
from asap.models.enums import TaskStatus
from asap.observability import get_logger, sanitize_for_logging
from asap.transport.handlers import Handler

logger = get_logger(__name__)


def create_secure_handler() -> Handler:
    """Create a handler that validates input and sanitizes logs.

    The handler:
    - Parses payload with TaskRequest (raises MalformedEnvelopeError on invalid input)
    - Validates file parts with FilePart so URIs are checked (no path traversal, no file://)
    - Logs payload only after sanitize_for_logging() to avoid leaking secrets

    Returns:
        A handler callable (envelope, manifest) -> Envelope suitable for
        registry.register("task.request", ...).
    """

    def secure_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        try:
            task_request = TaskRequest(**envelope.payload)
        except ValidationError as e:
            raise MalformedEnvelopeError(
                reason="Invalid TaskRequest payload",
                details={"validation_errors": e.errors()},
            ) from e

        logger.debug(
            "secure_handler.request",
            payload_type=envelope.payload_type,
            payload=sanitize_for_logging(envelope.payload),
        )

        validated_uris: list[str] = []
        input_data = task_request.input or {}
        parts = input_data.get("parts") or []
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "file":
                try:
                    file_part = FilePart.model_validate(part)
                    validated_uris.append(file_part.uri)
                except ValidationError as e:
                    raise MalformedEnvelopeError(
                        reason="Invalid file part (e.g. path traversal or file:// not allowed)",
                        details={"validation_errors": e.errors()},
                    ) from e

        result = {"echoed": task_request.input, "validated_file_uris": validated_uris}
        response_payload = TaskResponse(
            task_id=f"task_{generate_id()}",
            status=TaskStatus.COMPLETED,
            result=result,
        )

        return Envelope(
            asap_version=envelope.asap_version,
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
            trace_id=envelope.trace_id,
        )

    return secure_handler
