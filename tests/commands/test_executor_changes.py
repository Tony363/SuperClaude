"""Tests for CommandExecutor change management methods."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestDeriveChangePlan:
    """Tests for _derive_change_plan method."""

    def test_derive_change_plan_empty_outputs(self, executor, sample_context):
        """_derive_change_plan returns empty list when no agent outputs."""
        sample_context.agent_outputs = {}
        agent_result = {"status": "success"}

        result = executor._derive_change_plan(sample_context, agent_result)

        assert result == []

    def test_derive_change_plan_extracts_proposed_changes(
        self, executor, sample_context
    ):
        """_derive_change_plan extracts from proposed_changes key."""
        sample_context.agent_outputs = {
            "implementer": {
                "proposed_changes": [{"path": "src/file.py", "content": "# code"}]
            }
        }

        result = executor._derive_change_plan(sample_context, {})

        assert len(result) == 1
        assert result[0]["path"] == "src/file.py"
        assert result[0]["content"] == "# code"

    def test_derive_change_plan_extracts_generated_files(
        self, executor, sample_context
    ):
        """_derive_change_plan extracts from generated_files key."""
        sample_context.agent_outputs = {
            "implementer": {
                "generated_files": [
                    {"path": "tests/test.py", "content": "def test(): pass"}
                ]
            }
        }

        result = executor._derive_change_plan(sample_context, {})

        assert len(result) == 1
        assert result[0]["path"] == "tests/test.py"

    def test_derive_change_plan_extracts_file_updates(self, executor, sample_context):
        """_derive_change_plan extracts from file_updates key."""
        sample_context.agent_outputs = {
            "implementer": {"file_updates": [{"path": "config.json", "content": "{}"}]}
        }

        result = executor._derive_change_plan(sample_context, {})

        assert len(result) == 1
        assert result[0]["path"] == "config.json"

    def test_derive_change_plan_extracts_changes(self, executor, sample_context):
        """_derive_change_plan extracts from changes key."""
        sample_context.agent_outputs = {
            "implementer": {"changes": [{"path": "readme.md", "content": "# Title"}]}
        }

        result = executor._derive_change_plan(sample_context, {})

        assert len(result) == 1
        assert result[0]["path"] == "readme.md"

    def test_derive_change_plan_merges_multiple_agents(self, executor, sample_context):
        """_derive_change_plan merges changes from multiple agents."""
        sample_context.agent_outputs = {
            "implementer": {
                "proposed_changes": [{"path": "file1.py", "content": "code1"}]
            },
            "reviewer": {"changes": [{"path": "file2.py", "content": "code2"}]},
        }

        result = executor._derive_change_plan(sample_context, {})

        assert len(result) == 2
        paths = {r["path"] for r in result}
        assert paths == {"file1.py", "file2.py"}


class TestExtractAgentChangeSpecs:
    """Tests for _extract_agent_change_specs method."""

    def test_extract_returns_empty_for_none(self, executor):
        """_extract_agent_change_specs returns empty list for None."""
        result = executor._extract_agent_change_specs(None)
        assert result == []

    def test_extract_dict_with_path_and_content(self, executor):
        """_extract_agent_change_specs handles dict with path/content."""
        candidate = {"path": "file.py", "content": "code"}

        result = executor._extract_agent_change_specs(candidate)

        assert len(result) == 1
        assert result[0]["path"] == "file.py"
        assert result[0]["content"] == "code"

    def test_extract_dict_without_path_uses_key(self, executor):
        """_extract_agent_change_specs uses dict key as path."""
        candidate = {"src/module.py": {"content": "module code"}}

        result = executor._extract_agent_change_specs(candidate)

        assert len(result) == 1
        assert result[0]["path"] == "src/module.py"
        assert result[0]["content"] == "module code"

    def test_extract_nested_dict_pairs(self, executor):
        """_extract_agent_change_specs handles key-value pairs."""
        candidate = {"file1.py": "content1", "file2.py": "content2"}

        result = executor._extract_agent_change_specs(candidate)

        assert len(result) == 2

    def test_extract_list_of_changes(self, executor):
        """_extract_agent_change_specs handles list input."""
        candidate = [
            {"path": "a.py", "content": "a"},
            {"path": "b.py", "content": "b"},
        ]

        result = executor._extract_agent_change_specs(candidate)

        assert len(result) == 2

    def test_extract_nested_list(self, executor):
        """_extract_agent_change_specs flattens nested lists."""
        candidate = [
            [{"path": "a.py", "content": "a"}],
            [{"path": "b.py", "content": "b"}],
        ]

        result = executor._extract_agent_change_specs(candidate)

        assert len(result) == 2

    def test_extract_set_of_dicts(self, executor):
        """_extract_agent_change_specs handles set input (converts to list)."""
        # Sets can't contain dicts, but tuples work
        candidate = ({"path": "a.py", "content": "a"},)

        result = executor._extract_agent_change_specs(candidate)

        assert len(result) == 1


class TestNormalizeChangeDescriptor:
    """Tests for _normalize_change_descriptor method."""

    def test_normalize_preserves_path(self, executor):
        """_normalize_change_descriptor keeps path."""
        descriptor = {"path": "src/file.py", "content": "code"}

        result = executor._normalize_change_descriptor(descriptor)

        assert result["path"] == "src/file.py"

    def test_normalize_preserves_content(self, executor):
        """_normalize_change_descriptor keeps content."""
        descriptor = {"path": "src/file.py", "content": "code"}

        result = executor._normalize_change_descriptor(descriptor)

        assert result["content"] == "code"

    def test_normalize_defaults_mode_to_replace(self, executor):
        """_normalize_change_descriptor defaults mode to replace."""
        descriptor = {"path": "file.py", "content": "code"}

        result = executor._normalize_change_descriptor(descriptor)

        assert result["mode"] == "replace"

    def test_normalize_preserves_explicit_mode(self, executor):
        """_normalize_change_descriptor preserves explicit mode."""
        descriptor = {"path": "file.py", "content": "code", "mode": "append"}

        result = executor._normalize_change_descriptor(descriptor)

        assert result["mode"] == "append"

    def test_normalize_converts_path_to_string(self, executor):
        """_normalize_change_descriptor converts Path to string."""
        descriptor = {"path": Path("src/file.py"), "content": "code"}

        result = executor._normalize_change_descriptor(descriptor)

        assert result["path"] == "src/file.py"
        assert isinstance(result["path"], str)

    def test_normalize_empty_content_default(self, executor):
        """_normalize_change_descriptor defaults content to empty string."""
        descriptor = {"path": "file.py"}

        result = executor._normalize_change_descriptor(descriptor)

        assert result["content"] == ""


class TestApplyChangePlan:
    """Tests for _apply_change_plan method."""

    def test_apply_change_plan_empty_list(self, executor, sample_context):
        """_apply_change_plan handles empty change plan."""
        result = executor._apply_change_plan(sample_context, [])

        assert result["applied"] == []
        assert "No change entries" in result["warnings"][0]

    def test_apply_change_plan_with_safe_apply(self, executor, sample_context):
        """_apply_change_plan respects safe-apply mode."""
        sample_context.command.flags = {"safe": True}
        change_plan = [{"path": "file.py", "content": "code"}]

        with patch.object(executor, "_safe_apply_requested", return_value=True):  # noqa: SIM117
            with patch.object(
                executor,
                "_write_safe_apply_snapshot",
                return_value={"directory": "/tmp/safe", "files": ["file.py"]},
            ):
                result = executor._apply_change_plan(sample_context, change_plan)

        assert result["applied"] == []
        assert "safe_apply_directory" in result

    def test_apply_change_plan_uses_worktree_manager(self, executor, sample_context):
        """_apply_change_plan uses worktree manager when available."""
        change_plan = [{"path": "file.py", "content": "code"}]

        mock_manager = MagicMock()
        mock_manager.apply_changes.return_value = {
            "applied": ["file.py"],
            "warnings": [],
        }

        with patch.object(executor, "_safe_apply_requested", return_value=False):  # noqa: SIM117
            with patch.object(
                executor, "_ensure_worktree_manager", return_value=mock_manager
            ):
                result = executor._apply_change_plan(sample_context, change_plan)

        assert result["applied"] == ["file.py"]
        mock_manager.apply_changes.assert_called_once_with(change_plan)

    def test_apply_change_plan_uses_fallback(self, executor, sample_context):
        """_apply_change_plan uses fallback when manager unavailable."""
        change_plan = [{"path": "file.py", "content": "code"}]

        with patch.object(executor, "_safe_apply_requested", return_value=False):  # noqa: SIM117
            with patch.object(executor, "_ensure_worktree_manager", return_value=None):
                with patch.object(
                    executor,
                    "_apply_changes_fallback",
                    return_value={"applied": ["file.py"], "warnings": []},
                ) as mock_fallback:
                    result = executor._apply_change_plan(sample_context, change_plan)

        mock_fallback.assert_called_once()
        assert result["applied"] == ["file.py"]

    def test_apply_change_plan_handles_exception(self, executor, sample_context):
        """_apply_change_plan handles exceptions gracefully."""
        change_plan = [{"path": "file.py", "content": "code"}]

        with patch.object(executor, "_safe_apply_requested", return_value=False):  # noqa: SIM117
            with patch.object(
                executor,
                "_ensure_worktree_manager",
                side_effect=Exception("manager error"),
            ):
                result = executor._apply_change_plan(sample_context, change_plan)

        assert result["applied"] == []
        assert result["session"] == "error"
        assert len(sample_context.errors) > 0


class TestApplyChangesFallback:
    """Tests for _apply_changes_fallback method."""

    def test_fallback_creates_file(self, executor, command_workspace):
        """_apply_changes_fallback creates new files."""
        changes = [{"path": "new_file.py", "content": "# new file"}]

        result = executor._apply_changes_fallback(changes)

        assert "new_file.py" in result["applied"]
        assert (command_workspace / "new_file.py").exists()
        assert (command_workspace / "new_file.py").read_text() == "# new file"

    def test_fallback_creates_nested_directories(self, executor, command_workspace):
        """_apply_changes_fallback creates parent directories."""
        changes = [{"path": "src/deep/nested/file.py", "content": "code"}]

        result = executor._apply_changes_fallback(changes)

        assert "src/deep/nested/file.py" in result["applied"]
        assert (command_workspace / "src/deep/nested/file.py").exists()

    def test_fallback_replaces_existing_file(self, executor, command_workspace):
        """_apply_changes_fallback replaces existing file content."""
        (command_workspace / "existing.py").write_text("old content")
        changes = [{"path": "existing.py", "content": "new content"}]

        result = executor._apply_changes_fallback(changes)

        assert "existing.py" in result["applied"]
        assert (command_workspace / "existing.py").read_text() == "new content"

    def test_fallback_append_mode(self, executor, command_workspace):
        """_apply_changes_fallback supports append mode."""
        (command_workspace / "log.txt").write_text("line1\n")
        changes = [{"path": "log.txt", "content": "line2\n", "mode": "append"}]

        result = executor._apply_changes_fallback(changes)

        assert "log.txt" in result["applied"]
        assert (command_workspace / "log.txt").read_text() == "line1\nline2\n"

    def test_fallback_rejects_missing_path(self, executor):
        """_apply_changes_fallback warns on missing path."""
        changes = [{"content": "code"}]  # No path

        result = executor._apply_changes_fallback(changes)

        assert result["applied"] == []
        assert "missing path" in result["warnings"][0].lower()

    def test_fallback_rejects_absolute_path(self, executor):
        """_apply_changes_fallback rejects absolute paths."""
        changes = [{"path": "/etc/passwd", "content": "hack"}]

        result = executor._apply_changes_fallback(changes)

        assert result["applied"] == []
        assert "Invalid path" in result["warnings"][0]

    def test_fallback_rejects_path_traversal(self, executor):
        """_apply_changes_fallback rejects path traversal attempts."""
        changes = [{"path": "../../../etc/passwd", "content": "hack"}]

        result = executor._apply_changes_fallback(changes)

        assert result["applied"] == []
        assert any("escapes" in w or "Invalid" in w for w in result["warnings"])

    def test_fallback_handles_write_error(self, executor, command_workspace):
        """_apply_changes_fallback handles write failures."""
        # Create read-only file
        readonly_file = command_workspace / "readonly.py"
        readonly_file.write_text("original")
        readonly_file.chmod(0o444)

        changes = [{"path": "readonly.py", "content": "new"}]

        try:
            result = executor._apply_changes_fallback(changes)

            # Might fail or succeed depending on OS permissions
            # Just ensure no exception raised
            assert isinstance(result["warnings"], list)
        finally:
            readonly_file.chmod(0o644)  # Restore for cleanup

    def test_fallback_returns_base_path(self, executor, command_workspace):
        """_apply_changes_fallback returns base_path in result."""
        changes = [{"path": "file.py", "content": "code"}]

        result = executor._apply_changes_fallback(changes)

        assert "base_path" in result
        assert str(command_workspace) in result["base_path"]


class TestSnapshotRepoChanges:
    """Tests for _snapshot_repo_changes method."""

    def test_snapshot_returns_set(self, executor):
        """_snapshot_repo_changes returns a set of file paths."""
        result = executor._snapshot_repo_changes()
        assert isinstance(result, set)

    def test_snapshot_empty_without_git(self, executor, tmp_path, monkeypatch):
        """_snapshot_repo_changes returns empty set without git repo."""
        monkeypatch.chdir(tmp_path)
        executor.repo_root = tmp_path

        result = executor._snapshot_repo_changes()

        assert result == set()


class TestDiffSnapshots:
    """Tests for _diff_snapshots method."""

    def test_diff_empty_snapshots(self, executor):
        """_diff_snapshots handles empty snapshots."""
        before = set()
        after = set()

        result = executor._diff_snapshots(before, after)

        assert result == []

    def test_diff_detects_new_files(self, executor):
        """_diff_snapshots detects newly created files."""
        before = set()
        after = {"M\tnew_file.py"}

        result = executor._diff_snapshots(before, after)

        assert "M\tnew_file.py" in result

    def test_diff_returns_only_new_entries(self, executor):
        """_diff_snapshots returns only entries not in before."""
        before = {"M\tfile1.py"}
        after = {"M\tfile1.py", "A\tfile2.py"}

        result = executor._diff_snapshots(before, after)

        assert len(result) == 1
        assert "A\tfile2.py" in result

    def test_diff_returns_sorted(self, executor):
        """_diff_snapshots returns sorted list."""
        before = set()
        after = {"M\tz.py", "M\ta.py"}

        result = executor._diff_snapshots(before, after)

        assert result == ["M\ta.py", "M\tz.py"]


class TestPartitionChangeEntries:
    """Tests for _partition_change_entries method."""

    def test_partition_empty_list(self, executor):
        """_partition_change_entries handles empty list."""
        artifacts, evidence = executor._partition_change_entries([])

        assert artifacts == []
        assert evidence == []

    def test_partition_artifacts(self, executor):
        """_partition_change_entries identifies artifact changes."""
        # git name-status format: "M\tpath"
        entries = [
            "M\tSuperClaude/Generated/file1.py",
            "M\tSuperClaude/Generated/file2.py",
        ]

        artifacts, evidence = executor._partition_change_entries(entries)

        assert len(artifacts) == 2
        assert len(evidence) == 0

    def test_partition_evidence(self, executor):
        """_partition_change_entries identifies evidence changes."""
        entries = [
            "M\tdocs/implementation.md",
        ]

        artifacts, evidence = executor._partition_change_entries(entries)

        assert len(artifacts) == 0
        assert len(evidence) == 1

    def test_partition_mixed(self, executor):
        """_partition_change_entries separates mixed entries."""
        entries = [
            "M\tSuperClaude/Generated/code.py",  # artifact
            "A\tsrc/feature.py",  # evidence (not in Generated dir)
        ]

        artifacts, evidence = executor._partition_change_entries(entries)

        assert len(artifacts) == 1
        assert len(evidence) == 1


class TestIsArtifactChange:
    """Tests for _is_artifact_change method."""

    def test_is_artifact_generated_dir(self, executor):
        """_is_artifact_change identifies SuperClaude/Generated/ as artifacts."""
        entry = "M\tSuperClaude/Generated/module.py"

        result = executor._is_artifact_change(entry)

        assert result is True

    def test_is_artifact_worktrees_dir(self, executor):
        """_is_artifact_change identifies .worktrees/ as artifacts."""
        entry = "A\t.worktrees/feature/file.py"

        result = executor._is_artifact_change(entry)

        assert result is True

    def test_is_not_artifact_regular_file(self, executor):
        """_is_artifact_change returns False for regular files."""
        entry = "M\tsrc/module.py"

        result = executor._is_artifact_change(entry)

        assert result is False

    def test_is_not_artifact_malformed_entry(self, executor):
        """_is_artifact_change handles malformed entries."""
        entry = "no-tabs-here"

        result = executor._is_artifact_change(entry)

        assert result is False


class TestSafeApplyRequested:
    """Tests for _safe_apply_requested method."""

    def test_safe_apply_false_by_default(self, executor, sample_context):
        """_safe_apply_requested returns False when no safe-apply flag."""
        sample_context.command.flags = {}
        sample_context.command.parameters = {}

        result = executor._safe_apply_requested(sample_context)

        assert result is False

    def test_safe_apply_true_with_hyphen_flag(self, executor, sample_context):
        """_safe_apply_requested returns True with --safe-apply flag."""
        sample_context.command.flags = {"safe-apply": True}
        sample_context.command.parameters = {}

        result = executor._safe_apply_requested(sample_context)

        assert result is True

    def test_safe_apply_true_with_underscore_flag(self, executor, sample_context):
        """_safe_apply_requested returns True with --safe_apply flag."""
        sample_context.command.flags = {"safe_apply": True}
        sample_context.command.parameters = {}

        result = executor._safe_apply_requested(sample_context)

        assert result is True

    def test_safe_apply_true_with_hyphen_parameter(self, executor, sample_context):
        """_safe_apply_requested returns True with safe-apply parameter."""
        sample_context.command.flags = {}
        sample_context.command.parameters = {"safe-apply": "true"}

        result = executor._safe_apply_requested(sample_context)

        assert result is True

    def test_safe_apply_true_with_underscore_parameter(self, executor, sample_context):
        """_safe_apply_requested returns True with safe_apply parameter."""
        sample_context.command.flags = {}
        sample_context.command.parameters = {"safe_apply": "true"}

        result = executor._safe_apply_requested(sample_context)

        assert result is True
