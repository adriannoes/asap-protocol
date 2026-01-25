"""Tests for bounded thread pool executor.

This module tests the BoundedExecutor class that limits concurrent thread usage
to prevent DoS attacks through resource exhaustion.
"""

import asyncio
import time
from typing import TYPE_CHECKING

import pytest

from asap.errors import ThreadPoolExhaustedError
from asap.transport.executors import BoundedExecutor

if TYPE_CHECKING:
    pass


class TestBoundedExecutor:
    """Test suite for BoundedExecutor."""

    def test_executor_accepts_tasks_within_limit(self) -> None:
        """Test that executor accepts tasks when within limit."""
        executor = BoundedExecutor(max_threads=2)

        def simple_task(x: int) -> int:
            return x * 2

        # Submit tasks within limit
        future1 = executor.submit(simple_task, 1)
        future2 = executor.submit(simple_task, 2)

        assert future1.result() == 2
        assert future2.result() == 4

        executor.shutdown()

    def test_executor_rejects_when_pool_exhausted(self) -> None:
        """Test that executor rejects tasks when pool is exhausted."""
        executor = BoundedExecutor(max_threads=2)

        # Use a lock to keep threads busy
        import threading

        lock = threading.Lock()
        lock.acquire()  # Lock is held

        def blocking_task() -> int:
            lock.acquire()  # This will block
            return 42

        # Fill the pool with blocking tasks
        future1 = executor.submit(blocking_task)
        future2 = executor.submit(blocking_task)

        # Give threads time to start
        time.sleep(0.1)

        # Third task should be rejected
        with pytest.raises(ThreadPoolExhaustedError) as exc_info:
            executor.submit(blocking_task)

        assert exc_info.value.max_threads == 2
        assert exc_info.value.active_threads == 2

        # Release lock to allow tasks to complete
        lock.release()
        lock.release()

        # Wait for tasks to complete
        future1.result()
        future2.result()

        executor.shutdown()

    @pytest.mark.asyncio
    async def test_executor_works_with_run_in_executor(self) -> None:
        """Test that executor works with asyncio.run_in_executor."""
        executor = BoundedExecutor(max_threads=2)

        def sync_task(x: int) -> int:
            return x * 3

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, sync_task, 5)

        assert result == 15

        executor.shutdown()

    @pytest.mark.asyncio
    async def test_executor_rejects_in_run_in_executor_when_exhausted(self) -> None:
        """Test that executor rejects tasks in run_in_executor when exhausted."""
        executor = BoundedExecutor(max_threads=2)

        import threading

        lock = threading.Lock()
        lock.acquire()  # Lock is held

        def blocking_task() -> int:
            lock.acquire()  # This will block
            return 42

        loop = asyncio.get_event_loop()

        # Fill the pool
        future1 = loop.run_in_executor(executor, blocking_task)
        future2 = loop.run_in_executor(executor, blocking_task)

        # Give threads time to start
        await asyncio.sleep(0.1)

        # Third task should be rejected
        with pytest.raises(ThreadPoolExhaustedError):
            await loop.run_in_executor(executor, blocking_task)

        # Release lock to allow tasks to complete
        lock.release()
        lock.release()

        # Wait for tasks to complete
        await future1
        await future2

        executor.shutdown()

    def test_executor_default_max_threads(self) -> None:
        """Test that executor uses default max_threads when None."""
        import os

        executor = BoundedExecutor(max_threads=None)
        cpu_count = os.cpu_count() or 1
        expected = min(32, cpu_count + 4)

        assert executor.max_threads == expected

        executor.shutdown()

    def test_executor_raises_on_invalid_max_threads(self) -> None:
        """Test that executor raises ValueError for invalid max_threads."""
        with pytest.raises(ValueError, match="max_threads must be >= 1"):
            BoundedExecutor(max_threads=0)

        with pytest.raises(ValueError, match="max_threads must be >= 1"):
            BoundedExecutor(max_threads=-1)

    def test_executor_context_manager(self) -> None:
        """Test that executor works as context manager."""
        with BoundedExecutor(max_threads=2) as executor:
            future = executor.submit(lambda x: x * 2, 5)
            assert future.result() == 10

        # Executor should be shut down after context exit
        # (Cannot easily test this without accessing private state)

    def test_executor_releases_semaphore_on_exception(self) -> None:
        """Test that executor releases semaphore even when task raises exception."""
        executor = BoundedExecutor(max_threads=1)

        def failing_task() -> int:
            raise ValueError("Task failed")

        # First task fails
        future1 = executor.submit(failing_task)
        with pytest.raises(ValueError, match="Task failed"):
            future1.result()

        # Semaphore should be released, so we can submit another task
        future2 = executor.submit(lambda: 42)
        assert future2.result() == 42

        executor.shutdown()


class TestBoundedExecutorStarvation:
    """Test suite for thread pool starvation scenarios."""

    @pytest.mark.asyncio
    async def test_starvation_n_plus_one_slow_tasks(self) -> None:
        """Test that N+1 slow tasks result in rejection of the extra task."""
        executor = BoundedExecutor(max_threads=3)

        import threading

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
