"""Multi-agent orchestration example for ASAP protocol.

This module demonstrates a main (orchestrator) agent delegating work to two
sub-agents, with explicit task coordination and state tracking. Use it as
a reference for building multi-agent workflows (3+ agents).

Scenario:
    - Orchestrator receives a high-level task, splits it into two sub-tasks.
    - Sub-agent A and Sub-agent B each handle one sub-task (e.g. "fetch" and "summarize").
    - Orchestrator coordinates order, collects results, and tracks state.

Run:
    Start two echo agents (or your own agents) on ports 8001 and 8002, then:
    uv run python -m asap.examples.orchestration --worker-a-url http://127.0.0.1:8001 --worker-b-url http://127.0.0.1:8002
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from typing import Any, Sequence

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest
from asap.observability import get_logger
from asap.observability.logging import bind_context, clear_context
from asap.transport.client import ASAPClient

logger = get_logger(__name__)

# Orchestrator (main agent)
ORCHESTRATOR_ID = "urn:asap:agent:orchestrator"
ORCHESTRATOR_NAME = "Orchestrator Agent"
ORCHESTRATOR_VERSION = "0.1.0"
ORCHESTRATOR_DESCRIPTION = "Coordinates tasks across two sub-agents"

# Sub-agents (default: two echo agents on different ports)
SUB_AGENT_A_ID = "urn:asap:agent:worker-a"
SUB_AGENT_B_ID = "urn:asap:agent:worker-b"
DEFAULT_WORKER_A_URL = "http://127.0.0.1:8001"
DEFAULT_WORKER_B_URL = "http://127.0.0.1:8002"


@dataclass
class OrchestrationState:
    """Tracks progress and results across the orchestration workflow.

    Used for task coordination and observability: which step we are in,
    what each sub-agent returned, and final status.
    """

    conversation_id: str
    trace_id: str
    step: str = "init"
    result_a: dict[str, Any] | None = None
    result_b: dict[str, Any] | None = None
    error: str | None = None
    completed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state for logging or persistence."""
        return {
            "conversation_id": self.conversation_id,
            "trace_id": self.trace_id,
            "step": self.step,
            "result_a": self.result_a,
            "result_b": self.result_b,
            "error": self.error,
            "completed": self.completed,
            "metadata": self.metadata,
        }


def build_orchestrator_manifest(asap_endpoint: str = "http://localhost:8000/asap") -> Manifest:
    """Build the manifest for the orchestrator agent.

    Args:
        asap_endpoint: URL where the orchestrator receives ASAP messages.

    Returns:
        Manifest describing the orchestrator's capabilities and endpoints.
    """
    return Manifest(
        id=ORCHESTRATOR_ID,
        name=ORCHESTRATOR_NAME,
        version=ORCHESTRATOR_VERSION,
        description=ORCHESTRATOR_DESCRIPTION,
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(
                    id="orchestrate", description="Delegate and coordinate work across sub-agents"
                ),
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=asap_endpoint),
    )


def build_task_envelope(
    recipient_id: str,
    skill_id: str,
    input_payload: dict[str, Any],
    conversation_id: str,
    trace_id: str,
    parent_task_id: str | None = None,
) -> Envelope:
    """Build a TaskRequest envelope for a sub-agent.

    Args:
        recipient_id: URN of the sub-agent.
        skill_id: Skill to invoke (e.g. "echo" for echo agents).
        input_payload: Input dict for the skill.
        conversation_id: Shared conversation ID for the workflow.
        trace_id: Shared trace ID for distributed tracing.
        parent_task_id: Optional parent task ID for hierarchy.

    Returns:
        Envelope ready to send via ASAPClient.
    """
    task_request = TaskRequest(
        conversation_id=conversation_id,
        parent_task_id=parent_task_id,
        skill_id=skill_id,
        input=input_payload,
    )
    return Envelope(
        asap_version="0.1",
        sender=ORCHESTRATOR_ID,
        recipient=recipient_id,
        payload_type="task.request",
        payload=task_request.model_dump(),
        trace_id=trace_id,
    )


async def send_to_sub_agent(
    client: ASAPClient,
    envelope: Envelope,
) -> Envelope:
    """Send an envelope to a sub-agent and return the response envelope.

    Uses the provided client so the caller can reuse a single ASAPClient
    instance for multiple requests (e.g. one client per worker in run_orchestration).

    Args:
        client: Open ASAPClient connected to the sub-agent (caller owns lifecycle).
        envelope: TaskRequest envelope to send.

    Returns:
        Response envelope from the sub-agent (e.g. TaskResponse).
    """
    return await client.send(envelope)


