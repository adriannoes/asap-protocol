"""Tests for DX examples (orchestration, long_running, error_recovery, etc.).

Each example is tested to run successfully and produce expected output
without requiring live servers (mocks or in-process demos only).
"""

from __future__ import annotations

from asap.examples import auth_patterns
from asap.testing import assert_envelope_valid
from asap.examples import error_recovery
from asap.examples import long_running
from asap.examples import mcp_integration
from asap.examples import multi_step_workflow
from asap.examples import orchestration
from asap.examples import rate_limiting
from asap.examples import state_migration
from asap.examples import streaming_response
from asap.examples import websocket_concept


class TestOrchestrationExample:
    """Tests for orchestration example."""

    def test_build_orchestrator_manifest_returns_manifest(self) -> None:
        """build_orchestrator_manifest returns a valid manifest."""
        manifest = orchestration.build_orchestrator_manifest()
        assert manifest.id == orchestration.ORCHESTRATOR_ID
        assert "orchestrate" in [s.id for s in manifest.capabilities.skills]

    def test_build_task_envelope_returns_envelope(self) -> None:
        """build_task_envelope returns envelope with task.request payload."""
        env = orchestration.build_task_envelope(
            recipient_id="urn:asap:agent:worker-a",
            skill_id="echo",
            input_payload={"msg": "hello"},
            conversation_id="conv-1",
            trace_id="trace-1",
        )
        assert_envelope_valid(env, allowed_payload_types=["task.request"])
        assert env.recipient == "urn:asap:agent:worker-a"
        assert env.payload.get("skill_id") == "echo"

    def test_orchestration_state_to_dict(self) -> None:
        """OrchestrationState.to_dict returns expected keys."""
        state = orchestration.OrchestrationState(
            conversation_id="c1",
            trace_id="t1",
            step="completed",
            result_a={"ok": True},
            result_b={"ok": True},
            completed=True,
        )
        d = state.to_dict()
        assert d["conversation_id"] == "c1"
        assert d["step"] == "completed"
        assert d["completed"] is True


class TestLongRunningExample:
    """Tests for long_running example."""

    def test_run_demo_completes(self) -> None:
        """run_demo runs without error (checkpoint, crash, resume, complete)."""
        long_running.run_demo(num_steps=3, crash_after_step=1)

    def test_run_steps_saves_snapshots(self) -> None:
        """run_steps saves snapshots to store."""
        store = long_running.InMemorySnapshotStore()
        task_id = "task-test-1"
        long_running.run_steps(store, task_id, num_steps=3, crash_after_step=2)
        latest = store.get(task_id, version=None)
        assert latest is not None
        assert latest.data[long_running.KEY_STEP] == 2

    def test_resume_from_store_continues_work(self) -> None:
        """resume_from_store continues from last snapshot."""
        store = long_running.InMemorySnapshotStore()
        task_id = "task-resume-1"
        long_running.run_steps(store, task_id, num_steps=5, crash_after_step=2)
        final = long_running.resume_from_store(store, task_id, num_steps=5)
        assert final is not None
        assert final.data[long_running.KEY_COMPLETED] is True
        assert final.data[long_running.KEY_STEP] == 5


class TestErrorRecoveryExample:
    """Tests for error_recovery example."""

    def test_run_demo_completes(self) -> None:
        """run_demo runs without error."""
        error_recovery.run_demo()

    def test_retry_with_backoff_succeeds_after_failures(self) -> None:
        """retry_with_backoff succeeds when fn eventually returns."""
        calls = 0

        def flaky() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ValueError("fail")
            return "ok"

        result = error_recovery.retry_with_backoff(
            flaky,
            max_retries=5,
            base_delay=0.01,
            max_delay=0.1,
        )
        assert result == "ok"
        assert calls == 3

    def test_with_fallback_returns_primary_when_ok(self) -> None:
        """with_fallback returns primary result when primary does not raise."""
        assert error_recovery.with_fallback(lambda: 42, lambda: 0) == 42

    def test_with_fallback_returns_fallback_on_error(self) -> None:
        """with_fallback returns fallback result when primary raises."""

        def fail() -> None:
            raise RuntimeError("fail")

        assert error_recovery.with_fallback(fail, lambda: 99) == 99


class TestMcpIntegrationExample:
    """Tests for mcp_integration example."""

    def test_run_demo_local_completes(self) -> None:
        """run_demo_local runs without error."""
        mcp_integration.run_demo_local()

    def test_build_mcp_tool_call_envelope(self) -> None:
        """build_mcp_tool_call_envelope returns envelope with mcp_tool_call."""
        env = mcp_integration.build_mcp_tool_call_envelope(
            tool_name="test_tool",
            arguments={"a": 1},
        )
        assert env.payload_type == "mcp_tool_call"
        assert env.payload.get("tool_name") == "test_tool"

    def test_build_mcp_tool_result_envelope(self) -> None:
        """build_mcp_tool_result_envelope returns envelope with mcp_tool_result."""
        env = mcp_integration.build_mcp_tool_result_envelope(
            request_id="req-1",
            success=True,
            result={"data": "ok"},
            correlation_id="corr-1",
        )
        assert env.payload_type == "mcp_tool_result"
        assert env.payload.get("success") is True
        assert env.correlation_id == "corr-1"


