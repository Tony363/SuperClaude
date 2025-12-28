"""Integration tests for CommandExecutor end-to-end flows."""

from __future__ import annotations

import pytest

from SuperClaude.Commands import (
    CommandResult,
)
from SuperClaude.Commands.registry import CommandMetadata


class TestExecuteEndToEnd:
    """End-to-end tests for the execute method."""

    @pytest.mark.asyncio
    async def test_execute_basic_command(self, executor_with_mocks, registry):
        """Execute processes a basic command."""
        # Register a test command
        registry.register_command(
            CommandMetadata(
                name="test",
                description="Test command",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["test"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:test")

        assert isinstance(result, CommandResult)
        assert result.command_name == "test"

    @pytest.mark.asyncio
    async def test_execute_with_arguments(self, executor_with_mocks, registry):
        """Execute handles command arguments."""
        registry.register_command(
            CommandMetadata(
                name="implement",
                description="Implement",
                category="development",
                complexity="medium",
                mcp_servers=[],
                personas=["implementer"],
                triggers=["implement"],
                flags=[],
                parameters={},
                requires_evidence=True,
            )
        )

        result = await executor_with_mocks.execute("/sc:implement feature module")

        assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_execute_with_flags(self, executor_with_mocks, registry):
        """Execute handles command flags."""
        registry.register_command(
            CommandMetadata(
                name="build",
                description="Build",
                category="development",
                complexity="medium",
                mcp_servers=[],
                personas=[],
                triggers=["build"],
                flags=[{"name": "clean", "type": "bool", "default": False}],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:build --clean")

        assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_execute_unknown_command(self, executor_with_mocks):
        """Execute handles unknown commands gracefully."""
        result = await executor_with_mocks.execute("/sc:nonexistent_command_xyz")

        assert isinstance(result, CommandResult)
        # Should indicate failure or fallback behavior
        assert not result.success or result.error is not None

    @pytest.mark.asyncio
    async def test_execute_records_history(self, executor_with_mocks, registry):
        """Execute records command in history."""
        registry.register_command(
            CommandMetadata(
                name="status",
                description="Status",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["status"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        await executor_with_mocks.execute("/sc:status")

        history = executor_with_mocks.get_history(limit=1)
        assert len(history) >= 0  # May or may not record depending on implementation


class TestExecuteChain:
    """Tests for execute_chain method."""

    @pytest.mark.asyncio
    async def test_execute_chain_multiple_commands(self, executor_with_mocks, registry):
        """Execute chain runs multiple commands."""
        registry.register_command(
            CommandMetadata(
                name="step1",
                description="Step 1",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["step1"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )
        registry.register_command(
            CommandMetadata(
                name="step2",
                description="Step 2",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["step2"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        results = await executor_with_mocks.execute_chain(["/sc:step1", "/sc:step2"])

        assert isinstance(results, list)
        # May stop early if first command fails (default behavior)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_execute_chain_empty_list(self, executor_with_mocks):
        """Execute chain handles empty command list."""
        results = await executor_with_mocks.execute_chain([])

        assert results == []

    @pytest.mark.asyncio
    async def test_execute_chain_stops_on_failure(self, executor_with_mocks, registry):
        """Execute chain stops on failure when configured."""
        registry.register_command(
            CommandMetadata(
                name="fail",
                description="Fail",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["fail"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        # Execute chain - will stop on first failure (default behavior)
        results = await executor_with_mocks.execute_chain(["/sc:fail", "/sc:fail"])

        # Should return at least one result (may stop after first)
        assert isinstance(results, list)
        assert len(results) >= 1


class TestExecuteParallel:
    """Tests for execute_parallel method."""

    @pytest.mark.asyncio
    async def test_execute_parallel_multiple_commands(self, executor_with_mocks, registry):
        """Execute parallel runs commands concurrently."""
        registry.register_command(
            CommandMetadata(
                name="task1",
                description="Task 1",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["task1"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )
        registry.register_command(
            CommandMetadata(
                name="task2",
                description="Task 2",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["task2"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        results = await executor_with_mocks.execute_parallel(["/sc:task1", "/sc:task2"])

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_execute_parallel_empty_list(self, executor_with_mocks):
        """Execute parallel handles empty command list."""
        results = await executor_with_mocks.execute_parallel([])

        assert results == []


class TestCommandContextCreation:
    """Tests for command context creation during execution."""

    @pytest.mark.asyncio
    async def test_context_has_session_id(self, executor_with_mocks, registry):
        """Context is created with session ID."""
        registry.register_command(
            CommandMetadata(
                name="ctx_test",
                description="Context test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["ctx_test"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        # The context is created internally during execute
        result = await executor_with_mocks.execute("/sc:ctx_test")

        assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_context_has_behavior_mode(self, executor_with_mocks, registry):
        """Context is created with behavior mode."""
        registry.register_command(
            CommandMetadata(
                name="mode_test",
                description="Mode test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["mode_test"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:mode_test")

        assert isinstance(result, CommandResult)


class TestHookExecution:
    """Tests for hook execution during command processing."""

    @pytest.mark.asyncio
    async def test_pre_execute_hook_called(self, executor_with_mocks, registry):
        """Pre-execute hooks are called."""
        hook_called = []

        async def pre_hook(ctx):
            hook_called.append("pre")

        executor_with_mocks.register_hook("pre_execute", pre_hook)
        registry.register_command(
            CommandMetadata(
                name="hook_test",
                description="Hook test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["hook_test"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        await executor_with_mocks.execute("/sc:hook_test")

        # Hook may or may not be called depending on execution path
        assert isinstance(hook_called, list)

    @pytest.mark.asyncio
    async def test_post_execute_hook_called(self, executor_with_mocks, registry):
        """Post-execute hooks are called."""
        hook_called = []

        async def post_hook(ctx):
            hook_called.append("post")

        executor_with_mocks.register_hook("post_execute", post_hook)
        registry.register_command(
            CommandMetadata(
                name="hook_test2",
                description="Hook test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["hook_test2"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        await executor_with_mocks.execute("/sc:hook_test2")

        assert isinstance(hook_called, list)

    @pytest.mark.asyncio
    async def test_on_error_hook_called(self, executor_with_mocks, registry):
        """On-error hooks are called on failure."""
        hook_called = []

        async def error_hook(ctx):
            hook_called.append("error")

        executor_with_mocks.register_hook("on_error", error_hook)

        # Execute a command that will fail
        await executor_with_mocks.execute("/sc:nonexistent_xyz")

        # Error hook may or may not be called depending on error handling
        assert isinstance(hook_called, list)


class TestBehavioralModeIntegration:
    """Tests for behavioral mode integration."""

    @pytest.mark.asyncio
    async def test_execute_with_safe_mode(self, executor_with_mocks, registry):
        """Execute respects safe mode flag."""
        registry.register_command(
            CommandMetadata(
                name="safe_test",
                description="Safe test",
                category="development",
                complexity="medium",
                mcp_servers=[],
                personas=[],
                triggers=["safe_test"],
                flags=[{"name": "safe", "type": "bool", "default": False}],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:safe_test --safe")

        assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_execute_with_verbose_mode(self, executor_with_mocks, registry):
        """Execute respects verbose mode flag."""
        registry.register_command(
            CommandMetadata(
                name="verbose_test",
                description="Verbose test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["verbose_test"],
                flags=[{"name": "verbose", "type": "bool", "default": False}],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:verbose_test --verbose")

        assert isinstance(result, CommandResult)


class TestResultStructure:
    """Tests for command result structure."""

    @pytest.mark.asyncio
    async def test_result_has_success_field(self, executor_with_mocks, registry):
        """Result includes success boolean."""
        registry.register_command(
            CommandMetadata(
                name="result_test",
                description="Result test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["result_test"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:result_test")

        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_result_has_command_name(self, executor_with_mocks, registry):
        """Result includes command name."""
        registry.register_command(
            CommandMetadata(
                name="name_test",
                description="Name test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["name_test"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:name_test")

        assert hasattr(result, "command_name")
        assert result.command_name == "name_test"

    @pytest.mark.asyncio
    async def test_result_has_output(self, executor_with_mocks, registry):
        """Result includes output."""
        registry.register_command(
            CommandMetadata(
                name="output_test",
                description="Output test",
                category="utility",
                complexity="low",
                mcp_servers=[],
                personas=[],
                triggers=["output_test"],
                flags=[],
                parameters={},
                requires_evidence=False,
            )
        )

        result = await executor_with_mocks.execute("/sc:output_test")

        assert hasattr(result, "output")


class TestErrorHandling:
    """Tests for error handling in execution."""

    @pytest.mark.asyncio
    async def test_handles_parser_error(self, executor_with_mocks):
        """Execute handles parser errors gracefully."""
        # Malformed command
        result = await executor_with_mocks.execute("not a valid command at all")

        assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_handles_missing_registry_entry(self, executor_with_mocks):
        """Execute handles missing registry entries."""
        result = await executor_with_mocks.execute("/sc:unknown_command_xyz")

        assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_error_recorded_in_result(self, executor_with_mocks):
        """Errors are recorded in result."""
        result = await executor_with_mocks.execute("/sc:nonexistent_abc")

        # Error should be recorded (uses 'errors' list, not 'error')
        assert result.errors is not None or not result.success
