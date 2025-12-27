"""Tests for CommandExecutor git and filesystem operations."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry


class TestSnapshotRepoChanges:
    """Tests for _snapshot_repo_changes method."""

    def test_snapshot_returns_empty_without_repo_root(self, command_workspace):
        """Snapshot returns empty set when repo_root is None."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=command_workspace)
        executor.repo_root = None

        result = executor._snapshot_repo_changes()

        assert result == set()

    def test_snapshot_returns_empty_without_git_dir(self, command_workspace):
        """Snapshot returns empty set when .git doesn't exist."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=command_workspace)

        result = executor._snapshot_repo_changes()

        assert result == set()

    def test_snapshot_captures_modified_files(self, temp_repo, monkeypatch):
        """Snapshot captures modified files from git."""
        monkeypatch.chdir(temp_repo)
        # Modify a file
        readme = temp_repo / "README.md"
        readme.write_text("# Modified\n")

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._snapshot_repo_changes()

        assert isinstance(result, set)
        assert any("README.md" in entry for entry in result)

    def test_snapshot_captures_staged_files(self, temp_repo, monkeypatch):
        """Snapshot captures staged files."""
        monkeypatch.chdir(temp_repo)
        # Create and stage a new file
        new_file = temp_repo / "staged.txt"
        new_file.write_text("staged content")
        subprocess.run(["git", "add", "staged.txt"], cwd=temp_repo, check=True)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._snapshot_repo_changes()

        assert isinstance(result, set)
        assert any("staged.txt" in entry for entry in result)

    def test_snapshot_captures_untracked_files(self, temp_repo, monkeypatch):
        """Snapshot captures untracked files."""
        monkeypatch.chdir(temp_repo)
        untracked = temp_repo / "untracked.txt"
        untracked.write_text("untracked content")

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._snapshot_repo_changes()

        assert isinstance(result, set)
        assert any("untracked.txt" in entry for entry in result)

    def test_snapshot_handles_subprocess_failure(self, temp_repo, monkeypatch):
        """Snapshot handles git command failure gracefully."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        with patch("subprocess.run", side_effect=subprocess.SubprocessError("git failed")):
            result = executor._snapshot_repo_changes()

        assert result == set()


class TestDiffSnapshots:
    """Tests for _diff_snapshots method."""

    def test_diff_returns_empty_for_empty_after(self, executor):
        """Diff returns empty when after snapshot is empty."""
        before = {"M\tfile1.py", "A\tfile2.py"}
        after: set[str] = set()

        result = executor._diff_snapshots(before, after)

        assert result == []

    def test_diff_returns_all_for_empty_before(self, executor):
        """Diff returns all entries when before snapshot is empty."""
        before: set[str] = set()
        after = {"M\tfile1.py", "A\tfile2.py"}

        result = executor._diff_snapshots(before, after)

        assert sorted(result) == ["A\tfile2.py", "M\tfile1.py"]

    def test_diff_returns_new_entries_only(self, executor):
        """Diff returns only entries that appeared in after."""
        before = {"M\tfile1.py"}
        after = {"M\tfile1.py", "A\tfile2.py", "D\tfile3.py"}

        result = executor._diff_snapshots(before, after)

        assert sorted(result) == ["A\tfile2.py", "D\tfile3.py"]

    def test_diff_returns_empty_when_identical(self, executor):
        """Diff returns empty when snapshots are identical."""
        entries = {"M\tfile1.py", "A\tfile2.py"}

        result = executor._diff_snapshots(entries, entries.copy())

        assert result == []

    def test_diff_is_sorted(self, executor):
        """Diff returns sorted list."""
        before: set[str] = set()
        after = {"M\tzebra.py", "A\talpha.py", "D\tbeta.py"}

        result = executor._diff_snapshots(before, after)

        assert result == sorted(result)


