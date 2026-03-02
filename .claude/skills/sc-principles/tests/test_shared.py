"""Tests for shared.py - Shared utilities for principle validators."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest  # noqa: F401 - used in type annotations
from scripts.shared import find_python_files


class TestFindPythonFiles:
    """Test git-based and fallback file discovery."""

    def test_git_success_returns_changed_py_files(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Git status returning changed .py files should be used."""
        # Arrange
        (tmp_path / "changed.py").write_text("x = 1")
        (tmp_path / "other.py").write_text("y = 2")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "?? changed.py\n?? other.py"

        monkeypatch.setattr("scripts.shared.subprocess.run", lambda *a, **kw: mock_result)

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert
        filenames = {f.name for f in result}
        assert "changed.py" in filenames
        assert "other.py" in filenames

    def test_git_failure_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """When git fails, should fall back to rglob discovery."""
        # Arrange
        (tmp_path / "fallback.py").write_text("x = 1")

        monkeypatch.setattr(
            "scripts.shared.subprocess.run",
            MagicMock(side_effect=FileNotFoundError("git not found")),
        )

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert - should have found files via rglob
        assert any(f.name == "fallback.py" for f in result)

    def test_git_subprocess_error_falls_back(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """SubprocessError should also trigger rglob fallback."""
        # Arrange
        (tmp_path / "found.py").write_text("x = 1")

        monkeypatch.setattr(
            "scripts.shared.subprocess.run",
            MagicMock(side_effect=subprocess.SubprocessError("timeout")),
        )

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert
        assert any(f.name == "found.py" for f in result)

    def test_changed_only_false_uses_rglob(self, tmp_path: Path) -> None:
        """changed_only=False should skip git and use rglob."""
        # Arrange
        (tmp_path / "all_files.py").write_text("x = 1")

        # Act - no git mock needed, should go straight to rglob
        result = find_python_files(tmp_path, changed_only=False)

        # Assert
        assert any(f.name == "all_files.py" for f in result)

    def test_rename_handling_uses_new_name(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Renames (old -> new) should use the new filename."""
        # Arrange
        (tmp_path / "new_name.py").write_text("x = 1")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "R  old_name.py -> new_name.py\n"

        monkeypatch.setattr("scripts.shared.subprocess.run", lambda *a, **kw: mock_result)

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert
        filenames = {f.name for f in result}
        assert "new_name.py" in filenames

    def test_non_py_files_filtered_out(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Non-.py files from git status should be filtered out."""
        # Arrange
        (tmp_path / "code.py").write_text("x = 1")
        (tmp_path / "readme.md").write_text("# readme")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "M  code.py\nM  readme.md\n"

        monkeypatch.setattr("scripts.shared.subprocess.run", lambda *a, **kw: mock_result)

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert
        filenames = {f.name for f in result}
        assert "code.py" in filenames
        assert "readme.md" not in filenames

    def test_git_no_changes_falls_back_to_rglob(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """When git returns empty output (no changes), should fall back to rglob."""
        # Arrange
        (tmp_path / "existing.py").write_text("x = 1")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""  # no changes

        monkeypatch.setattr("scripts.shared.subprocess.run", lambda *a, **kw: mock_result)

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert - should fall back to rglob
        assert any(f.name == "existing.py" for f in result)

    def test_short_status_lines_skipped(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Lines shorter than 4 chars in git status output should be skipped."""
        # Arrange
        (tmp_path / "valid.py").write_text("x = 1")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ab\nM  valid.py\n"  # "ab" is < 4 chars

        monkeypatch.setattr("scripts.shared.subprocess.run", lambda *a, **kw: mock_result)

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert
        assert len(result) == 1
        assert result[0].name == "valid.py"

    def test_nonexistent_file_in_git_status_excluded(
        self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Files listed by git but no longer on disk should be excluded."""
        # Arrange - don't create deleted.py on disk
        (tmp_path / "exists.py").write_text("x = 1")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "D  deleted.py\nM  exists.py\n"

        monkeypatch.setattr("scripts.shared.subprocess.run", lambda *a, **kw: mock_result)

        # Act
        result = find_python_files(tmp_path, changed_only=True)

        # Assert
        filenames = {f.name for f in result}
        assert "exists.py" in filenames
        assert "deleted.py" not in filenames
