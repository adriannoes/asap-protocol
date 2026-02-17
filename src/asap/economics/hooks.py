"""Metering hooks for capturing usage during task execution (v1.3).

Intercepts task lifecycle to record tokens, duration, and API calls.
Accepts agent-reported metrics from TaskResponse.metrics when available.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from asap.economics.metering import UsageMetrics
from asap.models.entities import Manifest
from asap.models.envelope import Envelope

if TYPE_CHECKING:
    from asap.state.metering import MeteringStore

# Keys used in TaskResponse.metrics for agent-reported usage
_METRICS_KEY_TOKENS_IN = "tokens_in"
_METRICS_KEY_TOKENS_OUT = "tokens_out"
_METRICS_KEY_API_CALLS = "api_calls"
_METRICS_KEY_TOKENS_USED = "tokens_used"  # Fallback: map to tokens_out


def _safe_int(value: object, default: int = 0) -> int:
    """Extract int from value, return default if invalid."""
    if value is None:
        return default
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, (float, str)):
        try:
            n = int(value)
            return n if n >= 0 else default
        except (ValueError, TypeError):
            pass
    return default


async def record_task_usage(
    store: "MeteringStore",
    envelope: Envelope,
    response_envelope: Envelope,
    duration_ms: float,
    manifest: Manifest,
) -> None:
    """Record usage event from a completed task.request -> task.response.

    Extracts task_id, agent_id, consumer_id from envelope/response.
    Uses measured duration_ms; tokens and api_calls from TaskResponse.metrics
    when the agent reports them.

    Args:
        store: MeteringStore to record the event.
        envelope: Incoming request envelope (task.request).
        response_envelope: Response envelope (task.response).
        duration_ms: Measured handler duration in milliseconds.
        manifest: Agent manifest (agent_id = manifest.id).

    Example:
        >>> await record_task_usage(store, req_env, resp_env, 1234.5, manifest)
    """
    if envelope.payload_type != "task.request":
        return
    if response_envelope.payload_type != "task.response":
        return

    payload = response_envelope.payload
    task_id = payload.get("task_id")
    if not task_id:
        return

    agent_id = manifest.id
    consumer_id = envelope.sender

    tokens_in = 0
    tokens_out = 0
    api_calls = 0

    metrics_dict = payload.get("metrics")
    if isinstance(metrics_dict, dict):
        tokens_in = _safe_int(metrics_dict.get(_METRICS_KEY_TOKENS_IN))
        tokens_out = _safe_int(metrics_dict.get(_METRICS_KEY_TOKENS_OUT))
        if tokens_out == 0:
            tokens_out = _safe_int(metrics_dict.get(_METRICS_KEY_TOKENS_USED))
        api_calls = _safe_int(metrics_dict.get(_METRICS_KEY_API_CALLS))

    duration_ms_int = int(round(duration_ms))
    if duration_ms_int < 0:
        duration_ms_int = 0

    usage = UsageMetrics(
        task_id=str(task_id),
        agent_id=agent_id,
        consumer_id=consumer_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=duration_ms_int,
        api_calls=api_calls,
        timestamp=datetime.now(timezone.utc),
    )

    event = usage.to_usage_event()
    await store.record(event)


def wrap_handler_with_metering(
    handler: "Handler",
    store: "MeteringStore | None",
    manifest: Manifest,
) -> "Handler":
    """Wrap a handler to record usage after task completion.

    When store is None, returns the original handler unchanged.
    When store is provided, returns a wrapper that:
    - Tracks start time
    - Calls the inner handler
    - On success for task.request, records usage to store
    - Returns the response

    Args:
        handler: The handler to wrap.
        store: Optional MeteringStore. If None, no wrapping.
        manifest: Agent manifest for agent_id.

    Returns:
        Wrapped handler (or original if store is None).
    """
    if store is None:
        return handler

    import inspect
    import time
    from typing import cast

    from asap.models.envelope import Envelope

    if inspect.iscoroutinefunction(handler):

        async def async_wrapper(
            envelope: Envelope,
            mf: Manifest,
        ) -> Envelope:
            start = time.perf_counter()
            result = await handler(envelope, mf)
            duration_ms = (time.perf_counter() - start) * 1000
            await record_task_usage(store, envelope, cast(Envelope, result), duration_ms, manifest)
            return cast(Envelope, result)

        return cast("Handler", async_wrapper)

    async def sync_wrapper(envelope: Envelope, mf: Manifest) -> Envelope:
        import asyncio

        loop = asyncio.get_running_loop()
        start = time.perf_counter()
        result = await loop.run_in_executor(None, handler, envelope, mf)
        duration_ms = (time.perf_counter() - start) * 1000
        await record_task_usage(store, envelope, cast(Envelope, result), duration_ms, manifest)
        return cast(Envelope, result)

    return cast("Handler", sync_wrapper)


if TYPE_CHECKING:
    from asap.transport.handlers import Handler
