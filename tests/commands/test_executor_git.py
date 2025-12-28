"""Tests for CommandExecutor git command handling."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from SuperClaude.Commands.parser import ParsedCommand


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
    (tmp_path / ".git").mkdir()
    return tmp_path


class TestGitNoRepository:
    """Tests for git when no repository exists."""

    @pytest.mark.asyncio
    async def test_git_no_repo_error(self, executor, sample_context, tmp_path):
        """Git returns error when .git directory missing."""
        executor.repo_root = tmp_path
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            arguments=["status"],
            flags={},
            parameters={},
            description="Git operations",
        )

        result = await executor._execute_git(sample_context)

        assert result["status"] == "git_failed"
        assert "error" in result
        assert len(sample_context.errors) > 0


class TestGitStatusOperation:
    """Tests for git status operation handling."""

    @pytest.mark.asyncio
    async def test_git_status_default(self, executor, sample_context, git_repo):
        """Git command defaults to status operation."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git",
            arguments=[],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "## main\n M file.py\n?? new.py",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert result["operation"] == "status"

    @pytest.mark.asyncio
    async def test_git_status_parses_branch(self, executor, sample_context, git_repo):
        """Git status extracts branch name."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            arguments=["status"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "## main...origin/main\n",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert "main" in result["summary"]["branch"]

    @pytest.mark.asyncio
    async def test_git_status_counts_untracked(self, executor, sample_context, git_repo):
        """Git status counts untracked files."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            arguments=["status"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "## main\n?? untracked1.py\n?? untracked2.py\n",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        summary = result.get("summary", {})
        assert summary.get("untracked_files", 0) == 2


class TestGitDiffOperation:
    """Tests for git diff operation handling."""

    @pytest.mark.asyncio
    async def test_git_diff_operation(self, executor, sample_context, git_repo):
        """Git diff runs diff --stat."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git diff",
            arguments=["diff"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "file.py | 10 +++++-----\n1 file changed",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert result["operation"] == "diff"
        assert len(result["logs"]) >= 1


class TestGitLogOperation:
    """Tests for git log operation handling."""

    @pytest.mark.asyncio
    async def test_git_log_operation(self, executor, sample_context, git_repo):
        """Git log runs log --oneline -5."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git log",
            arguments=["log"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "abc1234 First commit\ndef5678 Second commit",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert result["operation"] == "log"


class TestGitBranchOperation:
    """Tests for git branch operation handling."""

    @pytest.mark.asyncio
    async def test_git_branch_operation(self, executor, sample_context, git_repo):
        """Git branch runs branch --show-current."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git branch",
            arguments=["branch"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "feature-branch\n",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert result["operation"] == "branch"
        assert result["summary"]["branch"] == "feature-branch"


class TestGitAddOperation:
    """Tests for git add operation handling."""

    @pytest.mark.asyncio
    async def test_git_add_default_targets(self, executor, sample_context, git_repo):
        """Git add defaults to '.' when no targets specified."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git add",
            arguments=["add"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                await executor._execute_git(sample_context)

        # Check that git add was called
        assert mock_run.called

    @pytest.mark.asyncio
    async def test_git_add_specific_files(self, executor, sample_context, git_repo):
        """Git add uses specified file targets."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git add file1.py file2.py",
            arguments=["add", "file1.py", "file2.py"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                await executor._execute_git(sample_context)

        call_args = mock_run.call_args[0][0]
        assert "file1.py" in call_args
        assert "file2.py" in call_args


class TestGitCommitOperation:
    """Tests for git commit operation handling."""

    @pytest.mark.asyncio
    async def test_git_commit_with_message(self, executor, sample_context, git_repo):
        """Git commit uses provided message."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git commit --message 'test commit'",
            arguments=["commit"],
            flags={},
            parameters={"message": "test commit"},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "[main abc1234] test commit",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert result["operation"] == "commit"
        assert result["summary"].get("commit_message") == "test commit"

    @pytest.mark.asyncio
    async def test_git_commit_dry_run_without_apply(self, executor, sample_context, git_repo):
        """Git commit uses --dry-run when apply flag not set."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git commit",
            arguments=["commit"],
            flags={},
            parameters={"message": "test"},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                await executor._execute_git(sample_context)

        call_args = mock_run.call_args[0][0]
        assert "--dry-run" in call_args

    @pytest.mark.asyncio
    async def test_git_commit_real_with_apply_flag(self, executor, sample_context, git_repo):
        """Git commit skips --dry-run when apply flag is set."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git commit --apply",
            arguments=["commit"],
            flags={"apply": True},
            parameters={"message": "test"},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                await executor._execute_git(sample_context)

        call_args = mock_run.call_args[0][0]
        assert "--dry-run" not in call_args


class TestGitGenericOperation:
    """Tests for generic git operation handling."""

    @pytest.mark.asyncio
    async def test_git_generic_operation(self, executor, sample_context, git_repo):
        """Git passes unknown operations through."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git stash",
            arguments=["stash"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "Saved working directory",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert result["operation"] == "stash"


class TestGitWarnings:
    """Tests for git warning handling."""

    @pytest.mark.asyncio
    async def test_git_records_warnings_on_error(self, executor, sample_context, git_repo):
        """Git records warnings when command fails."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            arguments=["status"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "fatal: not a git repository",
                "exit_code": 128,
                "duration_s": 0.1,
                "error": "fatal: not a git repository",
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert "warnings" in result
        assert len(result["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_git_status_failed_on_warnings(self, executor, sample_context, git_repo):
        """Git status is 'git_failed' when warnings present."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            arguments=["status"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "",
                "stderr": "error occurred",
                "exit_code": 1,
                "duration_s": 0.1,
                "error": "error occurred",
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert result["status"] == "git_failed"


class TestGitOutputStructure:
    """Tests for git output structure."""

    @pytest.mark.asyncio
    async def test_git_output_has_logs(self, executor, sample_context, git_repo):
        """Git output includes command logs."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            arguments=["status"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "## main",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert "logs" in result
        assert isinstance(result["logs"], list)

    @pytest.mark.asyncio
    async def test_git_output_has_mode(self, executor, sample_context, git_repo):
        """Git output includes behavior mode."""
        executor.repo_root = git_repo
        sample_context.command = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            arguments=["status"],
            flags={},
            parameters={},
            description="Git operations",
        )

        with patch.object(executor, "_run_command") as mock_run:
            mock_run.return_value = {
                "stdout": "## main",
                "stderr": "",
                "exit_code": 0,
                "duration_s": 0.1,
            }
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_git(sample_context)

        assert "mode" in result
