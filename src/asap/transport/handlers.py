"""Handler registry for ASAP protocol payload processing.

This module provides a handler registry for dispatching ASAP envelopes
to appropriate handlers based on payload type.

The HandlerRegistry allows:
- Registration of handlers for specific payload types
- Dispatch of envelopes to registered handlers
- Discovery of registered payload types
- Structured logging for observability

Thread Safety:
    All operations on HandlerRegistry are thread-safe. The registry uses
    an internal RLock to protect concurrent access to the handler mapping.
    This allows safe usage in multi-threaded environments.

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

import asyncio
import inspect
import time
from collections.abc import Awaitable
from threading import RLock
from typing import Protocol, cast

from asap.errors import ASAPError
from asap.models.entities import Manifest
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest, TaskResponse
from asap.observability import get_logger

# Module logger
logger = get_logger(__name__)


class SyncHandler(Protocol):
    """Protocol for synchronous handlers."""

    def __call__(self, envelope: Envelope, manifest: Manifest) -> Envelope:
        """Process envelope synchronously.

        Args:
            envelope: The incoming ASAP envelope to process
            manifest: The server's manifest for context

        Returns:
            Response envelope to send back
        """
        ...


class AsyncHandler(Protocol):
    """Protocol for asynchronous handlers."""

    def __call__(self, envelope: Envelope, manifest: Manifest) -> Awaitable[Envelope]:
        """Process envelope asynchronously.

        Args:
            envelope: The incoming ASAP envelope to process
            manifest: The server's manifest for context

        Returns:
            Awaitable that resolves to response envelope
        """
        ...


# Type alias for handler functions (supports both sync and async)
Handler = SyncHandler | AsyncHandler
"""Type alias for ASAP message handlers.

A handler is a callable that receives an Envelope and a Manifest,
and returns a response Envelope (sync) or an awaitable that resolves
to a response Envelope (async).

Args:
    envelope: The incoming ASAP envelope to process
    manifest: The server's manifest for context

Returns:
    Response envelope to send back (sync) or awaitable (async)