async def run_orchestration(
    worker_a_url: str = DEFAULT_WORKER_A_URL,
    worker_b_url: str = DEFAULT_WORKER_B_URL,
    input_a: dict[str, Any] | None = None,
    input_b: dict[str, Any] | None = None,
) -> OrchestrationState:
    """Run the orchestration: delegate to sub-agent A, then sub-agent B, and track state.

    Task coordination: steps run sequentially (A then B). State is updated after
    each response so you can inspect or persist progress.

    Args:
        worker_a_url: Base URL for sub-agent A.
        worker_b_url: Base URL for sub-agent B.
        input_a: Input payload for sub-agent A (default: step "a" message).
        input_b: Input payload for sub-agent B (default: step "b" message).

    Returns:
        Final orchestration state with both results and completion status.
    """
    conversation_id = generate_id()
    trace_id = generate_id()
    state = OrchestrationState(conversation_id=conversation_id, trace_id=trace_id)
    state.step = "start"
    state.metadata["worker_a_url"] = worker_a_url
    state.metadata["worker_b_url"] = worker_b_url

    payload_a = input_a if input_a is not None else {"step": "a", "message": "task for worker A"}
    payload_b = input_b if input_b is not None else {"step": "b", "message": "task for worker B"}

    bind_context(trace_id=trace_id, correlation_id=conversation_id)
    try:
        async with ASAPClient(worker_a_url) as client_a, ASAPClient(worker_b_url) as client_b:
            state.step = "sent_to_a"
            envelope_a = build_task_envelope(
                recipient_id=SUB_AGENT_A_ID,
                skill_id="echo",
                input_payload=payload_a,
                conversation_id=conversation_id,
                trace_id=trace_id,
            )
            logger.info(
                "asap.orchestration.sent_to_a",
                envelope_id=envelope_a.id,
                recipient=SUB_AGENT_A_ID,
            )
            try:
                response_a = await send_to_sub_agent(client_a, envelope_a)
                state.result_a = response_a.payload
                state.step = "received_from_a"
            except Exception as e:  # noqa: BLE001
                state.error = f"worker_a: {e!s}"
                state.step = "failed_at_a"
                clear_context()
                return state

            state.step = "sent_to_b"
            envelope_b = build_task_envelope(
                recipient_id=SUB_AGENT_B_ID,
                skill_id="echo",
                input_payload=payload_b,
                conversation_id=conversation_id,
                trace_id=trace_id,
            )
            logger.info(
                "asap.orchestration.sent_to_b",
                envelope_id=envelope_b.id,
                recipient=SUB_AGENT_B_ID,
            )
            try:
                response_b = await send_to_sub_agent(client_b, envelope_b)
                state.result_b = response_b.payload
                state.step = "received_from_b"
            except Exception as e:  # noqa: BLE001
                state.error = f"worker_b: {e!s}"
                state.step = "failed_at_b"
                clear_context()
                return state

        state.step = "completed"
        state.completed = True
        logger.info(
            "asap.orchestration.complete",
            conversation_id=conversation_id,
            state=state.to_dict(),
        )
    finally:
        clear_context()

    return state


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the orchestration demo.

    Args:
        argv: Optional list of CLI arguments for testing.

    Returns:
        Parsed argparse namespace.
    """
    parser = argparse.ArgumentParser(
        description="Run multi-agent orchestration (orchestrator + 2 sub-agents)."
    )
    parser.add_argument(
        "--worker-a-url",
        default=DEFAULT_WORKER_A_URL,
        help="Base URL for sub-agent A (e.g. echo agent on 8001).",
    )
    parser.add_argument(
        "--worker-b-url",
        default=DEFAULT_WORKER_B_URL,
        help="Base URL for sub-agent B (e.g. echo agent on 8002).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run a single orchestration round: delegate to worker A then B and print state."""
    args = parse_args(argv)
    state = asyncio.run(
        run_orchestration(
            worker_a_url=args.worker_a_url,
            worker_b_url=args.worker_b_url,
        )
    )
    logger.info("asap.orchestration.demo_complete", state=state.to_dict())
    if state.error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
