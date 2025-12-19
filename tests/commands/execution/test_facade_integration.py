"""Integration tests for ExecutionFacade with CommandExecutor.

Golden tests that verify end-to-end behavior through the real executor.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands.execution.facade import (
    DECOMPOSED_COMMANDS_ENV_VAR,
    DECOMPOSED_ENV_VAR,
)
from SuperClaude.Commands.execution.routing import RuntimeMode


class TestFacadeIntegrationWithExecutor:
    """Integration tests for facade wired into CommandExecutor."""

    @pytest.fixture
    def integration_workspace(self, tmp_path, monkeypatch):
        """Create isolated workspace for integration tests."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        monkeypatch.chdir(workspace)

        # Set offline mode
        monkeypatch.setenv("SUPERCLAUDE_OFFLINE_MODE", "1")
        monkeypatch.setenv("SC_NETWORK_MODE", "offline")

        # Create git repo
        subprocess.run(
            ["git", "init"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        # Initial commit
        readme = workspace / "README.md"
        readme.write_text("# Integration Test\n")
        subprocess.run(
            ["git", "add", "."], cwd=workspace, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=workspace,
            check=True,
            capture_output=True,
        )

        # Metrics dir
        metrics_dir = workspace / ".superclaude_metrics"
        monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(metrics_dir))

        return workspace

    @pytest.fixture
    def executor(self, integration_workspace):
        """Create CommandExecutor with real dependencies."""
        registry = CommandRegistry()
        parser = CommandParser()
        return CommandExecutor(registry, parser, repo_root=integration_workspace)

    def test_facade_initialized_when_available(self, executor):
        """Executor initializes facade when dependencies available."""
        # Facade should be initialized (may be None if skills unavailable)
        # But the initialization should not raise
        assert hasattr(executor, "execution_facade")

    def test_facade_disabled_routes_to_legacy(
        self, executor, integration_workspace, monkeypatch
    ):
        """Commands route to legacy path when facade disabled."""
        # Ensure disabled
        monkeypatch.delenv(DECOMPOSED_ENV_VAR, raising=False)

        if executor.execution_facade:
            assert executor.execution_facade.should_handle("analyze") is False

    def test_facade_enabled_routes_allowed_commands(
        self, executor, integration_workspace, monkeypatch
    ):
        """Commands route through facade when enabled and allowed."""
        # Enable with analyze in allowlist
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "1")
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, "analyze")

        # Need to reinitialize to pick up env changes
        registry = CommandRegistry()
        parser = CommandParser()
        new_executor = CommandExecutor(registry, parser, repo_root=integration_workspace)

        if new_executor.execution_facade:
            assert new_executor.execution_facade.should_handle("analyze") is True
            assert new_executor.execution_facade.should_handle("implement") is False

    def test_executor_facade_wiring(self, integration_workspace, monkeypatch):
        """Verify facade is wired into executor initialization."""
        monkeypatch.setenv(DECOMPOSED_ENV_VAR, "1")
        monkeypatch.setenv(DECOMPOSED_COMMANDS_ENV_VAR, "analyze")

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser, repo_root=integration_workspace)

        # Check facade exists and has router
        if executor.execution_facade:
            assert hasattr(executor.execution_facade, "router")
            assert hasattr(executor.execution_facade.router, "resolver")


class TestFacadeRoutingDecisions:
    """Test that routing decisions produce expected plans."""

    @pytest.fixture
    def router_with_skills(self, tmp_path, monkeypatch):
        """Create router with mock skill that has execute script."""
        from SuperClaude.Commands.execution.routing import (
            CommandMetadataResolver,
            CommandRouter,
        )
        from SuperClaude.Commands.registry import CommandRegistry

        # Create mock skill dir with execute script
        skill_dir = tmp_path / "skills" / "sc-analyze"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "execute.py").write_text(
            "def execute(args, context): return {'result': 'done'}"
        )

        # Mock skill
        mock_skill = MagicMock()
        mock_skill.skill_dir = str(skill_dir)

        # Mock runtime
        mock_runtime = MagicMock()
        mock_runtime.get_skill.return_value = mock_skill
        mock_runtime.config.allow_instruction_only = False

        # Registry
        registry = CommandRegistry()

        resolver = CommandMetadataResolver(
            registry=registry,
            skills_runtime=mock_runtime,
            skills_first=True,
        )

        return CommandRouter(resolver=resolver, skills_runtime=mock_runtime)

    def test_skill_backed_command_routes_to_skills(self, router_with_skills):
        """Command with execute script routes to SKILLS mode."""
        plan = router_with_skills.plan("analyze")
        assert plan.runtime_mode == RuntimeMode.SKILLS
        assert plan.skill_id == "sc-analyze"

    def test_non_skill_command_routes_to_legacy(self, router_with_skills):
        """Command without skill routes to LEGACY mode."""
        # Mock skill not found for this command
        router_with_skills.skills_runtime.get_skill.return_value = None

        plan = router_with_skills.plan("unknown")
        assert plan.runtime_mode == RuntimeMode.LEGACY
        assert plan.skill_id is None


