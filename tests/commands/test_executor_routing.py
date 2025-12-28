"""Tests for CommandExecutor routing and execution flag methods."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from SuperClaude.Commands import (
    CommandContext,
    CommandResult,
)
from SuperClaude.Commands.parser import ParsedCommand


class TestResolveThinkLevel:
    """Tests for _resolve_think_level method."""

    def test_resolve_think_level_default(self, executor):
        """resolve_think_level returns default level 2 when not specified."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            flags={},
            parameters={},
        )
        result = executor._resolve_think_level(parsed)
        assert result["level"] == 2
        assert result["requested"] is False

    def test_resolve_think_level_flag_only(self, executor):
        """resolve_think_level returns level 3 when --think flag present."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --think feature",
            flags={"think": True},
            parameters={},
        )
        result = executor._resolve_think_level(parsed)
        assert result["level"] == 3
        assert result["requested"] is True

    def test_resolve_think_level_with_value(self, executor):
        """resolve_think_level uses parameter value."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --think=1",
            flags={},
            parameters={"think": "1"},
        )
        result = executor._resolve_think_level(parsed)
        assert result["level"] == 1
        assert result["requested"] is True

    def test_resolve_think_level_alias_think_level(self, executor):
        """resolve_think_level accepts think_level parameter."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --think-level=2",
            flags={},
            parameters={"think_level": "2"},
        )
        result = executor._resolve_think_level(parsed)
        assert result["level"] == 2
        assert result["requested"] is True

    def test_resolve_think_level_alias_depth(self, executor):
        """resolve_think_level accepts depth parameter."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --depth=3",
            flags={},
            parameters={"depth": "3"},
        )
        result = executor._resolve_think_level(parsed)
        assert result["level"] == 3
        assert result["requested"] is True

    def test_resolve_think_level_clamped_below(self, executor):
        """resolve_think_level clamps values below 1."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --think=0",
            flags={},
            parameters={"think": "0"},
        )
        result = executor._resolve_think_level(parsed)
        assert result["level"] == 1  # Clamped to minimum

    def test_resolve_think_level_clamped_above(self, executor):
        """resolve_think_level clamps values above 3."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --think=10",
            flags={},
            parameters={"think": "10"},
        )
        result = executor._resolve_think_level(parsed)
        assert result["level"] == 3  # Clamped to maximum


class TestResolveLoopRequest:
    """Tests for _resolve_loop_request method."""

    def test_resolve_loop_disabled_by_default(self, executor):
        """resolve_loop_request returns disabled when no flags."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            flags={},
            parameters={},
        )
        result = executor._resolve_loop_request(parsed)
        assert result["enabled"] is False
        assert result["iterations"] is None
        assert result["min_improvement"] is None

    def test_resolve_loop_enabled_by_flag(self, executor):
        """resolve_loop_request enables loop with --loop flag."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --loop feature",
            flags={"loop": True},
            parameters={},
        )
        result = executor._resolve_loop_request(parsed)
        assert result["enabled"] is True

    def test_resolve_loop_with_iterations(self, executor):
        """resolve_loop_request captures iteration count."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --loop=3",
            flags={},
            parameters={"loop": "3"},
        )
        result = executor._resolve_loop_request(parsed)
        assert result["enabled"] is True
        assert result["iterations"] == 3

    def test_resolve_loop_with_loop_count_alias(self, executor):
        """resolve_loop_request accepts loop-count alias."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --loop-count=5",
            flags={},
            parameters={"loop-count": "5"},
        )
        result = executor._resolve_loop_request(parsed)
        assert result["enabled"] is True
        # Should be clamped to MAX_ITERATIONS if above
        assert result["iterations"] is not None

    def test_resolve_loop_with_min_improvement(self, executor):
        """resolve_loop_request captures minimum improvement."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --loop --loop-min=0.1",
            flags={"loop": True},
            parameters={"loop-min": "0.1"},
        )
        result = executor._resolve_loop_request(parsed)
        assert result["enabled"] is True
        assert result["min_improvement"] == 0.1

    def test_resolve_loop_min_enables_loop(self, executor):
        """resolve_loop_request enables loop when min_improvement specified."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --loop-improvement=0.05",
            flags={},
            parameters={"loop_improvement": "0.05"},
        )
        result = executor._resolve_loop_request(parsed)
        assert result["enabled"] is True
        assert result["min_improvement"] == 0.05