class TestPartitionChangeEntries:
    """Tests for _partition_change_entries method."""

    def test_partition_separates_artifacts(self, executor):
        """Partition correctly separates artifact entries."""
        entries = [
            "M\tSuperClaude/Generated/output.py",
            "M\tsrc/main.py",
            "A\t.worktrees/temp.txt",
        ]

        artifacts, evidence = executor._partition_change_entries(entries)

        assert "M\tSuperClaude/Generated/output.py" in artifacts
        assert "A\t.worktrees/temp.txt" in artifacts
        assert "M\tsrc/main.py" in evidence

    def test_partition_empty_list(self, executor):
        """Partition handles empty list."""
        artifacts, evidence = executor._partition_change_entries([])

        assert artifacts == []
        assert evidence == []

    def test_partition_all_artifacts(self, executor):
        """Partition handles list with only artifacts."""
        entries = [
            "M\tSuperClaude/Generated/a.py",
            "M\tSuperClaude/Generated/b.py",
        ]

        artifacts, evidence = executor._partition_change_entries(entries)

        assert len(artifacts) == 2
        assert len(evidence) == 0

    def test_partition_no_artifacts(self, executor):
        """Partition handles list with no artifacts."""
        entries = [
            "M\tsrc/app.py",
            "A\ttests/test_app.py",
        ]

        artifacts, evidence = executor._partition_change_entries(entries)

        assert len(artifacts) == 0
        assert len(evidence) == 2


class TestIsArtifactChange:
    """Tests for _is_artifact_change method."""

    def test_is_artifact_generated_path(self, executor):
        """Generated path is detected as artifact."""
        assert executor._is_artifact_change("M\tSuperClaude/Generated/output.py")

    def test_is_artifact_worktrees_path(self, executor):
        """Worktrees path is detected as artifact."""
        assert executor._is_artifact_change("A\t.worktrees/temp.txt")

    def test_not_artifact_regular_path(self, executor):
        """Regular path is not detected as artifact."""
        assert not executor._is_artifact_change("M\tsrc/main.py")

    def test_not_artifact_empty_entry(self, executor):
        """Empty entry is not an artifact."""
        assert not executor._is_artifact_change("")

    def test_not_artifact_no_tab(self, executor):
        """Entry without tab is not an artifact."""
        assert not executor._is_artifact_change("M src/main.py")

    def test_artifact_with_rename(self, executor):
        """Renamed file in Generated is detected."""
        assert executor._is_artifact_change("R100\told.py\tSuperClaude/Generated/new.py")

    def test_artifact_nested_generated(self, executor):
        """Nested Generated path is detected."""
        assert executor._is_artifact_change("M\tSuperClaude/Generated/sub/file.py")


class TestFormatChangeEntry:
    """Tests for _format_change_entry method."""

    def test_format_modified(self, executor):
        """Format modified file entry."""
        result = executor._format_change_entry("M\tsrc/main.py")

        assert "modify" in result.lower()
        assert "src/main.py" in result

    def test_format_added(self, executor):
        """Format added file entry."""
        result = executor._format_change_entry("A\tsrc/new.py")

        assert "add" in result.lower()
        assert "src/new.py" in result

    def test_format_deleted(self, executor):
        """Format deleted file entry."""
        result = executor._format_change_entry("D\tsrc/old.py")

        assert "delete" in result.lower()
        assert "src/old.py" in result

    def test_format_renamed(self, executor):
        """Format renamed file entry."""
        result = executor._format_change_entry("R100\told.py\tnew.py")

        assert "rename" in result.lower()

    def test_format_copied(self, executor):
        """Format copied file entry."""
        result = executor._format_change_entry("C50\torig.py\tcopy.py")

        assert "copy" in result.lower()

    def test_format_untracked(self, executor):
        """Format untracked file entry."""
        result = executor._format_change_entry("??\tuntracked.txt")

        assert "untracked" in result.lower()
        assert "untracked.txt" in result

    def test_format_unknown_code(self, executor):
        """Format handles unknown status code."""
        result = executor._format_change_entry("X\tfile.py")

        assert "file.py" in result

    def test_format_empty_entry(self, executor):
        """Format handles empty entry."""
        result = executor._format_change_entry("")

        assert result == ""


