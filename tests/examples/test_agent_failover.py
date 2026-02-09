"""Tests for agent_failover.py example.

Validates the failover pattern: primary agent does work and saves snapshots,
coordinator detects failure, sends StateRestore to backup agent.
All functions are tested in-process with mocked subprocesses and HTTP calls.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import httpx

from datetime import datetime, timezone

from asap.examples import agent_failover
from asap.models.entities import StateSnapshot
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest
from asap.state.stores.memory import InMemorySnapshotStore


class TestCreateFailoverWorkHandler:
    """Tests for _create_failover_work_handler."""

    def _make_request_envelope(
        self,
        skill_id: str = agent_failover.SKILL_FAILOVER_WORK,
        task_id: str = "task-001",
        step: int = 1,
    ) -> Envelope:
        """Build a task.request envelope for the failover handler."""
        return Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id=generate_id(),
                skill_id=skill_id,
                input={
                    agent_failover.KEY_TASK_ID: task_id,
                    agent_failover.KEY_STEP: step,
                },
            ).model_dump(),
        )

    def _make_manifest(self) -> agent_failover.Manifest:
        """Build a minimal manifest for testing."""
        return agent_failover.Manifest(
            id=agent_failover.WORKER_AGENT_ID,
            name="Test Worker",
            version="0.1.0",
            description="Test",
            capabilities=agent_failover.Capability(
                asap_version="0.1",
                skills=[
                    agent_failover.Skill(
                        id=agent_failover.SKILL_FAILOVER_WORK,
                        description="test",
                    )
                ],
            ),
            endpoints=agent_failover.Endpoint(asap="http://localhost:8001/asap"),
        )

    def test_handler_saves_snapshot_and_returns_completed(self) -> None:
        """Handler saves a snapshot and returns task.response with COMPLETED."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_failover_work_handler(store)
        envelope = self._make_request_envelope(task_id="task-42", step=3)
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        assert response.payload_type == "task.response"
        payload = response.payload or {}
        assert payload["status"] == "completed"
        assert payload["result"]["step"] == 3
        # Snapshot was persisted
        snap = store.get("task-42")
        assert snap is not None
        assert snap.data[agent_failover.KEY_STEP] == 3

    def test_handler_generates_task_id_when_missing(self) -> None:
        """Handler generates task_id when not provided in input."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_failover_work_handler(store)
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id=generate_id(),
                skill_id=agent_failover.SKILL_FAILOVER_WORK,
                input={agent_failover.KEY_STEP: 1},
            ).model_dump(),
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["status"] == "completed"
        # task_id was auto-generated (non-empty)
        assert payload["task_id"]

    def test_handler_rejects_unknown_skill(self) -> None:
        """Handler returns FAILED for unknown skill_id."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_failover_work_handler(store)
        envelope = self._make_request_envelope(skill_id="unknown_skill")
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["status"] == "failed"
        assert payload["result"]["error"] == "unknown_skill"

    def test_handler_sets_correlation_and_trace_ids(self) -> None:
        """Handler propagates correlation_id and trace_id."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_failover_work_handler(store)
        trace = str(generate_id())
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id=generate_id(),
                skill_id=agent_failover.SKILL_FAILOVER_WORK,
                input={
                    agent_failover.KEY_TASK_ID: "task-trace",
                    agent_failover.KEY_STEP: 1,
                },
            ).model_dump(),
            trace_id=trace,
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        assert response.correlation_id == envelope.id
        assert response.trace_id == trace


class TestCreateStateRestoreHandler:
    """Tests for _create_state_restore_handler."""

    def _make_manifest(self) -> agent_failover.Manifest:
        """Build a minimal manifest."""
        return agent_failover.Manifest(
            id=agent_failover.WORKER_AGENT_ID,
            name="Test",
            version="0.1.0",
            description="Test",
            capabilities=agent_failover.Capability(asap_version="0.1", skills=[]),
            endpoints=agent_failover.Endpoint(asap="http://localhost:8002/asap"),
        )

    def test_restore_succeeds_with_valid_snapshot(self) -> None:
        """Handler returns ok=True when snapshot exists and matches."""
        store = InMemorySnapshotStore()
        snap = StateSnapshot(
            id="snap-001",
            task_id="task-100",
            version=1,
            data={"step": 1},
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )
        store.save(snap)
        handler = agent_failover._create_state_restore_handler(store)
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="state_restore",
            payload={"task_id": "task-100", "snapshot_id": "snap-001"},
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["ok"] is True
        assert payload["task_id"] == "task-100"

    def test_restore_fails_when_missing_task_id(self) -> None:
        """Handler returns ok=False when task_id is missing."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_state_restore_handler(store)
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="state_restore",
            payload={"snapshot_id": "snap-001"},
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["ok"] is False
        assert "missing" in payload["error"]

    def test_restore_fails_when_missing_snapshot_id(self) -> None:
        """Handler returns ok=False when snapshot_id is missing."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_state_restore_handler(store)
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="state_restore",
            payload={"task_id": "task-100"},
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["ok"] is False

    def test_restore_fails_when_snapshot_not_found(self) -> None:
        """Handler returns ok=False when snapshot does not exist in store."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_state_restore_handler(store)
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="state_restore",
            payload={"task_id": "nonexistent", "snapshot_id": "snap-xxx"},
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["ok"] is False
        assert "not found" in payload["error"]

    def test_restore_fails_when_snapshot_id_mismatch(self) -> None:
        """Handler returns ok=False when snapshot exists but id does not match."""
        store = InMemorySnapshotStore()
        snap = StateSnapshot(
            id="snap-REAL",
            task_id="task-200",
            version=1,
            data={"step": 1},
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )
        store.save(snap)
        handler = agent_failover._create_state_restore_handler(store)
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="state_restore",
            payload={"task_id": "task-200", "snapshot_id": "snap-WRONG"},
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["ok"] is False

    def test_restore_handles_empty_payload(self) -> None:
        """Handler handles empty payload gracefully (no task_id/snapshot_id)."""
        store = InMemorySnapshotStore()
        handler = agent_failover._create_state_restore_handler(store)
        envelope = Envelope(
            asap_version="0.1",
            sender=agent_failover.COORDINATOR_AGENT_ID,
            recipient=agent_failover.WORKER_AGENT_ID,
            payload_type="state_restore",
            payload={},
        )
        manifest = self._make_manifest()

        response = handler(envelope, manifest)

        payload = response.payload or {}
        assert payload["ok"] is False
        assert "missing" in payload["error"]