class TestResolvePalReviewRequest:
    """Tests for _resolve_pal_review_request method."""

    def test_resolve_pal_review_disabled_by_default(self, executor):
        """resolve_pal_review_request disabled when no loop or flag."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            flags={},
            parameters={},
        )
        result = executor._resolve_pal_review_request(parsed, loop_requested=False)
        assert result["enabled"] is False

    def test_resolve_pal_review_enabled_by_loop(self, executor):
        """resolve_pal_review_request enabled when loop requested."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --loop feature",
            flags={},
            parameters={},
        )
        result = executor._resolve_pal_review_request(parsed, loop_requested=True)
        assert result["enabled"] is True
        assert result["model"] == "gpt-5"  # Default model

    def test_resolve_pal_review_enabled_by_flag(self, executor):
        """resolve_pal_review_request enabled by --pal-review flag."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --pal-review feature",
            flags={"pal-review": True},
            parameters={},
        )
        result = executor._resolve_pal_review_request(parsed, loop_requested=False)
        assert result["enabled"] is True

    def test_resolve_pal_review_custom_model(self, executor):
        """resolve_pal_review_request uses custom model."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --pal-model=claude",
            flags={},
            parameters={"pal-model": "claude"},
        )
        result = executor._resolve_pal_review_request(parsed, loop_requested=False)
        assert result["enabled"] is True
        assert result["model"] == "claude"


class TestPrepareMode:
    """Tests for _prepare_mode method."""

    def test_prepare_mode_returns_dict(self, executor):
        """_prepare_mode returns dict with mode and context."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            flags={},
            parameters={},
        )
        result = executor._prepare_mode(parsed)
        assert "mode" in result
        assert "context" in result

    def test_prepare_mode_default_normal(self, executor):
        """_prepare_mode defaults to normal mode."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            flags={},
            parameters={},
        )
        result = executor._prepare_mode(parsed)
        assert result["mode"] == "normal"


class TestApplyExecutionFlags:
    """Tests for _apply_execution_flags method."""

    def test_apply_execution_flags_sets_think_level(
        self, executor, sample_parsed_command, sample_metadata
    ):
        """_apply_execution_flags sets think level on context."""
        context = CommandContext(
            command=sample_parsed_command,
            metadata=sample_metadata,
            session_id="test-123",
        )
        executor._apply_execution_flags(context)

        assert hasattr(context, "think_level")
        assert context.think_level in [1, 2, 3]

    def test_apply_execution_flags_sets_loop_enabled(self, executor, sample_metadata):
        """_apply_execution_flags sets loop_enabled on context."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --loop feature",
            flags={"loop": True},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        executor._apply_execution_flags(context)

        assert context.loop_enabled is True

    def test_apply_execution_flags_sets_consensus_forced(self, executor, sample_metadata):
        """_apply_execution_flags sets consensus_forced on context."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --consensus feature",
            flags={"consensus": True},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        executor._apply_execution_flags(context)

        assert context.consensus_forced is True


