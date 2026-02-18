"""Agent failover example for ASAP protocol.

Demonstrates the failover pattern from Best Practices: Agent A (primary) runs a task
and saves snapshots; Agent A is simulated as unhealthy (process exit); coordinator
detects via GET /.well-known/asap/health; coordinator reads state from shared
storage and sends StateRestore to Agent B (backup); Agent B resumes the task.

Run the full demo (starts primary and backup workers, simulates crash, failover):

    uv run python -m asap.examples.agent_failover

Run a single worker (for manual testing; set ASAP_STORAGE_BACKEND=sqlite and
ASAP_STORAGE_PATH to a shared path for failover):

    uv run python -m asap.examples.agent_failover worker --port 8001
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path
from typing import Sequence

from fastapi import FastAPI

import httpx

from asap.models.entities import StateSnapshot
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import StateRestore, TaskRequest, TaskResponse
from asap.observability import get_logger
from asap.state.snapshot import SnapshotStore
from asap.state.stores import create_snapshot_store
from asap.state.stores.sqlite import SQLiteSnapshotStore
from asap.transport.client import ASAPClient
from asap.transport.handlers import HandlerRegistry, SyncHandler
from asap.transport.server import create_app
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.enums import TaskStatus
from datetime import datetime, timezone

logger = get_logger(__name__)

SKILL_FAILOVER_WORK = "failover_work"
KEY_STEP = "step"
KEY_TASK_ID = "task_id"
PRIMARY_PORT = 8001
BACKUP_PORT = 8002
HEALTH_PATH = "/.well-known/asap/health"
READY_TIMEOUT_SECONDS = 15.0
READY_POLL_INTERVAL_SECONDS = 0.3
HEALTH_FAIL_TIMEOUT_SECONDS = 5.0

WORKER_AGENT_ID = "urn:asap:agent:failover-worker"
COORDINATOR_AGENT_ID = "urn:asap:agent:coordinator"


def _create_failover_work_handler(store: SnapshotStore) -> SyncHandler:
    """Create a task.request handler that does one step and saves a snapshot."""

    def handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        req = TaskRequest(**envelope.payload_dict)
        if req.skill_id != SKILL_FAILOVER_WORK:
            return Envelope(
                asap_version=envelope.asap_version,
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="task.response",
                payload=TaskResponse(
                    task_id=req.input.get(KEY_TASK_ID, generate_id()),
                    status=TaskStatus.FAILED,
                    result={"error": "unknown_skill", "skill_id": req.skill_id},
                ).model_dump(),
                correlation_id=envelope.id,
                trace_id=envelope.trace_id,
            )
        task_id = req.input.get(KEY_TASK_ID) or str(generate_id())
        step = int(req.input.get(KEY_STEP, 1))
        snapshot = StateSnapshot(
            id=generate_id(),
            task_id=task_id,
            version=step,
            data={KEY_STEP: step, KEY_TASK_ID: task_id, "agent": manifest.id},
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )
        store.save(snapshot)
        logger.info(
            "asap.agent_failover.step_saved",
            task_id=task_id,
            step=step,
            snapshot_id=snapshot.id,
        )
        return Envelope(
            asap_version=envelope.asap_version,
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="task.response",
            payload=TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result={"step": step, "snapshot_id": snapshot.id},
            ).model_dump(),
            correlation_id=envelope.id,
            trace_id=envelope.trace_id,
        )

    return handler


def _create_state_restore_handler(store: SnapshotStore) -> SyncHandler:
    """Create a state_restore handler that loads snapshot from store and returns ack."""

    def handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        payload = envelope.payload_dict
        task_id = payload.get("task_id")
        snapshot_id = payload.get("snapshot_id")
        if not task_id or not snapshot_id:
            return Envelope(
                asap_version=envelope.asap_version,
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="state_restore.ack",
                payload={"ok": False, "error": "missing task_id or snapshot_id"},
                correlation_id=envelope.id,
                trace_id=envelope.trace_id,
            )
        snapshot = store.get(task_id)
        if snapshot is None or snapshot.id != snapshot_id:
            return Envelope(
                asap_version=envelope.asap_version,
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="state_restore.ack",
                payload={"ok": False, "error": "snapshot not found"},
                correlation_id=envelope.id,
                trace_id=envelope.trace_id,
            )
        logger.info(
            "asap.agent_failover.state_restored",
            task_id=task_id,
            snapshot_id=snapshot_id,
            step=snapshot.data.get(KEY_STEP),
        )
        return Envelope(
            asap_version=envelope.asap_version,
            sender=manifest.id,
            recipient=envelope.sender,
            payload_type="state_restore.ack",
            payload={"ok": True, "task_id": task_id, "snapshot_id": snapshot_id},
            correlation_id=envelope.id,
            trace_id=envelope.trace_id,
        )

    return handler


def create_worker_app(
    port: int,
    asap_endpoint: str | None = None,
    snapshot_store: SnapshotStore | None = None,
) -> FastAPI:
    """Create the FastAPI app for the failover worker (primary or backup).

    Uses create_snapshot_store() when snapshot_store is None (reads ASAP_STORAGE_*
    from env). Registers task.request (failover_work) and state_restore handlers.
    """
    base = f"http://127.0.0.1:{port}"
    endpoint = asap_endpoint or f"{base}/asap"
    manifest = Manifest(
        id=WORKER_AGENT_ID,
        name="Failover Worker",
        version="0.1.0",
        description="Worker that saves state for failover demo",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id=SKILL_FAILOVER_WORK, description="One-step work with snapshot")],
            state_persistence=True,
        ),
        endpoints=Endpoint(asap=endpoint),
    )
    store = snapshot_store or create_snapshot_store()
    registry = HandlerRegistry()
    registry.register("task.request", _create_failover_work_handler(store))
    registry.register("state_restore", _create_state_restore_handler(store))
    return create_app(manifest, registry, snapshot_store=store)


def _start_worker_process(port: int, db_path: Path) -> subprocess.Popen[str]:
    """Start a worker subprocess with shared SQLite storage."""
    env = os.environ.copy()
    env["ASAP_STORAGE_BACKEND"] = "sqlite"
    env["ASAP_STORAGE_PATH"] = str(db_path)
    cmd = [sys.executable, "-m", "asap.examples.agent_failover", "worker", "--port", str(port)]
    return subprocess.Popen(cmd, env=env, text=True)  # nosec B603


def _wait_ready(url: str, timeout: float) -> bool:
    """Return True if url returns 200 within timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(READY_POLL_INTERVAL_SECONDS)
    return False


