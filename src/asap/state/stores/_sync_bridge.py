"""Sync->async bridge for the synchronous :class:`SQLiteSnapshotStore` (v2.5.1 S1).

``SQLiteSnapshotStore`` exposes a *synchronous* :class:`~asap.state.snapshot.SnapshotStore`
interface but the backend is async (``aiosqlite``); ``_run_sync`` bridges that. When
no event loop is running it uses ``asyncio.run``; when a loop is running (e.g. inside
a FastAPI handler) it submits the coroutine to a shared 4-worker thread pool so the
caller's loop is not blocked and we do not create a per-call executor.

The coroutine wrappers keep a reference to the backend's impl methods so the sync
store stays a thin facade over the async backend.
"""

from __future__ import annotations

import asyncio
import atexit
import concurrent.futures
from typing import Any, Protocol, runtime_checkable

from asap.models.entities import StateSnapshot
from asap.models.types import TaskID

# Shared executor for the sync bridge when called from a running loop. Reused
# across all DB operations to avoid per-call ThreadPoolExecutor creation.
_SYNC_BRIDGE_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None


@runtime_checkable
class _SnapshotBackendProtocol(Protocol):
    """Structural surface the coroutine wrappers call on a snapshot backend.

    Defined locally (rather than importing ``_SQLiteSnapshotBackend``) to avoid an
    import cycle: ``sqlite`` imports this module, so this module must not import
    ``sqlite``. The methods match ``_SQLiteSnapshotBackend`` verbatim.
    """

    async def _save_impl(self, snapshot: StateSnapshot) -> None: ...

    async def _get_impl(
        self,
        task_id: TaskID,
        version: int | None,
    ) -> StateSnapshot | None: ...

    async def _list_versions_impl(self, task_id: TaskID) -> list[int]: ...

    async def _delete_impl(
        self,
        task_id: TaskID,
        version: int | None,
    ) -> bool: ...


def _shutdown_sync_bridge_executor() -> None:
    """Best-effort shutdown for test suites and clean interpreter exit."""
    global _SYNC_BRIDGE_EXECUTOR
    if _SYNC_BRIDGE_EXECUTOR is not None:
        _SYNC_BRIDGE_EXECUTOR.shutdown(wait=False)
        _SYNC_BRIDGE_EXECUTOR = None


def _get_sync_bridge_executor() -> concurrent.futures.ThreadPoolExecutor:
    """Return the shared executor for running async coros from sync code."""
    global _SYNC_BRIDGE_EXECUTOR
    if _SYNC_BRIDGE_EXECUTOR is None:
        _SYNC_BRIDGE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="asap-sqlite-sync",
        )
        atexit.register(_shutdown_sync_bridge_executor)
    return _SYNC_BRIDGE_EXECUTOR


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine from sync code (new loop or shared executor).

    When a loop is running (e.g. a sync ``SQLiteSnapshotStore`` call from inside
    a FastAPI handler), ``future.result()`` blocks the calling thread until the
    pool worker finishes — stalling the loop. Callers on an async server should
    prefer ``SQLiteAsyncSnapshotStore``.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    executor = _get_sync_bridge_executor()
    future = executor.submit(asyncio.run, coro)
    return future.result()


async def _co_snapshot_save(backend: _SnapshotBackendProtocol, snapshot: StateSnapshot) -> None:
    await backend._save_impl(snapshot)


async def _co_snapshot_get(
    backend: _SnapshotBackendProtocol,
    task_id: TaskID,
    version: int | None,
) -> StateSnapshot | None:
    return await backend._get_impl(task_id, version)


async def _co_snapshot_list_versions(
    backend: _SnapshotBackendProtocol,
    task_id: TaskID,
) -> list[int]:
    return await backend._list_versions_impl(task_id)


async def _co_snapshot_delete(
    backend: _SnapshotBackendProtocol,
    task_id: TaskID,
    version: int | None,
) -> bool:
    return await backend._delete_impl(task_id, version)


__all__ = [
    "_co_snapshot_delete",
    "_co_snapshot_get",
    "_co_snapshot_list_versions",
    "_co_snapshot_save",
    "_get_sync_bridge_executor",
    "_run_sync",
    "_shutdown_sync_bridge_executor",
]
