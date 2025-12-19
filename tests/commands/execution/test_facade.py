"""Tests for ExecutionFacade."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from SuperClaude.Commands.execution.facade import (
    DEFAULT_DECOMPOSED_COMMANDS,
    DECOMPOSED_COMMANDS_ENV_VAR,
    DECOMPOSED_ENV_VAR,
    ExecutionFacade,
)
from SuperClaude.Commands.execution.routing import (
    CommandRouter,
    ExecutionPlan,
    RuntimeMode,
)


class TestExecutionFacadeIsEnabled:
    """Tests for ExecutionFacade.is_enabled() static method."""

    def test_disabled_by_default(self, env_isolation):
        """Feature is disabled when env var not set."""
        env_isolation.clear()
        assert ExecutionFacade.is_enabled() is False

    def test_enabled_with_1(self, env_isolation, monkeypatch):
        """Feature enabled with SUPERCLAUDE_DECOMPOSED=1."""
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "1")
        assert ExecutionFacade.is_enabled() is True

    def test_enabled_with_true(self, env_isolation, monkeypatch):
        """Feature enabled with SUPERCLAUDE_DECOMPOSED=true."""
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "true")
        assert ExecutionFacade.is_enabled() is True

    def test_enabled_with_yes(self, env_isolation, monkeypatch):
        """Feature enabled with SUPERCLAUDE_DECOMPOSED=yes."""
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "yes")
        assert ExecutionFacade.is_enabled() is True

    def test_enabled_case_insensitive(self, env_isolation, monkeypatch):
        """Feature enabled regardless of case."""
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "TRUE")
        assert ExecutionFacade.is_enabled() is True

    def test_disabled_with_0(self, env_isolation, monkeypatch):
        """Feature disabled with SUPERCLAUDE_DECOMPOSED=0."""
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "0")
        assert ExecutionFacade.is_enabled() is False

    def test_disabled_with_invalid(self, env_isolation, monkeypatch):
        """Feature disabled with invalid value."""
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "invalid")
        assert ExecutionFacade.is_enabled() is False


class TestExecutionFacadeAllowlist:
    """Tests for allowlist loading and command checking."""

    def test_default_allowlist(self, env_isolation, router):
        """Use default allowlist when env var not set."""
        env_isolation.set_allowlist(None)
        facade = ExecutionFacade(router=router)
        assert facade._allowlist == DEFAULT_DECOMPOSED_COMMANDS

    def test_empty_string_allowlist(self, env_isolation, router, monkeypatch):
        """Empty string means no commands allowed."""
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, "")
        facade = ExecutionFacade(router=router)
        assert facade._allowlist == set()

    def test_custom_allowlist(self, env_isolation, router, monkeypatch):
        """Parse custom comma-separated allowlist."""
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, "analyze,build,test")
        facade = ExecutionFacade(router=router)
        assert facade._allowlist == {"analyze", "build", "test"}

    def test_allowlist_strips_whitespace(self, env_isolation, router, monkeypatch):
        """Strip whitespace from command names."""
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, " analyze , build , test ")
        facade = ExecutionFacade(router=router)
        assert facade._allowlist == {"analyze", "build", "test"}

    def test_allowlist_lowercase(self, env_isolation, router, monkeypatch):
        """Normalize command names to lowercase."""
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, "ANALYZE,Build,TEST")
        facade = ExecutionFacade(router=router)
        assert facade._allowlist == {"analyze", "build", "test"}

    def test_allowlist_empty_entries_ignored(self, env_isolation, router, monkeypatch):
        """Ignore empty entries in allowlist."""
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, "analyze,,build,")
        facade = ExecutionFacade(router=router)
        assert facade._allowlist == {"analyze", "build"}

    def test_is_command_allowed_in_list(self, env_isolation, router):
        """Command in allowlist returns True."""
        env_isolation.set_allowlist(["analyze", "build"])
        facade = ExecutionFacade(router=router)
        assert facade.is_command_allowed("analyze") is True
        assert facade.is_command_allowed("build") is True

    def test_is_command_allowed_not_in_list(self, env_isolation, router):
        """Command not in allowlist returns False."""
        env_isolation.set_allowlist(["analyze"])
        facade = ExecutionFacade(router=router)
        assert facade.is_command_allowed("implement") is False

    def test_is_command_allowed_case_insensitive(self, env_isolation, router):
        """Command check is case insensitive."""
        env_isolation.set_allowlist(["analyze"])
        facade = ExecutionFacade(router=router)
        assert facade.is_command_allowed("ANALYZE") is True
        assert facade.is_command_allowed("Analyze") is True

    def test_explicit_allowlist_override(self, env_isolation, router):
        """Explicit allowlist in constructor overrides env."""
        env_isolation.set_allowlist(["analyze"])
        facade = ExecutionFacade(router=router, allowlist={"build", "test"})
        assert facade._allowlist == {"build", "test"}
        assert facade.is_command_allowed("analyze") is False
        assert facade.is_command_allowed("build") is True


class TestExecutionFacadeShouldHandle:
    """Tests for should_handle() decision logic."""

    def test_should_handle_false_when_disabled(self, env_isolation, router):
        """Return False when feature disabled."""
        env_isolation.set_decomposed(False)
        env_isolation.set_allowlist(["analyze"])
        facade = ExecutionFacade(router=router)
        assert facade.should_handle("analyze") is False

    def test_should_handle_false_when_not_allowed(self, env_isolation, router):
        """Return False when command not in allowlist."""
        env_isolation.set_decomposed(True)
        env_isolation.set_allowlist(["analyze"])
        facade = ExecutionFacade(router=router)
        assert facade.should_handle("implement") is False

    def test_should_handle_true_when_enabled_and_allowed(self, env_isolation, router):
        """Return True when enabled AND command in allowlist."""
        env_isolation.set_decomposed(True)
        env_isolation.set_allowlist(["analyze"])
        facade = ExecutionFacade(router=router)
        assert facade.should_handle("analyze") is True

    def test_should_handle_empty_allowlist(self, env_isolation, router, monkeypatch):
        """Return False for all commands when allowlist is empty string."""
        env_isolation.set_decomposed(True)
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, "")
        facade = ExecutionFacade(router=router)
        assert facade.should_handle("analyze") is False
        assert facade.should_handle("build") is False


class TestExecutionFacadeExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_via_skills(
        self, env_isolation, mock_skills_runtime, telemetry_capture
    ):
        """Execute command via skills runtime."""
        # Setup
        resolver = MagicMock()
        resolver.resolve.return_value = None
        resolver.can_execute_via_skills.return_value = True

        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = mock_skills_runtime
        router.resolver = resolver
        router.should_use_skills.return_value = True
        router.plan.return_value = ExecutionPlan(
            command_name="analyze",
            runtime_mode=RuntimeMode.SKILLS,
            skill_id="sc-analyze",
        )

        mock_skills_runtime.execute_command.return_value = {
            "success": True,
            "output": {"result": "analyzed"},
            "skill_id": "sc-analyze",
        }

        facade = ExecutionFacade(
            router=router,
            telemetry_client=telemetry_capture,
        )

        # Create mock context
        context = MagicMock()
        context.command.name = "analyze"
        context.command.arguments = ["src/"]
        context.command.parameters = {}
        context.command.flags = {}
        context.session_id = "test-123"

        # Execute
        result = await facade.execute(context)

        # Verify
        assert result["execution_mode"] == "skills"
        assert result["skill_id"] == "sc-analyze"

        # Check telemetry
        routed_events = telemetry_capture.get_events_by_name("execution.routed")
        assert len(routed_events) == 1
        assert routed_events[0]["payload"]["runtime_mode"] == "skills"

    @pytest.mark.asyncio
    async def test_execute_via_legacy(self, env_isolation, telemetry_capture):
        """Execute command via legacy path."""
        # Setup
        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None
        router.plan.return_value = ExecutionPlan(
            command_name="build",
            runtime_mode=RuntimeMode.LEGACY,
        )

        facade = ExecutionFacade(
            router=router,
            telemetry_client=telemetry_capture,
        )

        context = MagicMock()
        context.command.name = "build"
        context.session_id = "test-456"

        async def legacy_executor(ctx):
            return {"status": "success", "output": "build complete"}

        # Execute
        result = await facade.execute(context, legacy_executor=legacy_executor)

        # Verify
        assert result["execution_mode"] == "legacy"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_legacy_no_executor_raises(self, env_isolation):
        """Raise RuntimeError when legacy path without executor."""
        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None
        router.plan.return_value = ExecutionPlan(
            command_name="build",
            runtime_mode=RuntimeMode.LEGACY,
        )

        facade = ExecutionFacade(router=router)

        context = MagicMock()
        context.command.name = "build"
        context.session_id = "test-789"

        with pytest.raises(RuntimeError, match="no legacy_executor provided"):
            await facade.execute(context, legacy_executor=None)

    @pytest.mark.asyncio
    async def test_execute_skills_runtime_unavailable(
        self, env_isolation, telemetry_capture
    ):
        """Return error when skills runtime not available."""
        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None  # No runtime
        router.plan.return_value = ExecutionPlan(
            command_name="analyze",
            runtime_mode=RuntimeMode.SKILLS,
            skill_id="sc-analyze",
        )

        facade = ExecutionFacade(
            router=router,
            telemetry_client=telemetry_capture,
        )

        context = MagicMock()
        context.command.name = "analyze"
        context.session_id = "test-abc"

        result = await facade.execute(context)

        assert result["status"] == "error"
        assert "Skills runtime not available" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_skills_error_handling(
        self, env_isolation, mock_skills_runtime, telemetry_capture
    ):
        """Handle errors from skills execution."""
        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = mock_skills_runtime
        router.plan.return_value = ExecutionPlan(
            command_name="analyze",
            runtime_mode=RuntimeMode.SKILLS,
            skill_id="sc-analyze",
        )

        mock_skills_runtime.execute_command.side_effect = ValueError("Skill failed")

        facade = ExecutionFacade(
            router=router,
            telemetry_client=telemetry_capture,
        )

        context = MagicMock()
        context.command.name = "analyze"
        context.command.arguments = []
        context.command.parameters = {}
        context.command.flags = {}
        context.session_id = "test-err"

        result = await facade.execute(context)

        assert result["status"] == "error"
        assert "Skill failed" in result["error"]

        # Check failure recorded
        completed_events = telemetry_capture.get_events_by_name("execution.completed")
        assert len(completed_events) == 1
        assert completed_events[0]["payload"]["success"] is False

    @pytest.mark.asyncio
    async def test_execute_records_telemetry_events(
        self, env_isolation, telemetry_capture
    ):
        """Verify telemetry events are recorded."""
        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None
        router.plan.return_value = ExecutionPlan(
            command_name="test",
            runtime_mode=RuntimeMode.LEGACY,
        )

        facade = ExecutionFacade(
            router=router,
            telemetry_client=telemetry_capture,
        )

        context = MagicMock()
        context.command.name = "test"
        context.session_id = "sess-001"

        async def executor(ctx):
            return {"status": "ok"}

        await facade.execute(context, legacy_executor=executor)

        # Check events
        assert len(telemetry_capture.events) >= 2

        routed = telemetry_capture.get_events_by_name("execution.routed")
        assert len(routed) == 1
        assert routed[0]["payload"]["command"] == "test"
        assert routed[0]["payload"]["session_id"] == "sess-001"

        completed = telemetry_capture.get_events_by_name("execution.completed")
        assert len(completed) == 1
        assert completed[0]["payload"]["success"] is True

    @pytest.mark.asyncio
    async def test_execute_no_telemetry_no_error(self, env_isolation):
        """Execute works without telemetry client."""
        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None
        router.plan.return_value = ExecutionPlan(
            command_name="test",
            runtime_mode=RuntimeMode.LEGACY,
        )

        facade = ExecutionFacade(router=router, telemetry_client=None)

        context = MagicMock()
        context.command.name = "test"
        context.session_id = "no-tel"

        async def executor(ctx):
            return {"done": True}

        result = await facade.execute(context, legacy_executor=executor)
        assert result["done"] is True


class TestExecutionFacadeShouldHandleMatrix:
    """Matrix tests for should_handle() combinations."""

    @pytest.mark.parametrize(
        "flag_on,allowlist,command,expected",
        [
            # Flag off - always False
            (False, None, "analyze", False),
            (False, ["analyze"], "analyze", False),
            (False, ["build"], "analyze", False),
            # Flag on, default allowlist
            (True, None, "analyze", True),  # analyze in default
            (True, None, "implement", False),  # implement not in default
            # Flag on, explicit allowlist
            (True, ["build"], "build", True),
            (True, ["build"], "analyze", False),
            (True, ["build", "test"], "test", True),
            # Flag on, empty allowlist
            (True, [], "analyze", False),
            (True, [], "build", False),
        ],
    )
    def test_should_handle_matrix(
        self, env_isolation, router, flag_on, allowlist, command, expected
    ):
        """Test should_handle() across all combinations."""
        env_isolation.set_decomposed(flag_on)
        env_isolation.set_allowlist(allowlist)

        facade = ExecutionFacade(router=router)
        result = facade.should_handle(command)
        assert result is expected, (
            f"flag_on={flag_on}, allowlist={allowlist}, "
            f"command={command}: expected {expected}, got {result}"
        )
