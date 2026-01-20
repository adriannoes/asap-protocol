"""Handler registry for ASAP protocol payload processing.

This module provides a handler registry for dispatching ASAP envelopes
to appropriate handlers based on payload type.

The HandlerRegistry allows:
- Registration of handlers for specific payload types
- Dispatch of envelopes to registered handlers
- Discovery of registered payload types

Example:
    >>> from asap.transport.handlers import HandlerRegistry, create_echo_handler
    >>> from asap.models.envelope import Envelope
    >>>
    >>> # Create registry and register handler
    >>> registry = HandlerRegistry()
    >>> registry.register("task.request", create_echo_handler())
    >>>
    >>> # Dispatch envelope to handler
    >>> response = registry.dispatch(envelope, manifest)
"""

from collections.abc import Callable

from asap.errors import ASAPError
from asap.models.entities import Manifest
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest, TaskResponse

# Type alias for handler functions
Handler = Callable[[Envelope, Manifest], Envelope]
"""Type alias for ASAP message handlers.

A handler is a callable that receives an Envelope and a Manifest,
and returns a response Envelope.

Args:
    envelope: The incoming ASAP envelope to process
    manifest: The server's manifest for context

Returns:
    Response envelope to send back
"""


class HandlerNotFoundError(ASAPError):
    """Raised when no handler is registered for a payload type.

    This error occurs when attempting to dispatch an envelope with
    a payload_type that has no registered handler.

    Attributes:
        payload_type: The payload type that has no handler
    """

    def __init__(self, payload_type: str) -> None:
        """Initialize handler not found error.

        Args:
            payload_type: The payload type that has no handler
        """
        message = f"No handler registered for payload type: {payload_type}"
        super().__init__(
            code="asap:transport/handler_not_found",
            message=message,
            details={"payload_type": payload_type},
        )
        self.payload_type = payload_type


class HandlerRegistry:
    """Registry for ASAP payload handlers.

    HandlerRegistry manages the mapping between payload types and their
    corresponding handlers. It provides methods for registration, dispatch,
    and discovery of handlers.

    Attributes:
        _handlers: Internal mapping of payload_type to handler function

    Example:
        >>> registry = HandlerRegistry()
        >>> registry.register("task.request", my_handler)
        >>> registry.has_handler("task.request")
        True
        >>> response = registry.dispatch(envelope, manifest)
    """

    def __init__(self) -> None:
        """Initialize empty handler registry."""
        self._handlers: dict[str, Handler] = {}

    def register(self, payload_type: str, handler: Handler) -> None:
        """Register a handler for a payload type.

        If a handler is already registered for the payload type,
        it will be replaced with the new handler.

        Args:
            payload_type: The payload type to handle (e.g., "task.request")
            handler: Callable that processes envelopes of this type
        """
        self._handlers[payload_type] = handler

    def has_handler(self, payload_type: str) -> bool:
        """Check if a handler is registered for a payload type.

        Args:
            payload_type: The payload type to check

        Returns:
            True if a handler is registered, False otherwise
        """
        return payload_type in self._handlers

    def dispatch(self, envelope: Envelope, manifest: Manifest) -> Envelope:
        """Dispatch an envelope to its registered handler.

        Looks up the handler for the envelope's payload_type and
        invokes it with the envelope and manifest.

        Args:
            envelope: The incoming ASAP envelope
            manifest: The server's manifest for context

        Returns:
            Response envelope from the handler

        Raises:
            HandlerNotFoundError: If no handler is registered for the payload type
        """
        payload_type = envelope.payload_type

        if payload_type not in self._handlers:
            raise HandlerNotFoundError(payload_type)

        handler = self._handlers[payload_type]
        return handler(envelope, manifest)

    def list_handlers(self) -> list[str]:
        """List all registered payload types.

        Returns:
            List of payload type strings that have registered handlers
        """
        return list(self._handlers.keys())


def create_echo_handler() -> Handler:
    """Create an echo handler that echoes TaskRequest input.

    The echo handler is a simple implementation that:
    - Receives a TaskRequest envelope
    - Returns a TaskResponse with the input echoed back
    - Preserves trace_id and sets correlation_id

    This is useful for testing and as a base for custom handlers.

    Returns:
        Handler function that echoes TaskRequest input

    Example:
        >>> handler = create_echo_handler()
        >>> response = handler(request_envelope, manifest)
    """

    def echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        """Echo handler implementation."""
        # Parse the TaskRequest payload
        task_request = TaskRequest(**envelope.payload)

        # Create response with echoed input
        response_payload = TaskResponse(
            task_id=f"task_{generate_id()}",
            status=TaskStatus.COMPLETED,
            result={"echoed": task_request.input},
        )

        # Create response envelope
        return Envelope(
            asap_version=envelope.asap_version,
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
            trace_id=envelope.trace_id,
        )

    return echo_handler


def create_default_registry() -> HandlerRegistry:
    """Create a registry with default handlers.

    Creates a HandlerRegistry pre-configured with standard handlers:
    - task.request: Echo handler (for basic testing)

    Additional handlers can be registered after creation.

    Returns:
        HandlerRegistry with default handlers registered

    Example:
        >>> registry = create_default_registry()
        >>> registry.has_handler("task.request")
        True
    """
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    return registry
