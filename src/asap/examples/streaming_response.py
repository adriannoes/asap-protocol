"""Streaming response example for ASAP protocol.

This module demonstrates how to simulate streaming task updates using
TaskUpdate payloads: yield progress updates (and optionally a final
TaskResponse) so clients can show real-time progress.

Use case: Long-running tasks that emit TaskUpdate (progress, status_change)
before sending a final TaskResponse.

Run:
    uv run python -m asap.examples.streaming_response
"""

from __future__ import annotations

import argparse
from typing import Any, Iterator, Sequence

from asap.models.enums import TaskStatus, UpdateType
from asap.models.ids import generate_id
from asap.models.payloads import TaskUpdate
from asap.observability import get_logger

logger = get_logger(__name__)


def stream_task_updates(
    task_id: str,
    num_chunks: int = 5,
    chunk_message_prefix: str = "Processing chunk",
) -> Iterator[TaskUpdate]:
    """Yield TaskUpdate payloads to simulate streaming progress.

    In a real implementation, each update would be sent over HTTP chunked
    response, WebSocket, or Server-Sent Events. Here we just yield in-process.

    Args:
        task_id: Task identifier.
        num_chunks: Number of progress updates to yield (1..num_chunks).
        chunk_message_prefix: Message prefix for progress updates.

    Yields:
        TaskUpdate with progress percent and message.
    """
    for i in range(1, num_chunks + 1):
        percent = (i * 100) // num_chunks
        update = TaskUpdate(
            task_id=task_id,
            update_type=UpdateType.PROGRESS,
            status=TaskStatus.WORKING,
            progress={
                "percent": percent,
                "message": f"{chunk_message_prefix} {i}/{num_chunks}",
            },
        )
        yield update
        logger.info(
            "asap.streaming_response.update",
            task_id=task_id,
            percent=percent,
            message=update.progress.get("message"),
        )


def run_demo(num_chunks: int = 5) -> list[dict[str, Any]]:
    """Run streaming demo: yield TaskUpdate payloads and collect them.

    Args:
        num_chunks: Number of progress chunks to stream.

    Returns:
        List of update payload dicts (for tests or inspection).
    """
    task_id = generate_id()
    updates: list[dict[str, Any]] = []
    for update in stream_task_updates(task_id, num_chunks=num_chunks):
        updates.append(update.model_dump())
    logger.info(
        "asap.streaming_response.demo_complete",
        task_id=task_id,
        num_updates=len(updates),
    )
    return updates


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the streaming demo."""
    parser = argparse.ArgumentParser(
        description="Streaming response example (TaskUpdate progress chunks)."
    )
    parser.add_argument(
        "--chunks",
        type=int,
        default=5,
        help="Number of progress chunks to stream.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the streaming response demo."""
    args = parse_args(argv)
    run_demo(num_chunks=args.chunks)


if __name__ == "__main__":
    main()