class TestOutputModeAnnotation:
    """Test that execution mode is annotated in output."""

    @pytest.mark.asyncio
    async def test_legacy_output_annotated(self, telemetry_capture):
        """Legacy execution annotates output with mode."""
        from SuperClaude.Commands.execution.facade import ExecutionFacade
        from SuperClaude.Commands.execution.routing import (
            CommandRouter,
            ExecutionPlan,
            RuntimeMode,
        )

        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None
        router.plan.return_value = ExecutionPlan(
            command_name="test",
            runtime_mode=RuntimeMode.LEGACY,
        )

        facade = ExecutionFacade(router=router, telemetry_client=telemetry_capture)

        context = MagicMock()
        context.command.name = "test"
        context.session_id = "out-test"

        async def executor(ctx):
            return {"result": "done"}

        result = await facade.execute(context, legacy_executor=executor)

        assert result["execution_mode"] == "legacy"
        assert result["result"] == "done"

    @pytest.mark.asyncio
    async def test_skills_output_annotated(self, telemetry_capture):
        """Skills execution annotates output with mode and skill_id."""
        from SuperClaude.Commands.execution.facade import ExecutionFacade
        from SuperClaude.Commands.execution.routing import (
            CommandRouter,
            ExecutionPlan,
            RuntimeMode,
        )

        mock_runtime = MagicMock()
        mock_runtime.execute_command.return_value = {
            "success": True,
            "output": {"data": "from skill"},
        }

        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = mock_runtime
        router.plan.return_value = ExecutionPlan(
            command_name="analyze",
            runtime_mode=RuntimeMode.SKILLS,
            skill_id="sc-analyze",
        )

        facade = ExecutionFacade(router=router, telemetry_client=telemetry_capture)

        context = MagicMock()
        context.command.name = "analyze"
        context.command.arguments = []
        context.command.parameters = {}
        context.command.flags = {}
        context.session_id = "skill-out"

        result = await facade.execute(context)

        assert result["execution_mode"] == "skills"
        assert result["skill_id"] == "sc-analyze"


class TestLegacyGuardrails:
    """Test that legacy path has proper guardrails."""

    @pytest.mark.asyncio
    async def test_legacy_without_executor_raises_runtime_error(self):
        """RuntimeError raised when legacy path without executor."""
        from SuperClaude.Commands.execution.facade import ExecutionFacade
        from SuperClaude.Commands.execution.routing import (
            CommandRouter,
            ExecutionPlan,
            RuntimeMode,
        )

        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None
        router.plan.return_value = ExecutionPlan(
            command_name="build",
            runtime_mode=RuntimeMode.LEGACY,
        )

        facade = ExecutionFacade(router=router)

        context = MagicMock()
        context.command.name = "build"
        context.session_id = "guard-test"

        with pytest.raises(RuntimeError) as exc_info:
            await facade.execute(context, legacy_executor=None)

        assert "build" in str(exc_info.value)
        assert "legacy_executor" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_legacy_executor_exception_propagates(self):
        """Exceptions from legacy executor propagate up."""
        from SuperClaude.Commands.execution.facade import ExecutionFacade
        from SuperClaude.Commands.execution.routing import (
            CommandRouter,
            ExecutionPlan,
            RuntimeMode,
        )

        router = MagicMock(spec=CommandRouter)
        router.skills_runtime = None
        router.plan.return_value = ExecutionPlan(
            command_name="fail",
            runtime_mode=RuntimeMode.LEGACY,
        )

        facade = ExecutionFacade(router=router)

        context = MagicMock()
        context.command.name = "fail"
        context.session_id = "exc-test"

        async def failing_executor(ctx):
            raise ValueError("Legacy execution failed")

        with pytest.raises(ValueError, match="Legacy execution failed"):
            await facade.execute(context, legacy_executor=failing_executor)


class TestWorktreeAndConsensusDetermination:
    """Test worktree and consensus determination from metadata."""

    def test_no_worktree_for_readonly_command(self, sample_command_metadata):
        """Read-only commands don't require worktree."""
        from SuperClaude.Commands.execution.routing import ExecutionPlan, RuntimeMode

        plan = ExecutionPlan(
            command_name="analyze",
            runtime_mode=RuntimeMode.LEGACY,
            metadata=sample_command_metadata,
        )

        assert plan.requires_worktree is False
        assert plan.requires_consensus is False

    def test_worktree_for_evidence_command(self, evidence_command_metadata):
        """Commands requiring evidence need worktree."""
        from SuperClaude.Commands.execution.routing import ExecutionPlan, RuntimeMode

        plan = ExecutionPlan(
            command_name="implement",
            runtime_mode=RuntimeMode.LEGACY,
            metadata=evidence_command_metadata,
        )

        assert plan.requires_worktree is True
        assert plan.requires_consensus is True

    def test_no_worktree_without_metadata(self):
        """No metadata means no worktree requirement."""
        from SuperClaude.Commands.execution.routing import ExecutionPlan, RuntimeMode

        plan = ExecutionPlan(
            command_name="unknown",
            runtime_mode=RuntimeMode.LEGACY,
            metadata=None,
        )

        assert plan.requires_worktree is False
        assert plan.requires_consensus is False
