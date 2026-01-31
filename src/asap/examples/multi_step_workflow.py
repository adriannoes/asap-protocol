"""Multi-step workflow example for ASAP protocol.

This module demonstrates a pipeline of steps (fetch -> transform -> summarize)
where each step consumes input and produces output; state flows between steps.
Use this pattern for workflows that could be split across agents (each step
as a TaskRequest to a different agent) or run in-process.

Use case: Multi-agent pipelines, ETL-style workflows, or sequential task chains.

Run:
    uv run python -m asap.examples.multi_step_workflow
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from asap.models.ids import generate_id
from asap.observability import get_logger

logger = get_logger(__name__)


@dataclass
class WorkflowState:
    """State passed between workflow steps.

    In a distributed setup, this could be a TaskRequest input or
    TaskResponse result; here we keep it simple for the example.
    """

    step_name: str
    data: dict[str, Any]
    task_id: str | None = None


def make_step(name: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> Callable[[WorkflowState], WorkflowState]:
    """Wrap a function as a workflow step that takes and returns WorkflowState.

    Args:
        name: Step name for logging and state.
        fn: Function that takes input dict and returns output dict.

    Returns:
        Callable(WorkflowState) -> WorkflowState.
    """
    def step(state: WorkflowState) -> WorkflowState:
        out = fn(state.data)
        logger.info(
            "asap.multi_step_workflow.step",
            step_name=name,
            input_keys=list(state.data.keys()),
            output_keys=list(out.keys()),
        )
        return WorkflowState(step_name=name, data=out, task_id=state.task_id)

    return step


def run_workflow(
    initial_data: dict[str, Any],
    steps: Sequence[Callable[[WorkflowState], WorkflowState]],
    task_id: str | None = None,
) -> WorkflowState:
    """Run a linear workflow: initial_data -> step1 -> step2 -> ... -> final state.

    Args:
        initial_data: Input for the first step.
        steps: List of step functions (each takes WorkflowState, returns WorkflowState).
        task_id: Optional task ID for correlation.

    Returns:
        Final WorkflowState after all steps.
    """
    task_id = task_id or generate_id()
    state = WorkflowState(step_name="init", data=initial_data, task_id=task_id)
    for step in steps:
        state = step(state)
    logger.info(
        "asap.multi_step_workflow.complete",
        task_id=task_id,
        final_step=state.step_name,
    )
    return state


def run_demo() -> WorkflowState:
    """Run a demo workflow: fetch -> transform -> summarize."""
    def fetch(data: dict[str, Any]) -> dict[str, Any]:
        # Simulate fetching raw data
        return {"raw": ["item1", "item2", "item3"], "count": 3}

    def transform(data: dict[str, Any]) -> dict[str, Any]:
        # Simulate transforming data
        raw = data.get("raw", [])
        return {"transformed": [x.upper() for x in raw], "count": len(raw)}

    def summarize(data: dict[str, Any]) -> dict[str, Any]:
        # Simulate summarizing
        transformed = data.get("transformed", [])
        return {"summary": f"Processed {len(transformed)} items", "items": transformed}

    steps = [
        make_step("fetch", fetch),
        make_step("transform", transform),
        make_step("summarize", summarize),
    ]
    return run_workflow(initial_data={}, steps=steps)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the workflow demo."""
    parser = argparse.ArgumentParser(
        description="Multi-step workflow example (fetch -> transform -> summarize)."
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the multi-step workflow demo."""
    parse_args(argv)
    final = run_demo()
    logger.info(
        "asap.multi_step_workflow.demo_complete",
        final_data_keys=list(final.data.keys()),
        summary=final.data.get("summary"),
    )


if __name__ == "__main__":
    main()
