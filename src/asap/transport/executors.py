"""Bounded thread pool executor for DoS prevention.

This module provides a bounded executor that limits the number of concurrent
threads used for executing synchronous handlers. This prevents resource
exhaustion attacks by rejecting requests when the thread pool is full.

Example:
    >>> from asap.transport.executors import BoundedExecutor
    >>> executor = BoundedExecutor(max_threads=10)
    >>> result = await loop.run_in_executor(executor, sync_handler, arg1, arg2)
"""

import os
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from threading import Semaphore
from typing import Callable, TypeVar

from asap.errors import ThreadPoolExhaustedError
from asap.observability import get_logger, get_metrics

# Module logger
logger = get_logger(__name__)

# Type variable for function return type
T = TypeVar("T")


class BoundedExecutor(Executor):
    """Thread pool executor with bounded capacity for DoS prevention.

    This executor wraps a ThreadPoolExecutor and uses a semaphore to limit
    the number of concurrent tasks. When the limit is reached, submitting
    a new task raises ThreadPoolExhaustedError instead of queuing indefinitely.

    The executor prevents resource exhaustion by:
    - Limiting concurrent thread usage
    - Rejecting new tasks when capacity is reached (fail-fast)
    - Recording metrics for monitoring

    Attributes:
        _executor: Underlying ThreadPoolExecutor
        _semaphore: Semaphore controlling concurrent access
        max_threads: Maximum number of concurrent threads

    Example:
        >>> executor = BoundedExecutor(max_threads=10)
        >>> result = await loop.run_in_executor(executor, my_sync_function, arg1)
    """

    def __init__(self, max_threads: int | None = None) -> None:
        """Initialize bounded executor.

        Args:
            max_threads: Maximum number of concurrent threads.
                Defaults to min(32, os.cpu_count() + 4) if None.

        Raises:
            ValueError: If max_threads is less than 1
        """
        if max_threads is None:
            # Default: min(32, cpu_count + 4) following asyncio convention
            cpu_count = os.cpu_count() or 1
            max_threads = min(32, cpu_count + 4)

        if max_threads < 1:
            raise ValueError(f"max_threads must be >= 1, got {max_threads}")

        self.max_threads = max_threads
        self._executor = ThreadPoolExecutor(max_workers=max_threads)
        self._semaphore = Semaphore(max_threads)

        logger.info(
            "asap.executor.created",
            max_threads=max_threads,
            cpu_count=os.cpu_count(),
        )

    def submit(self, fn: Callable[..., T], /, *args: object, **kwargs: object) -> Future[T]:
        """Submit a function to be executed in the thread pool.

        This method acquires a semaphore permit before submitting to the
        executor. If no permit is available (pool is full), it raises
        ThreadPoolExhaustedError instead of blocking.

        The returned Future will automatically release the semaphore permit
        when the task completes (successfully or with an error).

        Args:
            fn: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Future representing the execution of the function

        Raises:
            ThreadPoolExhaustedError: If thread pool is exhausted

        Note:
            This method returns immediately with a Future. The function
            execution happens asynchronously in the thread pool.
        """
        # Try to acquire semaphore (non-blocking check)
        if not self._semaphore.acquire(blocking=False):
            # Pool is exhausted - record metric and raise error
            active_threads = self.max_threads - self._semaphore._value
            metrics = get_metrics()
            metrics.increment_counter(
                "asap_thread_pool_exhausted_total",
                labels=None,
                value=1.0,
            )

            logger.warning(
                "asap.executor.exhausted",
                max_threads=self.max_threads,
                active_threads=active_threads,
            )

            raise ThreadPoolExhaustedError(
                max_threads=self.max_threads,
                active_threads=active_threads,
            )

        # Submit to executor
        future = self._executor.submit(fn, *args, **kwargs)

        # Wrap future to release semaphore when done
        def release_on_done(f: Future[T]) -> None:
            """Release semaphore permit when future completes."""
            # Future is already done when callback is called, just release semaphore
            self._semaphore.release()

        # Add callback to release semaphore when future completes
        future.add_done_callback(release_on_done)

        return future

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """Shutdown the executor and release resources.

        Args:
            wait: If True, wait for all pending tasks to complete
            cancel_futures: If True, cancel pending futures (Python 3.9+)
        """
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)
        logger.info("asap.executor.shutdown", max_threads=self.max_threads)

    def __enter__(self) -> "BoundedExecutor":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit - shutdown executor."""
        self.shutdown(wait=True)
