"""Tests for storage_backends.py example.

Validates that the storage backend example works with both InMemory and
SQLite backends, ensuring the example remains valid for users.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from asap.examples import storage_backends


class TestStorageBackendsMain:
    """Tests for storage_backends.main function."""

    def test_main_with_memory_backend(self) -> None:
        """main() runs successfully with default memory backend."""
        with patch.dict(
            "os.environ",
            {"ASAP_STORAGE_BACKEND": "memory"},
            clear=False,
        ):
            storage_backends.main()

    def test_main_with_sqlite_backend(self) -> None:
        """main() runs successfully with sqlite backend."""
        with tempfile.TemporaryDirectory(prefix="asap_test_") as tmp:
            db_path = str(Path(tmp) / "test_storage.db")
            with patch.dict(
                "os.environ",
                {
                    "ASAP_STORAGE_BACKEND": "sqlite",
                    "ASAP_STORAGE_PATH": db_path,
                },
                clear=False,
            ):
                storage_backends.main()

    def test_main_without_env_defaults_to_memory(self) -> None:
        """main() defaults to memory backend when env vars not set."""
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            # Ensure ASAP_STORAGE_BACKEND is absent so default is used
            storage_backends.main()

    def test_main_saves_and_retrieves_correct_data(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """main() saves snapshot and prints correct backend info."""
        with patch.dict(
            "os.environ",
            {"ASAP_STORAGE_BACKEND": "memory"},
            clear=False,
        ):
            storage_backends.main()

        captured = capsys.readouterr()
        assert "Backend: memory" in captured.out
        assert "task_demo_01" in captured.out

    def test_main_sqlite_prints_backend(self, capsys: pytest.CaptureFixture[str]) -> None:
        """main() with sqlite prints 'Backend: sqlite'."""
        with tempfile.TemporaryDirectory(prefix="asap_test_") as tmp:
            db_path = str(Path(tmp) / "test_print.db")
            with patch.dict(
                "os.environ",
                {
                    "ASAP_STORAGE_BACKEND": "sqlite",
                    "ASAP_STORAGE_PATH": db_path,
                },
                clear=False,
            ):
                storage_backends.main()

        captured = capsys.readouterr()
        assert "Backend: sqlite" in captured.out
        assert "task_demo_01" in captured.out
