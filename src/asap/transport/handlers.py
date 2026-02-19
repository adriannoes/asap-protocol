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

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable
from concurrent.futures import Executor
from threading import RLock
from typing import TYPE_CHECKING, Callable, Protocol, Union, cast

if TYPE_CHECKING:
    from asap.state.metering import MeteringStore  # noqa: F401

from asap.economics.hooks import record_task_usage
from asap.errors import ASAPError
from asap.models.entities import Manifest
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest, TaskResponse
from asap.observability import get_logger, get_metrics
from asap.observability.tracing import handler_span_context

# Module logger
logger = get_logger(__name__)


class SyncHandler(Protocol):
    """Protocol for synchronous handlers."""

    def __call__(self, envelope: Envelope, manifest: Manifest) -> Envelope: ...


class AsyncHandler(Protocol):
    """Protocol for asynchronous handlers."""

    def __call__(self, envelope: Envelope, manifest: Manifest) -> Awaitable[Envelope]: ...


# Type alias for handler functions (supports both sync and async)
Handler = Union[SyncHandler, AsyncHandler]

# Type alias for factories that return a sync handler (useful in tests)
SyncHandlerFactory = Callable[[], SyncHandler]


def validate_handler(handler: Handler) -> None:
    """Validate that a handler has the required signature (envelope, manifest).

    Checks that the handler is callable and accepts exactly two parameters
    (envelope and manifest), matching the Handler protocol. Use when
    registering custom handlers to fail fast on invalid signatures.

    Args:
        handler: The handler callable to validate (sync or async).

    Raises:
        TypeError: If handler is not callable or does not have the required
            signature (two parameters for a function, or three for a bound
            callable with self/cls).

    Example:
        >>> validate_handler(create_echo_handler())
        >>> def bad(x, y, z): ...
        >>> validate_handler(bad)
        Traceback (most recent call last):
            ...
        TypeError: Handler must accept (envelope, manifest); got 3 parameters
    """
    if not callable(handler):
        raise TypeError("Handler must be callable")
    try:
        sig = inspect.signature(handler)
    except (ValueError, TypeError):
        raise TypeError("Handler signature could not be inspected") from None
    params = list(sig.parameters)
    # Allow (envelope, manifest) or (self, envelope, manifest) / (cls, envelope, manifest)
    if len(params) == 2 or len(params) == 3 and params[0] in ("self", "cls"):
        pass
    else:
        raise TypeError(
            f"Handler must accept (envelope, manifest); got {len(params)} parameters: {params}"
        )


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
        _executor: Optional executor for running sync handlers (for DoS prevention)

    Example:
        >>> registry = HandlerRegistry()
        >>> registry.register("task.request", my_handler)
        >>> registry.has_handler("task.request")
        True
        >>> response = registry.dispatch(envelope, manifest)
    """

    def __init__(
        self,
        executor: Executor | None = None,
        metering_store: object | None = None,
    ) -> None:
        self._handlers: dict[str, Handler] = {}
        self._lock = RLock()
        self._executor: Executor | None = executor
        self._metering_store = metering_store

    def register(self, payload_type: str, handler: Handler) -> None:
        validate_handler(handler)
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
        with self._lock:
            return payload_type in self._handlers

    def set_metering_store(self, store: object | None) -> None:
        """Set MeteringStore for usage recording (optional).

        When set, task.request completions are recorded to the store.
        """
        self._metering_store = store

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

        logger.debug(
            "asap.handler.dispatch",
            payload_type=payload_type,
            envelope_id=envelope.id,
            handler_name=handler.__name__ if hasattr(handler, "__name__") else str(handler),
        )

        try:
            result = handler(envelope, manifest)
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
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

        logger.debug(
            "asap.handler.dispatch",
            payload_type=payload_type,
            envelope_id=envelope.id,
            handler_name=handler.__name__ if hasattr(handler, "__name__") else str(handler),
        )

        agent_urn = manifest.id
        with handler_span_context(
            payload_type=payload_type,
            agent_urn=agent_urn,
            envelope_id=envelope.id,
        ):
            try:
                response: Envelope
                if inspect.iscoroutinefunction(handler):
                    response = await handler(envelope, manifest)
                else:
                    loop = asyncio.get_running_loop()
                    executor = self._executor if self._executor is not None else None
                    result: object = await loop.run_in_executor(
                        executor, handler, envelope, manifest
                    )
                    if inspect.isawaitable(result):
                        response = await result
                    else:
                        response = cast(Envelope, result)

                duration_ms = (time.perf_counter() - start_time) * 1000
                duration_seconds = duration_ms / 1000.0
                logger.debug(
                    "asap.handler.completed",
                    payload_type=payload_type,
                    envelope_id=envelope.id,
                    response_id=response.id,
                    duration_ms=round(duration_ms, 2),
                )
                metrics = get_metrics()
                metrics.increment_counter(
                    "asap_handler_executions_total",
                    {"payload_type": payload_type},
                )
                metrics.observe_histogram(
                    "asap_handler_duration_seconds",
                    duration_seconds,
                    {"payload_type": payload_type},
                )
                if self._metering_store is not None:
                    from asap.state.metering import MeteringStore

                    await record_task_usage(
                        cast(MeteringStore, self._metering_store),
                        envelope,
                        response,
                        duration_ms,
                        manifest,
                    )
                return response
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                get_metrics().increment_counter(
                    "asap_handler_errors_total",
                    {"payload_type": payload_type},
                )
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


def create_echo_handler() -> SyncHandler:
    """Create a synchronous echo handler that echoes TaskRequest input.

    The echo handler is a simple implementation that:
    - Receives a TaskRequest envelope
    - Returns a TaskResponse with the input echoed back
    - Preserves trace_id and sets correlation_id

    Returns SyncHandler (not Handler) so tests can use it without casting.
    This is useful for testing and as a base for custom handlers.

    Returns:
        SyncHandler that echoes TaskRequest input

    Example:
        >>> handler = create_echo_handler()
        >>> response = handler(request_envelope, manifest)
    """

    def echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        """Echo handler implementation."""
        # Parse the TaskRequest payload
        task_request = TaskRequest(**envelope.payload_dict)

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


def create_default_registry(
    metering_store: object | None = None,
) -> HandlerRegistry:
    """Create a registry with default handlers.

    Creates a HandlerRegistry pre-configured with standard handlers:
    - task.request: Echo handler (for basic testing)

    Additional handlers can be registered after creation.

    Args:
        metering_store: Optional MeteringStore for usage recording.

    Returns:
        HandlerRegistry with default handlers registered

    Example:
        >>> registry = create_default_registry()
        >>> registry.has_handler("task.request")
        True
    """
    registry = HandlerRegistry(metering_store=metering_store)
    registry.register("task.request", create_echo_handler())
    return registry