class TestStateMigrationExample:
    """Tests for state_migration example."""

    def test_run_demo_completes(self) -> None:
        """run_demo runs without error."""
        state_migration.run_demo()

    def test_move_state_between_agents_copies_snapshot(self) -> None:
        """move_state_between_agents copies snapshot from source to target store."""
        from asap.state.snapshot import InMemorySnapshotStore

        source = InMemorySnapshotStore()
        target = InMemorySnapshotStore()
        snap = state_migration.create_snapshot(
            task_id="t1",
            version=1,
            data={"x": 1},
        )
        source.save(snap)
        migrated = state_migration.move_state_between_agents(source, target, "t1")
        assert migrated is not None
        restored = target.get("t1", version=1)
        assert restored is not None
        assert restored.data == {"x": 1}


class TestAuthPatternsExample:
    """Tests for auth_patterns example."""

    def test_run_demo_completes(self) -> None:
        """run_demo runs without error."""
        auth_patterns.run_demo()

    def test_build_manifest_bearer_only_has_bearer_scheme(self) -> None:
        """build_manifest_bearer_only includes bearer in auth schemes."""
        manifest = auth_patterns.build_manifest_bearer_only()
        assert manifest.auth is not None
        assert "bearer" in manifest.auth.schemes

    def test_static_map_validator_returns_agent_id(self) -> None:
        """static_map_validator returns agent_id for known token."""
        validator = auth_patterns.static_map_validator({"tok": "urn:asap:agent:a"})
        assert validator("tok") == "urn:asap:agent:a"
        assert validator("unknown") is None


class TestRateLimitingExample:
    """Tests for rate_limiting example."""

    def test_run_demo_completes(self) -> None:
        """run_demo runs without error."""
        rate_limiting.run_demo()

    def test_get_server_rate_limit_config_returns_string(self) -> None:
        """get_server_rate_limit_config returns non-empty string."""
        config = rate_limiting.get_server_rate_limit_config()
        assert isinstance(config, str)
        assert "/" in config or len(config) > 0

    def test_per_sender_key_concept_uses_sender_when_known(self) -> None:
        """per_sender_key_concept returns sender URN when provided."""
        key = rate_limiting.per_sender_key_concept("urn:asap:agent:a", "127.0.0.1")
        assert key == "urn:asap:agent:a"

    def test_per_endpoint_limits_concept_returns_dict(self) -> None:
        """per_endpoint_limits_concept returns dict of limits."""
        limits = rate_limiting.per_endpoint_limits_concept()
        assert "asap" in limits
        assert "metrics" in limits


class TestWebsocketConceptExample:
    """Tests for websocket_concept example."""

    def test_run_demo_completes(self) -> None:
        """run_demo runs without error."""
        websocket_concept.run_demo()

    def test_get_events_endpoint_concept_returns_wss_url(self) -> None:
        """get_events_endpoint_concept returns example wss URL."""
        url = websocket_concept.get_events_endpoint_concept()
        assert url.startswith("wss://")


class TestStreamingResponseExample:
    """Tests for streaming_response example."""

    def test_run_demo_returns_list_of_updates(self) -> None:
        """run_demo returns list of TaskUpdate payload dicts."""
        updates = streaming_response.run_demo(num_chunks=4)
        assert len(updates) == 4
        assert updates[0].get("progress", {}).get("percent") == 25
        assert updates[-1].get("progress", {}).get("percent") == 100

    def test_stream_task_updates_yields_task_updates(self) -> None:
        """stream_task_updates yields TaskUpdate with progress."""
        task_id = "task-stream-1"
        updates = list(streaming_response.stream_task_updates(task_id, num_chunks=3))
        assert len(updates) == 3
        for u in updates:
            assert u.task_id == task_id
            assert u.update_type.value == "progress"
            assert u.progress is not None


class TestMultiStepWorkflowExample:
    """Tests for multi_step_workflow example."""

    def test_run_demo_completes_with_summary(self) -> None:
        """run_demo completes and final state has summary."""
        final = multi_step_workflow.run_demo()
        assert "summary" in final.data
        assert "Processed" in str(final.data["summary"])
        assert "items" in final.data

    def test_run_workflow_applies_steps_in_order(self) -> None:
        """run_workflow applies steps and returns final state."""

        def step_a(data: dict) -> dict:
            return {"a": 1}

        def step_b(data: dict) -> dict:
            return {**data, "b": 2}

        steps = [
            multi_step_workflow.make_step("a", step_a),
            multi_step_workflow.make_step("b", step_b),
        ]
        state = multi_step_workflow.run_workflow(initial_data={}, steps=steps)
        assert state.data == {"a": 1, "b": 2}
        assert state.step_name == "b"