class TestCreateWorkerApp:
    """Tests for create_worker_app."""

    def test_creates_fastapi_app(self) -> None:
        """create_worker_app returns a FastAPI application."""
        store = InMemorySnapshotStore()
        app = agent_failover.create_worker_app(
            port=9999,
            snapshot_store=store,
        )
        assert app is not None
        # App has routes registered
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/asap" in routes

    def test_creates_app_with_custom_endpoint(self) -> None:
        """create_worker_app accepts custom asap_endpoint."""
        store = InMemorySnapshotStore()
        app = agent_failover.create_worker_app(
            port=9999,
            asap_endpoint="http://custom:9999/asap",
            snapshot_store=store,
        )
        assert app is not None


class TestWaitReady:
    """Tests for _wait_ready helper."""

    def test_returns_true_on_200(self) -> None:
        """Returns True when endpoint returns 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(httpx, "get", return_value=mock_response):
            result = agent_failover._wait_ready("http://localhost:8001/health", timeout=1.0)
        assert result is True

    def test_returns_false_on_timeout(self) -> None:
        """Returns False when endpoint never returns 200."""
        with patch.object(httpx, "get", side_effect=httpx.ConnectError("refused")):
            result = agent_failover._wait_ready("http://localhost:8001/health", timeout=0.5)
        assert result is False


class TestHealthFailed:
    """Tests for _health_failed helper."""

    def test_returns_true_on_connection_error(self) -> None:
        """Returns True when connection fails."""
        with patch.object(httpx, "get", side_effect=httpx.ConnectError("refused")):
            assert agent_failover._health_failed("http://localhost:8001", timeout=1.0) is True

    def test_returns_true_on_500(self) -> None:
        """Returns True when endpoint returns 500."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        with patch.object(httpx, "get", return_value=mock_response):
            assert agent_failover._health_failed("http://localhost:8001", timeout=1.0) is True

    def test_returns_false_on_200(self) -> None:
        """Returns False when endpoint returns 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch.object(httpx, "get", return_value=mock_response):
            assert agent_failover._health_failed("http://localhost:8001", timeout=1.0) is False


class TestTerminate:
    """Tests for _terminate helper."""

    def test_terminate_already_exited(self) -> None:
        """Does nothing when process already exited."""
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = 0
        agent_failover._terminate(mock_proc)
        mock_proc.terminate.assert_not_called()

    def test_terminate_none(self) -> None:
        """Does nothing when process is None."""
        agent_failover._terminate(None)

    def test_terminate_sends_terminate(self) -> None:
        """Sends SIGTERM then waits."""
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.wait.return_value = 0
        agent_failover._terminate(mock_proc)
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()

    def test_terminate_kills_on_timeout(self) -> None:
        """Sends SIGKILL when wait times out."""
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.poll.return_value = None
        mock_proc.wait.side_effect = [subprocess.TimeoutExpired("cmd", 3), None]
        agent_failover._terminate(mock_proc)
        mock_proc.terminate.assert_called_once()
        mock_proc.kill.assert_called_once()


class TestParseArgs:
    """Tests for parse_args."""

    def test_worker_command(self) -> None:
        """Parses worker command with port."""
        args = agent_failover.parse_args(["worker", "--port", "9001"])
        assert args.command == "worker"
        assert args.port == 9001

    def test_worker_default_port(self) -> None:
        """Worker command uses default port when not specified."""
        args = agent_failover.parse_args(["worker"])
        assert args.port == agent_failover.PRIMARY_PORT

    def test_no_command_is_demo(self) -> None:
        """No subcommand means demo mode."""
        args = agent_failover.parse_args([])
        assert args.command is None


class TestMain:
    """Tests for main entry point."""

    def test_main_worker_calls_uvicorn(self) -> None:
        """main('worker') calls uvicorn.run with correct port."""
        mock_uvicorn = MagicMock()
        mock_app = MagicMock()
        with (
            patch.dict("sys.modules", {"uvicorn": mock_uvicorn}),
            patch(
                "asap.examples.agent_failover.create_worker_app",
                return_value=mock_app,
            ) as mock_create,
        ):
            agent_failover.main(["worker", "--port", "9999"])
            mock_create.assert_called_once_with(9999)
            mock_uvicorn.run.assert_called_once()
            call_args = mock_uvicorn.run.call_args
            assert call_args[1]["port"] == 9999

    def test_main_demo_calls_asyncio_run(self) -> None:
        """main() without subcommand calls asyncio.run(run_demo())."""
        with patch("asap.examples.agent_failover.asyncio.run") as mock_run:
            agent_failover.main([])
            mock_run.assert_called_once()


class TestStartWorkerProcess:
    """Tests for _start_worker_process helper."""

    def test_builds_correct_command(self) -> None:
        """Builds command with python executable and port."""
        import sys
        from pathlib import Path

        mock_popen = MagicMock(spec=subprocess.Popen)
        with patch(
            "asap.examples.agent_failover.subprocess.Popen", return_value=mock_popen
        ) as popen:
            agent_failover._start_worker_process(9001, Path("/tmp/test.db"))

            popen.assert_called_once()
            call_args = popen.call_args
            cmd = call_args[0][0]

            assert cmd[0] == sys.executable
            assert "-m" in cmd
            assert "asap.examples.agent_failover" in cmd
            assert "worker" in cmd
            assert "--port" in cmd
            assert "9001" in cmd

    def test_sets_sqlite_environment(self) -> None:
        """Sets ASAP_STORAGE_BACKEND and ASAP_STORAGE_PATH in env."""
        from pathlib import Path

        mock_popen = MagicMock(spec=subprocess.Popen)
        with patch(
            "asap.examples.agent_failover.subprocess.Popen", return_value=mock_popen
        ) as popen:
            agent_failover._start_worker_process(8001, Path("/data/shared.db"))

            popen.assert_called_once()
            call_kwargs = popen.call_args[1]
            env = call_kwargs["env"]

            assert env["ASAP_STORAGE_BACKEND"] == "sqlite"
            assert env["ASAP_STORAGE_PATH"] == "/data/shared.db"
            assert call_kwargs["text"] is True


class TestRunDemo:
    """Tests for run_demo async function."""

    @staticmethod
    def _make_task_response_envelope(
        task_id: str,
        snapshot_id: str,
    ) -> Envelope:
        """Build a task.response envelope with snapshot_id."""
        from asap.models.payloads import TaskResponse
        from asap.models.enums import TaskStatus

        return Envelope(
            asap_version="0.1",
            sender=agent_failover.WORKER_AGENT_ID,
            recipient=agent_failover.COORDINATOR_AGENT_ID,
            payload_type="task.response",
            payload=TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result={"step": 1, "snapshot_id": snapshot_id},
            ).model_dump(),
        )

    @staticmethod
    def _make_state_restore_ack_envelope(task_id: str, snapshot_id: str) -> Envelope:
        """Build a state_restore.ack envelope."""
        return Envelope(
            asap_version="0.1",
            sender=agent_failover.WORKER_AGENT_ID,
            recipient=agent_failover.COORDINATOR_AGENT_ID,
            payload_type="state_restore.ack",
            payload={"ok": True, "task_id": task_id, "snapshot_id": snapshot_id},
        )

    @staticmethod
    async def test_run_demo_orchestrates_failover_flow() -> None:
        """run_demo executes full failover: task -> kill -> restore."""
        from unittest.mock import AsyncMock

        # Mock Popen processes
        mock_primary = MagicMock(spec=subprocess.Popen)
        mock_backup = MagicMock(spec=subprocess.Popen)
        mock_primary.poll.return_value = None
        mock_backup.poll.return_value = None

        # Track which snapshot was saved
        saved_snapshot_id: str | None = None
        saved_task_id: str | None = None

        def mock_sqlite_get(task_id: str) -> StateSnapshot | None:
            nonlocal saved_task_id
            saved_task_id = task_id
            if saved_snapshot_id:
                return StateSnapshot(
                    id=saved_snapshot_id,
                    task_id=task_id,
                    version=1,
                    data={"step": 1},
                    checkpoint=True,
                    created_at=datetime.now(timezone.utc),
                )
            return None

        # Mock ASAPClient responses
        async def mock_send(envelope: Envelope) -> Envelope:
            nonlocal saved_snapshot_id
            if envelope.payload_type == "task.request":
                # First call: primary handles task
                task_id = (envelope.payload or {}).get("input", {}).get("task_id", "t1")
                saved_snapshot_id = f"snap-{task_id}"
                return TestRunDemo._make_task_response_envelope(task_id, saved_snapshot_id)
            if envelope.payload_type == "state_restore":
                # Second call: backup handles restore
                payload = envelope.payload or {}
                return TestRunDemo._make_state_restore_ack_envelope(
                    payload.get("task_id", ""),
                    payload.get("snapshot_id", ""),
                )
            raise ValueError(f"Unexpected payload_type: {envelope.payload_type}")

        mock_client = MagicMock()
        mock_client.send = AsyncMock(side_effect=mock_send)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Track health_failed calls
        health_failed_call_count = 0

        def mock_health_failed(base_url: str, timeout: float) -> bool:
            nonlocal health_failed_call_count
            health_failed_call_count += 1
            # First call returns True (primary is down)
            return True

        with (
            patch(
                "asap.examples.agent_failover._start_worker_process",
                side_effect=[mock_primary, mock_backup],
            ),
            patch("asap.examples.agent_failover._wait_ready", return_value=True),
            patch(
                "asap.examples.agent_failover._health_failed",
                side_effect=mock_health_failed,
            ),
            patch("asap.examples.agent_failover._terminate") as mock_terminate,
            patch(
                "asap.examples.agent_failover.ASAPClient",
                return_value=mock_client,
            ),
            patch(
                "asap.examples.agent_failover.SQLiteSnapshotStore",
            ) as mock_sqlite_cls,
        ):
            mock_sqlite_instance = MagicMock()
            mock_sqlite_instance.get = mock_sqlite_get
            mock_sqlite_cls.return_value = mock_sqlite_instance

            # Run the demo
            await agent_failover.run_demo()

            # Verify workflow executed
            assert mock_client.send.call_count == 2  # task.request + state_restore
            assert mock_terminate.call_count >= 2  # cleanup in finally


class TestModuleEntryPoint:
    """Tests for __main__ guard."""

    def test_module_calls_main_when_run_directly(self) -> None:
        """Running module as __main__ calls main()."""
        # The __main__ guard is trivial: `if __name__ == "__main__": main()`
        # We test by verifying the guard exists and would call main()
        import ast
        import inspect

        source = inspect.getsource(agent_failover)
        tree = ast.parse(source)

        # Find the if __name__ == "__main__" block
        main_guard_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition is __name__ == "__main__"
                test = node.test
                if isinstance(test, ast.Compare):
                    left = test.left
                    if (
                        isinstance(left, ast.Name)
                        and left.id == "__name__"
                        and len(test.ops) == 1
                        and isinstance(test.ops[0], ast.Eq)
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == "__main__"
                    ):
                        # Check body calls main()
                        for stmt in node.body:
                            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                                func = stmt.value.func
                                if isinstance(func, ast.Name) and func.id == "main":
                                    main_guard_found = True
                                    break

        assert main_guard_found, "Module should have 'if __name__ == \"__main__\": main()' guard"