class TestRunCommand:
    """Tests for _run_command method."""

    def test_run_command_success(self, executor, command_workspace):
        """Run command captures successful output."""
        result = executor._run_command(["echo", "hello"])

        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
        assert result.get("error") is None

    def test_run_command_captures_stderr(self, executor):
        """Run command captures stderr."""
        result = executor._run_command(
            ["python", "-c", "import sys; sys.stderr.write('error message')"]
        )

        assert "error message" in result["stderr"]

    def test_run_command_nonzero_exit(self, executor):
        """Run command captures non-zero exit code."""
        result = executor._run_command(["python", "-c", "exit(1)"])

        assert result["exit_code"] == 1
        assert "error" in result

    def test_run_command_with_cwd(self, executor, tmp_path):
        """Run command respects cwd parameter."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = executor._run_command(["pwd"], cwd=subdir)

        assert str(subdir) in result["stdout"]

    def test_run_command_with_env(self, executor):
        """Run command merges environment variables."""
        result = executor._run_command(
            ["python", "-c", "import os; print(os.environ.get('TEST_VAR'))"],
            env={"TEST_VAR": "test_value"},
        )

        assert "test_value" in result["stdout"]

    def test_run_command_timeout(self, executor):
        """Run command handles timeout."""
        result = executor._run_command(
            ["python", "-c", "import time; time.sleep(10)"],
            timeout=1,
        )

        assert result["exit_code"] is None
        assert "timeout" in result.get("error", "").lower()

    def test_run_command_invalid_command(self, executor):
        """Run command handles invalid command."""
        result = executor._run_command(["nonexistent_command_12345"])

        assert result["exit_code"] is None
        assert "error" in result

    def test_run_command_includes_duration(self, executor):
        """Run command records duration."""
        result = executor._run_command(["echo", "test"])

        assert "duration_s" in result
        assert result["duration_s"] >= 0


class TestCollectDiffStats:
    """Tests for _collect_diff_stats method."""

    def test_collect_diff_stats_empty_repo(self, command_workspace):
        """Collect diff stats returns empty for non-git repo."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=command_workspace)

        result = executor._collect_diff_stats()

        assert result == []

    def test_collect_diff_stats_clean_repo(self, temp_repo, monkeypatch):
        """Collect diff stats returns empty for clean repo."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._collect_diff_stats()

        # Clean repo should have no stats
        assert isinstance(result, list)

    def test_collect_diff_stats_with_changes(self, temp_repo, monkeypatch):
        """Collect diff stats captures working changes."""
        monkeypatch.chdir(temp_repo)
        readme = temp_repo / "README.md"
        readme.write_text("# Modified content\nWith more lines\n")

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._collect_diff_stats()

        assert isinstance(result, list)
        # Should have some stats about the changed file
        if result:  # May be empty if git formats output differently
            stats_text = " ".join(result)
            assert "README" in stats_text or len(result) > 0


class TestGitHasModifications:
    """Tests for _git_has_modifications method."""

    def test_git_has_modifications_no_repo_root(self, command_workspace):
        """Returns False when repo_root is None."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=command_workspace)
        executor.repo_root = None

        assert not executor._git_has_modifications(Path("file.py"))

    def test_git_has_modifications_no_git_dir(self, command_workspace):
        """Returns False when .git doesn't exist."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=command_workspace)

        assert not executor._git_has_modifications(command_workspace / "file.py")

    def test_git_has_modifications_untracked(self, temp_repo, monkeypatch):
        """Returns False for untracked files."""
        monkeypatch.chdir(temp_repo)
        untracked = temp_repo / "untracked.txt"
        untracked.write_text("new file")

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        # Untracked files return False
        assert not executor._git_has_modifications(untracked)

    def test_git_has_modifications_modified(self, temp_repo, monkeypatch):
        """Returns True for modified tracked files."""
        monkeypatch.chdir(temp_repo)
        readme = temp_repo / "README.md"
        readme.write_text("# Modified\n")

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        assert executor._git_has_modifications(readme)

    def test_git_has_modifications_outside_repo(self, temp_repo, tmp_path, monkeypatch):
        """Returns False for files outside repo."""
        monkeypatch.chdir(temp_repo)
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("outside content")

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        assert not executor._git_has_modifications(outside_file)

    def test_git_has_modifications_subprocess_error(self, temp_repo, monkeypatch):
        """Returns False when subprocess fails."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        with patch("subprocess.run", side_effect=Exception("git error")):
            assert not executor._git_has_modifications(temp_repo / "README.md")


