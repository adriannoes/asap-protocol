"""Tests for thread pool bounds and exhaustion handling.

These tests validate that the server correctly handles thread pool exhaustion
by returning HTTP 503 (Service Temporarily Unavailable) when all threads are busy.

Rate limiting is automatically disabled for these tests via NoRateLimitTestBase
to prevent interference from rate limiting tests.
"""

import asyncio
import concurrent.futures
import threading
import time
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from asap.errors import ThreadPoolExhaustedError
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.enums import TaskStatus
from asap.models.payloads import TaskRequest, TaskResponse
from asap.transport.executors import BoundedExecutor
from asap.transport.handlers import HandlerRegistry
from asap.transport.jsonrpc import JsonRpcRequest
from asap.transport.server import create_app

if TYPE_CHECKING:
    pass


from ..conftest import NoRateLimitTestBase


class TestThreadPoolExhaustion(NoRateLimitTestBase):
    """Tests for thread pool exhaustion handling in /asap endpoint."""

    @pytest.fixture
    def manifest(self) -> Manifest:
        """Create a sample manifest for testing."""
        return Manifest(
            id="urn:asap:agent:test-threads",
            name="Test Thread Server",
            version="1.0.0",
            description="Test server for thread pool exhaustion",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )

    @pytest.fixture
    def slow_handler(self) -> object:
        """Create a slow sync handler that blocks."""
        lock = threading.Lock()
        lock.acquire()  # Lock is held initially

        def slow_sync_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            """Slow sync handler that blocks until lock is released."""
            lock.acquire()  # This will block
            return Envelope(
                asap_version="0.1",
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="task_123",
                    status=TaskStatus.COMPLETED,
                    result={},
                ).model_dump(),
                correlation_id=envelope.id,
            )

        # Store lock in handler for later release
        slow_sync_handler._lock = lock  # type: ignore[attr-defined]
        return slow_sync_handler

    def test_thread_pool_exhaustion_returns_503(
        self, manifest: Manifest, slow_handler: object
    ) -> None:
        """Test that thread pool exhaustion returns HTTP 503.

        Rate limiting is automatically disabled via NoRateLimitTestBase,
        so this test should pass even when run with other tests.
        """
        # Create completely isolated app for this test
        registry = HandlerRegistry()
        registry.register("task.request", slow_handler)

        # Create app with small thread pool (2 threads)
        # Rate limiting is automatically disabled via NoRateLimitTestBase
        app = create_app(manifest, registry=registry, max_threads=2)
        client = TestClient(app)

        # Create request envelope
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-threads",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            jsonrpc="2.0",
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="req-1",
        )

        request_data = rpc_request.model_dump(mode="json")

        # Start 2 requests in background threads that will block
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit 2 blocking requests
            future1 = executor.submit(
                client.post,
                "/asap",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )
            future2 = executor.submit(
                client.post,
                "/asap",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            # Give threads time to start and acquire semaphore
            time.sleep(0.2)

            # Third request should get 503 (pool exhausted)
            response3 = client.post(
                "/asap",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            assert response3.status_code == 503
            error_data = response3.json()
            assert "Service Temporarily Unavailable" in error_data["error"]
            assert error_data["code"] == "asap:transport/thread_pool_exhausted"
            assert "max_threads" in error_data["details"]

            # Release locks to allow tasks to complete
            lock = slow_handler._lock  # type: ignore[attr-defined]
            lock.release()
            lock.release()

            # Wait for first two requests to complete
            future1.result(timeout=5)
            future2.result(timeout=5)

    def test_bounded_executor_integration_direct(self, manifest: Manifest) -> None:
        """Test BoundedExecutor integration directly without HTTP layer.

        This test validates thread pool exhaustion without HTTP/rate limiting
        interference by testing the BoundedExecutor directly.
        """
        # Create bounded executor with 2 threads
        executor = BoundedExecutor(max_threads=2)

        # Create blocking function
        lock = threading.Lock()
        lock.acquire()  # Lock it initially

        def blocking_task() -> str:
            with lock:  # This will block
                return "completed"

        try:
            # Submit 2 tasks that will block
            executor.submit(blocking_task)
            executor.submit(blocking_task)

            # Give threads time to start
            time.sleep(0.1)

            # Third task should raise ThreadPoolExhaustedError
            with pytest.raises(ThreadPoolExhaustedError) as exc_info:
                executor.submit(blocking_task)

            assert "Thread pool exhausted" in str(exc_info.value)
            assert "2/2 threads in use" in str(exc_info.value)

        finally:
            # Release lock to allow cleanup
            lock.release()
            executor.shutdown(wait=True)


class TestBoundedExecutorStarvation(NoRateLimitTestBase):
    """Test suite for thread pool starvation scenarios."""

    @pytest.mark.asyncio
    async def test_starvation_n_plus_one_slow_tasks(self) -> None:
        """Test that N+1 slow tasks result in rejection of the extra task."""
        executor = BoundedExecutor(max_threads=3)

        # Create N+1 slow tasks (4 tasks, 3 threads)
        lock = threading.Lock()
        lock.acquire()  # Lock is held

        def slow_task(task_id: int) -> int:
            lock.acquire()  # Block until lock is released
            return task_id

        loop = asyncio.get_event_loop()

        # Submit N tasks (should succeed)
        futures = [loop.run_in_executor(executor, slow_task, i) for i in range(3)]

        # Give threads time to start
        await asyncio.sleep(0.1)

        # N+1th task should be rejected
        with pytest.raises(ThreadPoolExhaustedError) as exc_info:
            await loop.run_in_executor(executor, slow_task, 3)

        assert exc_info.value.max_threads == 3
        assert exc_info.value.active_threads == 3

        # Release locks to allow tasks to complete
        for _ in range(3):
            lock.release()

        # Wait for all tasks to complete
        results = await asyncio.gather(*futures)
        assert results == [0, 1, 2]

        executor.shutdown()
