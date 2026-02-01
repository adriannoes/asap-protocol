# Multi-Agent Orchestration

**Time:** ~25 minutes | **Level:** Advanced

This tutorial shows how to coordinate multiple ASAP agents: an orchestrator delegates tasks to sub-agents, collects results, and tracks progress. You will build a workflow where three agents collaborate (orchestrator + two workers).

**Prerequisites:** [Building Your First Agent](first-agent.md), [Stateful Workflows](stateful-workflows.md)

---

## Overview

In multi-agent systems, one agent often acts as an **orchestrator** that:

- Receives a high-level task
- Splits it into sub-tasks
- Delegates each sub-task to a specialized agent
- Collects results and tracks state
- Combines outputs into a final response

ASAP supports this pattern via `TaskRequest`, `ASAPClient`, and shared `conversation_id` / `trace_id` for correlation.

---

## Step 1: Start the Worker Agents

You need at least two worker agents (echo agents or custom). In separate terminals:

```bash
# Terminal 1: Worker A on port 8001
uv run python -m asap.examples.echo_agent --host 127.0.0.1 --port 8001

# Terminal 2: Worker B on port 8002
uv run python -m asap.examples.echo_agent --host 127.0.0.1 --port 8002
```

Keep both running.

---

## Step 2: Run the Orchestration Demo

ASAP includes a multi-agent orchestration example:

```bash
uv run python -m asap.examples.orchestration --worker-a-url http://127.0.0.1:8001 --worker-b-url http://127.0.0.1:8002
```

**What happens:**

1. Orchestrator builds two `TaskRequest` envelopes (one for each worker).
2. Sends the first task to Worker A; waits for the response.
3. Sends the second task to Worker B; waits for the response.
4. Aggregates both results and reports completion.

Check the logs for `asap.orchestration.sent_to_a`, `asap.orchestration.sent_to_b`, and `asap.orchestration.complete`.

---

## Step 3: Build an Orchestrator

### Orchestration State

Track progress across sub-agents with a simple state object:

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class OrchestrationState:
    conversation_id: str
    trace_id: str
    step: str = "init"
    result_a: dict[str, Any] | None = None
    result_b: dict[str, Any] | None = None
    error: str | None = None
    completed: bool = False
```

### Task Envelope Builder

Build envelopes for sub-agents with shared `conversation_id` and `trace_id`:

```python
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest

ORCHESTRATOR_ID = "urn:asap:agent:orchestrator"
WORKER_A_ID = "urn:asap:agent:worker-a"
WORKER_B_ID = "urn:asap:agent:worker-b"


def build_task_envelope(
    recipient_id: str,
    skill_id: str,
    input_payload: dict[str, Any],
    conversation_id: str,
    trace_id: str,
) -> Envelope:
    request = TaskRequest(
        conversation_id=conversation_id,
        skill_id=skill_id,
        input=input_payload,
    )
    return Envelope(
        asap_version="0.1",
        sender=ORCHESTRATOR_ID,
        recipient=recipient_id,
        payload_type="task.request",
        payload=request.model_dump(),
        trace_id=trace_id,
    )
```

### Run Orchestration

Use one `ASAPClient` per worker for efficient connection reuse:

```python
import asyncio
from asap.transport.client import ASAPClient


async def run_orchestration(
    worker_a_url: str = "http://127.0.0.1:8001",
    worker_b_url: str = "http://127.0.0.1:8002",
) -> OrchestrationState:
    conversation_id = generate_id()
    trace_id = generate_id()
    state = OrchestrationState(conversation_id=conversation_id, trace_id=trace_id)

    async with ASAPClient(worker_a_url) as client_a, ASAPClient(worker_b_url) as client_b:
        # Step 1: delegate to Worker A
        envelope_a = build_task_envelope(
            recipient_id=WORKER_A_ID,
            skill_id="echo",
            input_payload={"step": "a", "message": "task for worker A"},
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
        response_a = await client_a.send(envelope_a)
        state.result_a = response_a.payload

        # Step 2: delegate to Worker B
        envelope_b = build_task_envelope(
            recipient_id=WORKER_B_ID,
            skill_id="echo",
            input_payload={"step": "b", "message": "task for worker B"},
            conversation_id=conversation_id,
            trace_id=trace_id,
        )
        response_b = await client_b.send(envelope_b)
        state.result_b = response_b.payload

    state.completed = True
    return state


if __name__ == "__main__":
    state = asyncio.run(run_orchestration())
    print("Result A:", state.result_a)
    print("Result B:", state.result_b)
```

---

## Step 4: Task Coordination Patterns

### Sequential (A then B)

The orchestrator sends to A, waits for the response, then sends to B. Output of A can be passed to B:

```python
# A's output feeds B's input
response_a = await client_a.send(envelope_a)
input_b = {"previous_result": response_a.payload, "step": "b"}
envelope_b = build_task_envelope(..., input_payload=input_b)
response_b = await client_b.send(envelope_b)
```

### Parallel (A and B concurrently)

Use `asyncio.gather` for concurrent delegation:

```python
async with ASAPClient(worker_a_url) as client_a, ASAPClient(worker_b_url) as client_b:
    envelope_a = build_task_envelope(...)
    envelope_b = build_task_envelope(...)
    response_a, response_b = await asyncio.gather(
        client_a.send(envelope_a),
        client_b.send(envelope_b),
    )
```

### Error Handling

Wrap sub-agent calls in try/except to avoid failing the whole orchestration:

```python
try:
    response_a = await client_a.send(envelope_a)
    state.result_a = response_a.payload
except Exception as e:
    state.error = f"worker_a: {e}"
    state.step = "failed_at_a"
    return state  # Abort early
```

---

## Step 5: Shared Context for Observability

Use `conversation_id` and `trace_id` consistently so logs and traces correlate:

```python
from asap.observability.logging import bind_context, clear_context

bind_context(trace_id=trace_id, correlation_id=conversation_id)
try:
    # All logs within this block will include trace_id and correlation_id
    response_a = await client_a.send(envelope_a)
finally:
    clear_context()
```

Distributed tracing tools can use these IDs to follow a request across agents.

---

## Best Practices

1. **One client per worker** — Reuse `ASAPClient` instances for multiple requests; avoid creating a new client per call.
2. **Shared IDs** — Use the same `conversation_id` and `trace_id` for all envelopes in a workflow.
3. **State tracking** — Maintain `OrchestrationState` or similar to inspect progress and handle failures.
4. **Error boundaries** — Catch exceptions from sub-agents and decide: retry, fallback, or fail the orchestration.

---

## Related Patterns

- **Multi-step workflow** — The `multi_step_workflow` example shows an in-process pipeline (fetch → transform → summarize). Each step could be delegated to a different agent.
- **State migration** — For long-running multi-agent tasks, use `StateSnapshot` and `SnapshotStore` to persist and resume orchestration state.

---

## Next Steps

- [Building Resilient Agents](resilience.md) — Retries, circuit breakers, recovery
- [Production Deployment Checklist](production-checklist.md) — Security, monitoring, scaling
- [State Management Guide](../state-management.md) — Task lifecycle, snapshots