class TestExecuteCommandLogic:
    """Tests for _execute_command_logic dispatch."""

    @pytest.mark.asyncio
    async def test_execute_command_logic_routes_implement(self, executor, sample_metadata):
        """_execute_command_logic routes to _execute_implement."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            flags={},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        context.results = {"executed_operations": []}
        context.agent_instances = {}
        context.agent_outputs = {}

        with patch.object(executor, "_execute_implement", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "success"}
            result = await executor._execute_command_logic(context)

            mock.assert_called_once_with(context)
            assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_execute_command_logic_routes_analyze(self, executor, sample_metadata):
        """_execute_command_logic routes to _execute_analyze."""
        parsed = ParsedCommand(
            name="analyze",
            raw_string="/sc:analyze code",
            flags={},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        context.results = {}

        with patch.object(executor, "_execute_analyze", new_callable=AsyncMock) as mock:
            mock.return_value = {"analysis": "complete"}
            await executor._execute_command_logic(context)

            mock.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_execute_command_logic_routes_test(self, executor, sample_metadata):
        """_execute_command_logic routes to _execute_test."""
        parsed = ParsedCommand(
            name="test",
            raw_string="/sc:test",
            flags={},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        context.results = {}

        with patch.object(executor, "_execute_test", new_callable=AsyncMock) as mock:
            mock.return_value = {"tests": "passed"}
            await executor._execute_command_logic(context)

            mock.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_execute_command_logic_routes_build(self, executor, sample_metadata):
        """_execute_command_logic routes to _execute_build."""
        parsed = ParsedCommand(
            name="build",
            raw_string="/sc:build",
            flags={},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        context.results = {}

        with patch.object(executor, "_execute_build", new_callable=AsyncMock) as mock:
            mock.return_value = {"build": "success"}
            await executor._execute_command_logic(context)

            mock.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_execute_command_logic_routes_git(self, executor, sample_metadata):
        """_execute_command_logic routes to _execute_git."""
        parsed = ParsedCommand(
            name="git",
            raw_string="/sc:git status",
            flags={},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        context.results = {}

        with patch.object(executor, "_execute_git", new_callable=AsyncMock) as mock:
            mock.return_value = {"git": "status"}
            await executor._execute_command_logic(context)

            mock.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_execute_command_logic_routes_workflow(self, executor, sample_metadata):
        """_execute_command_logic routes to _execute_workflow."""
        parsed = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow run",
            flags={},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        context.results = {}

        with patch.object(executor, "_execute_workflow", new_callable=AsyncMock) as mock:
            mock.return_value = {"workflow": "executed"}
            await executor._execute_command_logic(context)

            mock.assert_called_once_with(context)

    @pytest.mark.asyncio
    async def test_execute_command_logic_routes_generic(self, executor, sample_metadata):
        """_execute_command_logic routes unknown commands to _execute_generic."""
        parsed = ParsedCommand(
            name="custom",
            raw_string="/sc:custom",
            flags={},
            parameters={},
        )
        context = CommandContext(
            command=parsed,
            metadata=sample_metadata,
            session_id="test-123",
        )
        context.results = {}

        with patch.object(executor, "_execute_generic", new_callable=AsyncMock) as mock:
            mock.return_value = {"generic": "output"}
            await executor._execute_command_logic(context)

            mock.assert_called_once_with(context)


class TestExecute:
    """Tests for main execute() entry point."""

    @pytest.mark.asyncio
    async def test_execute_returns_error_for_unknown_command(self, executor):
        """execute returns error result for unknown commands."""
        result = await executor.execute("/sc:nonexistent arg")

        assert result.success is False
        assert "not found" in str(result.errors).lower()

    @pytest.mark.asyncio
    async def test_execute_parses_command_string(self, executor, monkeypatch):
        """execute parses command string through parser."""
        # Register a known command
        from SuperClaude.Commands.registry import CommandMetadata

        executor.registry.register_command(
            CommandMetadata(
                name="testcmd",
                description="Test command",
                category="test",
                complexity="low",
            )
        )

        with patch.object(executor, "_execute_command_logic", new_callable=AsyncMock) as mock_logic:
            mock_logic.return_value = {"status": "done"}
            with patch.object(executor, "_snapshot_repo_changes") as mock_snap:
                mock_snap.return_value = {}
                with patch.object(
                    executor, "_ensure_consensus", new_callable=AsyncMock
                ) as mock_cons:
                    mock_cons.return_value = {"decision": "approve"}

                    await executor.execute("/sc:testcmd arg1")

                    # Logic was called
                    assert mock_logic.called


class TestExecuteChain:
    """Tests for execute_chain method."""

    @pytest.mark.asyncio
    async def test_execute_chain_runs_sequentially(self, executor, monkeypatch):
        """execute_chain runs commands in sequence."""
        call_order = []

        async def mock_execute(cmd):
            call_order.append(cmd)
            return CommandResult(success=True, command_name=cmd, output=cmd)

        with patch.object(executor, "execute", side_effect=mock_execute):
            results = await executor.execute_chain(["/sc:first", "/sc:second", "/sc:third"])

            assert len(results) == 3
            assert call_order == ["/sc:first", "/sc:second", "/sc:third"]

    @pytest.mark.asyncio
    async def test_execute_chain_stops_on_failure(self, executor):
        """execute_chain stops when a command fails."""
        call_count = 0

        async def mock_execute(cmd):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return CommandResult(success=False, command_name=cmd, output=None)
            return CommandResult(success=True, command_name=cmd, output="ok")

        with patch.object(executor, "execute", side_effect=mock_execute):
            results = await executor.execute_chain(["/sc:first", "/sc:second", "/sc:third"])

            # Should stop after second command fails
            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False

    @pytest.mark.asyncio
    async def test_execute_chain_empty_list(self, executor):
        """execute_chain handles empty command list."""
        results = await executor.execute_chain([])
        assert results == []


class TestExecuteParallel:
    """Tests for execute_parallel method."""

    @pytest.mark.asyncio
    async def test_execute_parallel_runs_concurrently(self, executor):
        """execute_parallel runs all commands concurrently."""
        execution_times = []

        async def mock_execute(cmd):
            import time

            start = time.time()
            await asyncio.sleep(0.01)  # Small delay
            execution_times.append((cmd, time.time() - start))
            return CommandResult(success=True, command_name=cmd, output=cmd)

        with patch.object(executor, "execute", side_effect=mock_execute):
            results = await executor.execute_parallel(["/sc:cmd1", "/sc:cmd2", "/sc:cmd3"])

            assert len(results) == 3
            # All commands should complete

    @pytest.mark.asyncio
    async def test_execute_parallel_continues_on_failure(self, executor):
        """execute_parallel continues even when some commands fail."""

        async def mock_execute(cmd):
            if "fail" in cmd:
                return CommandResult(success=False, command_name=cmd, output=None)
            return CommandResult(success=True, command_name=cmd, output="ok")

        with patch.object(executor, "execute", side_effect=mock_execute):
            results = await executor.execute_parallel(["/sc:pass1", "/sc:fail", "/sc:pass2"])

            assert len(results) == 3
            # Find results by command name
            pass_results = [r for r in results if r.success]
            fail_results = [r for r in results if not r.success]

            assert len(pass_results) == 2
            assert len(fail_results) == 1

    @pytest.mark.asyncio
    async def test_execute_parallel_empty_list(self, executor):
        """execute_parallel handles empty command list."""
        results = await executor.execute_parallel([])
        assert results == []
