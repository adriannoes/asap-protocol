"""Tests for storage factory create_snapshot_store()."""

import os
from pathlib import Path

import pytest

from asap.state.snapshot import SnapshotStore
from asap.state.stores import (
    create_snapshot_store,
    InMemorySnapshotStore,
    SQLiteSnapshotStore,
)


class TestCreateSnapshotStoreDefault:
    """Default (no env) returns InMemorySnapshotStore."""

    def test_default_returns_in_memory(self) -> None:
        """Without ASAP_STORAGE_BACKEND, returns InMemorySnapshotStore."""
        # Ensure env is unset for this test
        env_backend = os.environ.pop("ASAP_STORAGE_BACKEND", None)
        env_path = os.environ.pop("ASAP_STORAGE_PATH", None)
        try:
            store = create_snapshot_store()
            assert isinstance(store, InMemorySnapshotStore)
            assert isinstance(store, SnapshotStore)
        finally:
            if env_backend is not None:
                os.environ["ASAP_STORAGE_BACKEND"] = env_backend
            if env_path is not None:
                os.environ["ASAP_STORAGE_PATH"] = env_path


class TestCreateSnapshotStoreBackend:
    """ASAP_STORAGE_BACKEND selects backend."""

    def test_memory_returns_in_memory(self) -> None:
        """ASAP_STORAGE_BACKEND=memory returns InMemorySnapshotStore."""
        env_backend = os.environ.get("ASAP_STORAGE_BACKEND")
        os.environ["ASAP_STORAGE_BACKEND"] = "memory"
        try:
            store = create_snapshot_store()
            assert isinstance(store, InMemorySnapshotStore)
        finally:
            if env_backend is None:
                os.environ.pop("ASAP_STORAGE_BACKEND", None)
            else:
                os.environ["ASAP_STORAGE_BACKEND"] = env_backend

    def test_sqlite_returns_sqlite_store(self, tmp_path: Path) -> None:
        """ASAP_STORAGE_BACKEND=sqlite returns SQLiteSnapshotStore."""
        db_path = tmp_path / "factory_test.db"
        env_backend = os.environ.get("ASAP_STORAGE_BACKEND")
        env_path = os.environ.get("ASAP_STORAGE_PATH")
        os.environ["ASAP_STORAGE_BACKEND"] = "sqlite"
        os.environ["ASAP_STORAGE_PATH"] = str(db_path)
        try:
            store = create_snapshot_store()
            assert isinstance(store, SQLiteSnapshotStore)
            assert store._db_path == db_path
        finally:
            if env_backend is None:
                os.environ.pop("ASAP_STORAGE_BACKEND", None)
            else:
                os.environ["ASAP_STORAGE_BACKEND"] = env_backend
            if env_path is None:
                os.environ.pop("ASAP_STORAGE_PATH", None)
            else:
                os.environ["ASAP_STORAGE_PATH"] = env_path

    def test_custom_path_used_for_sqlite(self, tmp_path: Path) -> None:
        """ASAP_STORAGE_PATH is used when backend is sqlite."""
        custom = tmp_path / "custom.db"
        env_backend = os.environ.get("ASAP_STORAGE_BACKEND")
        env_path = os.environ.get("ASAP_STORAGE_PATH")
        os.environ["ASAP_STORAGE_BACKEND"] = "sqlite"
        os.environ["ASAP_STORAGE_PATH"] = str(custom)
        try:
            store = create_snapshot_store()
            assert isinstance(store, SQLiteSnapshotStore)
            assert store._db_path == custom
        finally:
            if env_backend is None:
                os.environ.pop("ASAP_STORAGE_BACKEND", None)
            else:
                os.environ["ASAP_STORAGE_BACKEND"] = env_backend
            if env_path is None:
                os.environ.pop("ASAP_STORAGE_PATH", None)
            else:
                os.environ["ASAP_STORAGE_PATH"] = env_path


class TestCreateSnapshotStoreInvalidBackend:
    """Invalid backend raises clear error."""

    def test_invalid_backend_raises_value_error(self) -> None:
        """Unknown ASAP_STORAGE_BACKEND raises ValueError with message."""
        env_backend = os.environ.get("ASAP_STORAGE_BACKEND")
        os.environ["ASAP_STORAGE_BACKEND"] = "redis"
        try:
            with pytest.raises(ValueError) as exc_info:
                create_snapshot_store()
            assert "ASAP_STORAGE_BACKEND" in str(exc_info.value)
            assert "redis" in str(exc_info.value)
            assert "memory" in str(exc_info.value) or "sqlite" in str(exc_info.value)
        finally:
            if env_backend is None:
                os.environ.pop("ASAP_STORAGE_BACKEND", None)
            else:
                os.environ["ASAP_STORAGE_BACKEND"] = env_backend
