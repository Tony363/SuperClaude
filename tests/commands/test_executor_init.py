"""Tests for CommandExecutor initialization and lifecycle methods."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands import CommandResult


class TestCommandExecutorInit:
    """Tests for CommandExecutor initialization."""

    def test_init_with_explicit_repo_root(self, tmp_path, monkeypatch):
        """Executor accepts explicit repo_root parameter."""
        target_repo = tmp_path / "target"
        target_repo.mkdir()
        monkeypatch.delenv("SUPERCLAUDE_REPO_ROOT", raising=False)
        monkeypatch.delenv("SUPERCLAUDE_METRICS_DIR", raising=False)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=target_repo)

        assert executor.repo_root == target_repo.resolve()

    def test_init_sets_env_variables(self, tmp_path, monkeypatch):
        """Executor sets environment variables on init."""
        target_repo = tmp_path / "target"
        target_repo.mkdir()
        monkeypatch.delenv("SUPERCLAUDE_REPO_ROOT", raising=False)
        monkeypatch.delenv("SUPERCLAUDE_METRICS_DIR", raising=False)

        registry = CommandRegistry()
        parser = CommandParser()
        CommandExecutor(registry, parser, repo_root=target_repo)

        assert os.environ.get("SUPERCLAUDE_REPO_ROOT") == str(target_repo.resolve())
        expected_metrics = str(target_repo.resolve() / ".superclaude_metrics")
        assert os.environ.get("SUPERCLAUDE_METRICS_DIR") == expected_metrics

    def test_init_from_env_variable(self, tmp_path, monkeypatch):
        """Executor reads repo_root from environment variable."""
        target_repo = tmp_path / "env_repo"
        target_repo.mkdir()
        monkeypatch.setenv("SUPERCLAUDE_REPO_ROOT", str(target_repo))

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        assert executor.repo_root == target_repo.resolve()

    def test_init_detects_git_root(self, temp_repo, monkeypatch):
        """Executor auto-detects git repository root."""
        monkeypatch.delenv("SUPERCLAUDE_REPO_ROOT", raising=False)
        monkeypatch.chdir(temp_repo)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        assert executor.repo_root == temp_repo.resolve()

    def test_init_creates_hooks_dict(self, command_workspace):
        """Executor initializes hooks dictionary."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        assert "pre_execute" in executor.hooks
        assert "post_execute" in executor.hooks
        assert "on_error" in executor.hooks

    def test_init_creates_empty_history(self, command_workspace):
        """Executor starts with empty execution history."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        assert executor.execution_history == []

    def test_init_with_none_repo_root_no_git(self, tmp_path, monkeypatch):
        """Executor handles missing git repo gracefully."""
        monkeypatch.delenv("SUPERCLAUDE_REPO_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        # Should not crash, repo_root may be None
        assert executor is not None


class TestNormalizeRepoRoot:
    """Tests for _normalize_repo_root method."""

    def test_normalize_with_provided_path(self, tmp_path, monkeypatch):
        """normalize_repo_root uses provided path."""
        target = tmp_path / "repo"
        target.mkdir()
        monkeypatch.delenv("SUPERCLAUDE_REPO_ROOT", raising=False)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=target)

        result = executor._normalize_repo_root(target)
        assert result == target.resolve()

    def test_normalize_from_env(self, tmp_path, monkeypatch):
        """normalize_repo_root reads from environment."""
        target = tmp_path / "env_repo"
        target.mkdir()
        monkeypatch.setenv("SUPERCLAUDE_REPO_ROOT", str(target))

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        result = executor._normalize_repo_root(None)
        assert result == target.resolve()

    def test_normalize_resolves_path(self, tmp_path, monkeypatch):
        """normalize_repo_root resolves relative paths."""
        monkeypatch.delenv("SUPERCLAUDE_REPO_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        result = executor._normalize_repo_root(Path("."))
        assert result is not None
        assert result.is_absolute()


class TestDetectRepoRoot:
    """Tests for _detect_repo_root method."""

    def test_detect_finds_git_repo(self, temp_repo, monkeypatch):
        """detect_repo_root finds .git directory."""
        monkeypatch.chdir(temp_repo)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._detect_repo_root()
        assert result == temp_repo.resolve()

    def test_detect_finds_parent_git_repo(self, temp_repo, monkeypatch):
        """detect_repo_root searches parent directories."""
        subdir = temp_repo / "src" / "module"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=temp_repo)

        result = executor._detect_repo_root()
        assert result == temp_repo.resolve()

    def test_detect_returns_none_without_git(self, tmp_path, monkeypatch):
        """detect_repo_root returns None when no .git exists."""
        monkeypatch.chdir(tmp_path)

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=tmp_path)

        result = executor._detect_repo_root()
        assert result is None


class TestSetAgentLoader:
    """Tests for set_agent_loader method."""

    def test_set_agent_loader(self, executor, mock_agent_loader):
        """set_agent_loader assigns the loader."""
        executor.set_agent_loader(mock_agent_loader)
        assert executor.agent_loader == mock_agent_loader

    def test_set_agent_loader_none_creates_default(self, executor):
        """set_agent_loader creates default loader for None."""
        executor.set_agent_loader(None)
        assert executor.agent_loader is not None


class TestRegisterHook:
    """Tests for register_hook method."""

    def test_register_pre_execute_hook(self, executor):
        """register_hook adds pre_execute hook."""
        hook = AsyncMock()
        executor.register_hook("pre_execute", hook)

        assert hook in executor.hooks["pre_execute"]

    def test_register_post_execute_hook(self, executor):
        """register_hook adds post_execute hook."""
        hook = AsyncMock()
        executor.register_hook("post_execute", hook)

        assert hook in executor.hooks["post_execute"]

    def test_register_on_error_hook(self, executor):
        """register_hook adds on_error hook."""
        hook = AsyncMock()
        executor.register_hook("on_error", hook)

        assert hook in executor.hooks["on_error"]

    def test_register_multiple_hooks(self, executor):
        """register_hook allows multiple hooks per type."""
        hook1 = AsyncMock()
        hook2 = AsyncMock()

        executor.register_hook("pre_execute", hook1)
        executor.register_hook("pre_execute", hook2)

        assert len(executor.hooks["pre_execute"]) == 2

    def test_register_invalid_hook_type(self, executor):
        """register_hook ignores invalid hook types."""
        hook = AsyncMock()
        executor.register_hook("invalid_type", hook)

        assert "invalid_type" not in executor.hooks


class TestGenerateSessionId:
    """Tests for _generate_session_id method."""

    def test_generate_session_id_format(self, executor):
        """_generate_session_id returns 12-char hex string."""
        session_id = executor._generate_session_id()

        assert len(session_id) == 12
        assert all(c in "0123456789abcdef" for c in session_id)

    def test_generate_session_id_unique(self, executor):
        """_generate_session_id produces unique IDs."""
        ids = {executor._generate_session_id() for _ in range(100)}
        # Most should be unique (allowing some collision due to fast generation)
        assert len(ids) >= 90


class TestHistory:
    """Tests for get_history and clear_history methods."""

    def test_get_history_empty(self, executor):
        """get_history returns empty list initially."""
        assert executor.get_history() == []

    def test_get_history_with_limit(self, executor):
        """get_history respects limit parameter."""
        # Add some history entries manually
        for i in range(15):
            executor.execution_history.append(
                CommandResult(
                    success=True,
                    command_name=f"test_{i}",
                    output=f"output_{i}",
                )
            )

        result = executor.get_history(limit=5)
        assert len(result) == 5
        assert result[-1].command_name == "test_14"

    def test_get_history_returns_recent(self, executor):
        """get_history returns most recent entries."""
        for i in range(5):
            executor.execution_history.append(
                CommandResult(
                    success=True,
                    command_name=f"test_{i}",
                    output=f"output_{i}",
                )
            )

        result = executor.get_history(limit=3)
        assert [r.command_name for r in result] == ["test_2", "test_3", "test_4"]

    def test_clear_history(self, executor):
        """clear_history empties the history."""
        executor.execution_history.append(
            CommandResult(success=True, command_name="test", output="output")
        )

        executor.clear_history()

        assert executor.execution_history == []

    def test_clear_history_when_empty(self, executor):
        """clear_history handles empty history."""
        executor.clear_history()  # Should not raise
        assert executor.execution_history == []


class TestRunHooks:
    """Tests for _run_hooks async method."""

    @pytest.mark.asyncio
    async def test_run_hooks_executes_all(self, executor, sample_context):
        """_run_hooks executes all registered hooks."""
        hook1 = AsyncMock()
        hook2 = AsyncMock()

        executor.register_hook("pre_execute", hook1)
        executor.register_hook("pre_execute", hook2)

        await executor._run_hooks("pre_execute", sample_context)

        hook1.assert_called_once_with(sample_context)
        hook2.assert_called_once_with(sample_context)

    @pytest.mark.asyncio
    async def test_run_hooks_handles_exception(self, executor, sample_context):
        """_run_hooks continues after hook exception."""
        failing_hook = AsyncMock(side_effect=Exception("hook error"))
        success_hook = AsyncMock()

        executor.register_hook("pre_execute", failing_hook)
        executor.register_hook("pre_execute", success_hook)

        await executor._run_hooks("pre_execute", sample_context)

        # Both should have been called
        failing_hook.assert_called_once()
        success_hook.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_hooks_unknown_type(self, executor, sample_context):
        """_run_hooks handles unknown hook type gracefully."""
        # Should not raise
        await executor._run_hooks("unknown_type", sample_context)