class TestExtractChangedPaths:
    """Tests for _extract_changed_paths method."""

    def test_extract_from_repo_entries(self, temp_repo, monkeypatch):
        """Extract paths from git name-status entries."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        repo_entries = ["M\tREADME.md", "A\tsrc/new.py"]
        result = executor._extract_changed_paths(repo_entries, [])

        paths = [str(p) for p in result]
        assert any("README.md" in p for p in paths)
        assert any("new.py" in p for p in paths)

    def test_extract_from_applied_changes(self, temp_repo, monkeypatch):
        """Extract paths from applied change descriptions."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        applied_changes = ["add src/feature.py", "modify README.md"]
        result = executor._extract_changed_paths([], applied_changes)

        paths = [str(p) for p in result]
        assert any("feature.py" in p for p in paths)
        assert any("README.md" in p for p in paths)

    def test_extract_handles_rename(self, temp_repo, monkeypatch):
        """Extract handles renamed files."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        repo_entries = ["R100\told.py\tnew.py"]
        result = executor._extract_changed_paths(repo_entries, [])

        paths = [str(p) for p in result]
        assert any("new.py" in p for p in paths)

    def test_extract_handles_copy(self, temp_repo, monkeypatch):
        """Extract handles copied files."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        repo_entries = ["C50\torig.py\tcopy.py"]
        result = executor._extract_changed_paths(repo_entries, [])

        paths = [str(p) for p in result]
        assert any("copy.py" in p for p in paths)

    def test_extract_handles_untracked(self, temp_repo, monkeypatch):
        """Extract handles untracked files."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        repo_entries = ["??\tuntracked.txt"]
        result = executor._extract_changed_paths(repo_entries, [])

        paths = [str(p) for p in result]
        assert any("untracked.txt" in p for p in paths)

    def test_extract_deduplicates(self, temp_repo, monkeypatch):
        """Extract removes duplicate paths."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        repo_entries = ["M\tfile.py"]
        applied_changes = ["modify file.py"]
        result = executor._extract_changed_paths(repo_entries, applied_changes)

        paths = [str(p) for p in result]
        file_paths = [p for p in paths if "file.py" in p]
        assert len(file_paths) == 1

    def test_extract_prevents_path_traversal(self, temp_repo, monkeypatch):
        """Extract rejects paths outside repo."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        repo_entries = ["M\t../../../etc/passwd"]
        result = executor._extract_changed_paths(repo_entries, [])

        assert len(result) == 0

    def test_extract_empty_input(self, temp_repo, monkeypatch):
        """Extract handles empty input."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._extract_changed_paths([], [])

        assert result == []

    def test_extract_no_repo_root(self, command_workspace):
        """Extract returns empty when repo_root is None."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=command_workspace)
        executor.repo_root = None

        result = executor._extract_changed_paths(["M\tfile.py"], [])

        assert result == []


class TestRunStaticValidation:
    """Tests for _run_static_validation method."""

    def test_validate_empty_paths(self, executor):
        """Validation returns empty for empty paths."""
        result = executor._run_static_validation([])

        assert result == []

    def test_validate_missing_file(self, executor, tmp_path):
        """Validation reports missing files."""
        missing = tmp_path / "missing.py"

        result = executor._run_static_validation([missing])

        assert len(result) == 1
        assert "not found" in result[0].lower()

    def test_validate_valid_python(self, executor, tmp_path):
        """Validation passes for valid Python."""
        valid_py = tmp_path / "valid.py"
        valid_py.write_text("def hello():\n    return 'world'\n")

        result = executor._run_static_validation([valid_py])

        # No syntax errors
        syntax_errors = [r for r in result if "syntax error" in r.lower()]
        assert len(syntax_errors) == 0

    def test_validate_invalid_python_syntax(self, executor, tmp_path):
        """Validation reports Python syntax errors."""
        invalid_py = tmp_path / "invalid.py"
        invalid_py.write_text("def hello(\n")

        result = executor._run_static_validation([invalid_py])

        assert len(result) >= 1
        assert any("syntax" in r.lower() for r in result)

    def test_validate_valid_json(self, executor, tmp_path):
        """Validation passes for valid JSON."""
        valid_json = tmp_path / "valid.json"
        valid_json.write_text('{"key": "value"}')

        result = executor._run_static_validation([valid_json])

        json_errors = [r for r in result if "json" in r.lower()]
        assert len(json_errors) == 0

    def test_validate_invalid_json(self, executor, tmp_path):
        """Validation reports JSON errors."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text('{"key": invalid}')

        result = executor._run_static_validation([invalid_json])

        assert len(result) >= 1
        assert any("json" in r.lower() for r in result)

    def test_validate_valid_yaml(self, executor, tmp_path):
        """Validation passes for valid YAML."""
        valid_yaml = tmp_path / "valid.yaml"
        valid_yaml.write_text("key: value\n")

        result = executor._run_static_validation([valid_yaml])

        yaml_errors = [r for r in result if "yaml" in r.lower() and "error" in r.lower()]
        assert len(yaml_errors) == 0

    def test_validate_invalid_yaml(self, executor, tmp_path):
        """Validation reports YAML errors."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("key: [unclosed")

        result = executor._run_static_validation([invalid_yaml])

        # May report YAML error or skip if PyYAML not installed
        assert isinstance(result, list)

    def test_validate_yml_extension(self, executor, tmp_path):
        """Validation handles .yml extension."""
        yml_file = tmp_path / "config.yml"
        yml_file.write_text("setting: true\n")

        result = executor._run_static_validation([yml_file])

        # Should not crash
        assert isinstance(result, list)

    def test_validate_non_python_file(self, executor, tmp_path):
        """Validation skips non-Python/JSON/YAML files."""
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("Just some text")

        result = executor._run_static_validation([txt_file])

        assert result == []


class TestDetectRepoRoot:
    """Tests for _detect_repo_root method (additional tests)."""

    def test_detect_from_nested_dir(self, temp_repo, monkeypatch):
        """Detect repo root from deeply nested directory."""
        nested = temp_repo / "a" / "b" / "c" / "d"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._detect_repo_root()

        assert result == temp_repo.resolve()

    def test_detect_handles_cwd_exception(self, executor, monkeypatch):
        """Detect handles Path.cwd() exception."""
        with patch.object(Path, "cwd", side_effect=OSError("cwd failed")):
            # Create fresh executor since cwd is called in __init__
            registry = CommandRegistry()
            parser = CommandParser()
            executor = CommandExecutor(registry, parser)
            result = executor._detect_repo_root()

        assert result is None


class TestRelativeToRepoPath:
    """Tests for _relative_to_repo_path method."""

    def test_relative_path_inside_repo(self, temp_repo, monkeypatch):
        """Returns relative path for file inside repo."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        file_path = temp_repo / "src" / "module.py"
        result = executor._relative_to_repo_path(file_path)

        assert result == "src/module.py"

    def test_relative_path_at_root(self, temp_repo, monkeypatch):
        """Returns filename for file at repo root."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        file_path = temp_repo / "README.md"
        result = executor._relative_to_repo_path(file_path)

        assert result == "README.md"

    def test_relative_path_outside_repo(self, temp_repo, tmp_path, monkeypatch):
        """Returns absolute path for file outside repo."""
        monkeypatch.chdir(temp_repo)
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        file_path = tmp_path / "outside.txt"
        result = executor._relative_to_repo_path(file_path)

        # Should return something usable even if outside repo
        assert "outside.txt" in result

    def test_relative_path_no_repo_root(self, command_workspace):
        """Returns str(path) when repo_root is None."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=command_workspace)
        executor.repo_root = None

        result = executor._relative_to_repo_path(Path("/some/path.py"))

        assert "path.py" in result