"""


class HandlerNotFoundError(ASAPError):
    """Raised when no handler is registered for a payload type.

    This error occurs when attempting to dispatch an envelope with
    a payload_type that has no registered handler.

    Attributes:
        payload_type: The payload type that has no handler

    Example:
        >>> try:
        ...     raise HandlerNotFoundError("task.request")
        ... except HandlerNotFoundError as exc:
        ...     exc.payload_type
        'task.request'
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

    Thread Safety:
        All public methods are thread-safe. The registry uses an internal
        RLock to protect concurrent access to the handler mapping. This
        allows safe concurrent registration and dispatch operations from
        multiple threads.

    Attributes:
        _handlers: Internal mapping of payload_type to handler function
        _lock: Reentrant lock for thread-safe operations

    Example:
        >>> registry = HandlerRegistry()
        >>> registry.register("task.request", my_handler)
        >>> registry.has_handler("task.request")
        True
        >>> response = registry.dispatch(envelope, manifest)
    """

    def __init__(self) -> None:
        """Initialize empty handler registry with thread-safe lock."""
        self._handlers: dict[str, Handler] = {}
        self._lock = RLock()

    def register(self, payload_type: str, handler: Handler) -> None:
        """Register a handler for a payload type.

        If a handler is already registered for the payload type,
        it will be replaced with the new handler.

        This method is thread-safe.

        Args:
            payload_type: The payload type to handle (e.g., "task.request")
            handler: Callable that processes envelopes of this type

        Example:
            >>> registry = HandlerRegistry()
            >>> registry.register("task.request", create_echo_handler())
        """
        with self._lock:
            is_override = payload_type in self._handlers
            self._handlers[payload_type] = handler
            logger.debug(
                "asap.handler.registered",
                payload_type=payload_type,
                handler_name=handler.__name__ if hasattr(handler, "__name__") else str(handler),
                is_override=is_override,
            )

    def has_handler(self, payload_type: str) -> bool:
        """Check if a handler is registered for a payload type.

        This method is thread-safe.

        Args:
            payload_type: The payload type to check

        Returns:
            True if a handler is registered, False otherwise

        Example:
            >>> registry = HandlerRegistry()
            >>> registry.has_handler("task.request")
            False
        """
        with self._lock:
            return payload_type in self._handlers

    def dispatch(self, envelope: Envelope, manifest: Manifest) -> Envelope:
        """Dispatch an envelope to its registered handler.

        Looks up the handler for the envelope's payload_type and
        invokes it with the envelope and manifest.

        This method is thread-safe for handler lookup. The handler
        execution itself is not protected by the lock.

        Args:
            envelope: The incoming ASAP envelope
            manifest: The server's manifest for context

        Returns:
            Response envelope from the handler

        Raises:
            HandlerNotFoundError: If no handler is registered for the payload type

        Example:
            >>> registry = create_default_registry()
            >>> response = registry.dispatch(envelope, manifest)
        """
        payload_type = envelope.payload_type
        start_time = time.perf_counter()

        with self._lock:
            if payload_type not in self._handlers:
                logger.warning(
                    "asap.handler.not_found",
                    payload_type=payload_type,
                    envelope_id=envelope.id,
                )
                raise HandlerNotFoundError(payload_type)
            handler = self._handlers[payload_type]

        # Log dispatch start
        logger.debug(
            "asap.handler.dispatch",
            payload_type=payload_type,
            envelope_id=envelope.id,
            handler_name=handler.__name__ if hasattr(handler, "__name__") else str(handler),
        )

        # Execute handler outside the lock to allow concurrent dispatches
        try:
            # Note: dispatch() only works with sync handlers that return Envelope directly
            # For async handlers, use dispatch_async() instead
            # Type narrowing: we expect sync handlers here
            result = handler(envelope, manifest)
            # For sync handlers, result is Envelope directly
            if inspect.isawaitable(result):
                raise TypeError(
                    f"Handler {handler} returned awaitable in sync dispatch(). "
                    "Use dispatch_async() for async handlers."
                )
            response: Envelope = result
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                "asap.handler.completed",
                payload_type=payload_type,
                envelope_id=envelope.id,
                response_id=response.id,
                duration_ms=round(duration_ms, 2),
            )
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "asap.handler.error",
                payload_type=payload_type,
                envelope_id=envelope.id,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise

    async def dispatch_async(self, envelope: Envelope, manifest: Manifest) -> Envelope:
        """Dispatch an envelope to its registered handler (async version).

        This method supports both synchronous and asynchronous handlers.
        When called from an async context (e.g., FastAPI endpoint), this
        method will properly await async handlers and run sync handlers
        in a thread pool to avoid blocking the event loop.

        Args:
            envelope: The ASAP envelope to dispatch
            manifest: The server's manifest for context

        Returns:
            Response envelope from the handler

        Raises:
            HandlerNotFoundError: If no handler is registered for the payload type

        Example:
            >>> registry = create_default_registry()
            >>> response = await registry.dispatch_async(envelope, manifest)
        """
        payload_type = envelope.payload_type
        start_time = time.perf_counter()

        with self._lock:
            if payload_type not in self._handlers:
                logger.warning(
                    "asap.handler.not_found",
                    payload_type=payload_type,
                    envelope_id=envelope.id,
                )
                raise HandlerNotFoundError(payload_type)
            handler = self._handlers[payload_type]

        # Log dispatch start
        logger.debug(
            "asap.handler.dispatch",
            payload_type=payload_type,
            envelope_id=envelope.id,
            handler_name=handler.__name__ if hasattr(handler, "__name__") else str(handler),
        )

        # Execute handler outside the lock to allow concurrent dispatches
        try:
            # Support both sync and async handlers
            response: Envelope
            if inspect.iscoroutinefunction(handler):
                # Async handler - await it directly
                response = await handler(envelope, manifest)
            else:
                # Sync handler - run in thread pool to avoid blocking event loop
                # Also handle async callable objects that return awaitables
                loop = asyncio.get_event_loop()
                result: object = await loop.run_in_executor(None, handler, envelope, manifest)
                # Check if result is awaitable (handles async __call__ methods)
                if inspect.isawaitable(result):
                    response = await result
                else:
                    # Type narrowing: result is Envelope for sync handlers
                    # After checking it's not awaitable, we know it's Envelope
                    response = cast(Envelope, result)

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                "asap.handler.completed",
                payload_type=payload_type,
                envelope_id=envelope.id,
                response_id=response.id,
                duration_ms=round(duration_ms, 2),
            )
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "asap.handler.error",
                payload_type=payload_type,
                envelope_id=envelope.id,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration_ms, 2),
            )
            raise

    def list_handlers(self) -> list[str]:
        """List all registered payload types.

        This method is thread-safe. Returns a copy of the keys list.

        Returns:
            List of payload type strings that have registered handlers

        Example:
            >>> registry = create_default_registry()
            >>> registry.list_handlers()
            ['task.request']
        """
        with self._lock:
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