def _health_failed(base_url: str, timeout: float) -> bool:
    """Return True if health endpoint is unreachable or returns 5xx."""
    try:
        r = httpx.get(f"{base_url}{HEALTH_PATH}", timeout=2.0)
        return r.status_code >= 500
    except httpx.HTTPError:
        return True


def _terminate(p: subprocess.Popen[str] | None) -> None:
    if p is None or p.poll() is not None:
        return
    p.terminate()
    try:
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(timeout=3)


async def run_demo() -> None:
    """Run failover demo: primary does work, crash, coordinator detects, StateRestore to backup."""
    with tempfile.TemporaryDirectory(prefix="asap_failover_") as tmp:
        db_path = Path(tmp) / "failover.db"
        primary_process = None
        backup_process = None

        try:
            primary_process = _start_worker_process(PRIMARY_PORT, db_path)
            backup_process = _start_worker_process(BACKUP_PORT, db_path)

            primary_base = f"http://127.0.0.1:{PRIMARY_PORT}"
            backup_base = f"http://127.0.0.1:{BACKUP_PORT}"

            if not _wait_ready(f"{primary_base}{HEALTH_PATH}", READY_TIMEOUT_SECONDS):
                raise RuntimeError("Primary worker did not become ready")
            if not _wait_ready(f"{backup_base}{HEALTH_PATH}", READY_TIMEOUT_SECONDS):
                raise RuntimeError("Backup worker did not become ready")

            task_id = str(generate_id())
            request_envelope = Envelope(
                asap_version="0.1",
                sender=COORDINATOR_AGENT_ID,
                recipient=WORKER_AGENT_ID,
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id=generate_id(),
                    skill_id=SKILL_FAILOVER_WORK,
                    input={KEY_TASK_ID: task_id, KEY_STEP: 1},
                ).model_dump(),
                trace_id=generate_id(),
            )

            async with ASAPClient(primary_base) as client:
                response = await client.send(request_envelope)
            if response.payload_type != "task.response":
                raise RuntimeError(f"Unexpected response type: {response.payload_type}")
            result = response.payload_dict.get("result") or {}
            snapshot_id = result.get("snapshot_id")
            if not snapshot_id:
                raise RuntimeError("Primary did not return snapshot_id")

            logger.info(
                "asap.agent_failover.primary_done",
                task_id=task_id,
                snapshot_id=snapshot_id,
            )

            _terminate(primary_process)
            primary_process = None

            deadline = time.monotonic() + HEALTH_FAIL_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                if _health_failed(primary_base, 1.0):
                    break
                await asyncio.sleep(READY_POLL_INTERVAL_SECONDS)
            else:
                raise RuntimeError("Primary health did not fail after termination")

            store = SQLiteSnapshotStore(db_path)
            snapshot = store.get(task_id)
            if snapshot is None:
                raise RuntimeError("Snapshot not found in shared store after primary exit")
            if snapshot.id != snapshot_id:
                snapshot_id = snapshot.id

            restore_envelope = Envelope(
                asap_version="0.1",
                sender=COORDINATOR_AGENT_ID,
                recipient=WORKER_AGENT_ID,
                payload_type="state_restore",
                payload=StateRestore(task_id=task_id, snapshot_id=snapshot_id).model_dump(),
                trace_id=generate_id(),
            )

            async with ASAPClient(backup_base) as client:
                ack = await client.send(restore_envelope)
            ack_payload = ack.payload_dict
            if ack_payload.get("ok") is not True:
                raise RuntimeError(f"Backup state_restore failed: {ack_payload}")

            logger.info(
                "asap.agent_failover.demo_complete",
                task_id=task_id,
                backup_ack=ack_payload,
            )
            print(
                "\nFailover demo complete: primary crashed, coordinator restored state on backup.\n"
            )
        finally:
            _terminate(primary_process)
            _terminate(backup_process)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent failover example: primary crash, coordinator restores state on backup."
    )
    sub = parser.add_subparsers(dest="command", help="Command")
    worker = sub.add_parser("worker", help="Run a single worker (use with ASAP_STORAGE_* env)")
    worker.add_argument(
        "--port",
        type=int,
        default=PRIMARY_PORT,
        help="Port to bind",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point: run demo or worker."""
    args = parse_args(argv)
    if args.command == "worker":
        import uvicorn

        port = args.port
        app = create_worker_app(port)
        uvicorn.run(app, host="127.0.0.1", port=port)
    else:
        asyncio.run(run_demo())


if __name__ == "__main__":
    main()
