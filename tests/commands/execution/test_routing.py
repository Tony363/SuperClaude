"""Tests for command routing and execution planning."""

from __future__ import annotations

from unittest.mock import MagicMock

from SuperClaude.Commands.execution.routing import (
    CommandMetadataResolver,
    CommandRouter,
    ExecutionPlan,
    RuntimeMode,
)


class TestRuntimeMode:
    """Tests for RuntimeMode enum."""

    def test_skills_value(self):
        assert RuntimeMode.SKILLS.value == "skills"

    def test_legacy_value(self):
        assert RuntimeMode.LEGACY.value == "legacy"

    def test_enum_members(self):
        members = list(RuntimeMode)
        assert len(members) == 2
        assert RuntimeMode.SKILLS in members
        assert RuntimeMode.LEGACY in members


class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass."""

    def test_basic_creation(self):
        plan = ExecutionPlan(
            command_name="test",
            runtime_mode=RuntimeMode.LEGACY,
        )
        assert plan.command_name == "test"
        assert plan.runtime_mode == RuntimeMode.LEGACY
        assert plan.metadata is None
        assert plan.skill_id is None

    def test_skills_plan(self):
        plan = ExecutionPlan(
            command_name="analyze",
            runtime_mode=RuntimeMode.SKILLS,
            skill_id="sc-analyze",
        )
        assert plan.runtime_mode == RuntimeMode.SKILLS
        assert plan.skill_id == "sc-analyze"

    def test_requires_worktree_no_metadata(self):
        plan = ExecutionPlan(
            command_name="test",
            runtime_mode=RuntimeMode.LEGACY,
        )
        assert plan.requires_worktree is False

    def test_requires_worktree_no_evidence(self, sample_command_metadata):
        plan = ExecutionPlan(
            command_name="analyze",
            runtime_mode=RuntimeMode.LEGACY,
            metadata=sample_command_metadata,
        )
        assert plan.requires_worktree is False

    def test_requires_worktree_with_evidence(self, evidence_command_metadata):
        plan = ExecutionPlan(
            command_name="implement",
            runtime_mode=RuntimeMode.LEGACY,
            metadata=evidence_command_metadata,
        )
        assert plan.requires_worktree is True

    def test_requires_consensus_no_metadata(self):
        plan = ExecutionPlan(
            command_name="test",
            runtime_mode=RuntimeMode.LEGACY,
        )
        assert plan.requires_consensus is False

    def test_requires_consensus_with_evidence(self, evidence_command_metadata):
        plan = ExecutionPlan(
            command_name="implement",
            runtime_mode=RuntimeMode.LEGACY,
            metadata=evidence_command_metadata,
        )
        assert plan.requires_consensus is True


class TestCommandMetadataResolver:
    """Tests for CommandMetadataResolver."""

    def test_resolve_from_registry(self, mock_registry, sample_command_metadata):
        """Fallback to registry when skills unavailable."""
        mock_registry.get_command.return_value = sample_command_metadata

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=None,
            skills_first=True,
        )

        result = resolver.resolve("analyze")
        assert result == sample_command_metadata
        mock_registry.get_command.assert_called_once_with("analyze")

    def test_resolve_strips_prefix(self, mock_registry):
        """Strip /sc: prefix from command name."""
        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=None,
        )

        resolver.resolve("/sc:analyze")
        mock_registry.get_command.assert_called_once_with("analyze")

    def test_resolve_from_skills_first(
        self, mock_registry, mock_skills_runtime, sample_command_metadata
    ):
        """Skills-first resolution when skill exists."""
        mock_skill = MagicMock()
        mock_skills_runtime.get_skill.return_value = mock_skill
        mock_skills_runtime.adapter = MagicMock()
        mock_skills_runtime.adapter.to_command_metadata.return_value = (
            sample_command_metadata
        )

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=mock_skills_runtime,
            skills_first=True,
        )

        result = resolver.resolve("analyze")
        assert result == sample_command_metadata
        mock_skills_runtime.get_skill.assert_called_once_with("sc-analyze")
        mock_registry.get_command.assert_not_called()

    def test_resolve_fallback_when_skill_not_found(
        self, mock_registry, mock_skills_runtime, sample_command_metadata
    ):
        """Fall back to registry when skill not found."""
        mock_skills_runtime.get_skill.return_value = None
        mock_registry.get_command.return_value = sample_command_metadata

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=mock_skills_runtime,
            skills_first=True,
        )

        result = resolver.resolve("analyze")
        assert result == sample_command_metadata
        mock_skills_runtime.get_skill.assert_called_once()
        mock_registry.get_command.assert_called_once()

    def test_resolve_skills_first_disabled(
        self, mock_registry, mock_skills_runtime, sample_command_metadata
    ):
        """Skip skills when skills_first is False."""
        mock_registry.get_command.return_value = sample_command_metadata

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=mock_skills_runtime,
            skills_first=False,
        )

        resolver.resolve("analyze")
        mock_skills_runtime.get_skill.assert_not_called()
        mock_registry.get_command.assert_called_once()

    def test_list_commands_combines_sources(self, mock_registry, mock_skills_runtime):
        """List commands from both registry and skills."""
        mock_registry.list_commands.return_value = ["analyze", "build"]
        mock_skills_runtime.list_commands.return_value = ["sc-implement", "sc-review"]

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=mock_skills_runtime,
        )

        commands = resolver.list_commands()
        assert "analyze" in commands
        assert "build" in commands
        assert "implement" in commands
        assert "review" in commands

    def test_can_execute_via_skills_no_runtime(self, mock_registry):
        """Return False when no skills runtime."""
        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=None,
        )

        assert resolver.can_execute_via_skills("analyze") is False

    def test_can_execute_via_skills_with_script(
        self, mock_registry, mock_skills_runtime, tmp_path
    ):
        """Return True when execute script exists."""
        skill = MagicMock()
        skill.skill_dir = str(tmp_path)
        mock_skills_runtime.get_skill.return_value = skill

        # Create execute script
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "execute.py").write_text("# execute script")

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=mock_skills_runtime,
        )

        assert resolver.can_execute_via_skills("analyze") is True

    def test_can_execute_via_skills_no_script_no_fallback(
        self, mock_registry, mock_skills_runtime, tmp_path
    ):
        """Return False when no execute script and fallback_to_python disabled."""
        skill = MagicMock()
        skill.skill_dir = str(tmp_path)
        mock_skills_runtime.get_skill.return_value = skill
        mock_skills_runtime.config.fallback_to_python = False

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=mock_skills_runtime,
        )

        assert resolver.can_execute_via_skills("analyze") is False

    def test_can_execute_via_skills_no_script_with_fallback(
        self, mock_registry, mock_skills_runtime, tmp_path
    ):
        """Return True when no execute script but fallback_to_python enabled."""
        skill = MagicMock()
        skill.skill_dir = str(tmp_path)
        mock_skills_runtime.get_skill.return_value = skill
        mock_skills_runtime.config.fallback_to_python = True

        resolver = CommandMetadataResolver(
            registry=mock_registry,
            skills_runtime=mock_skills_runtime,
        )

        assert resolver.can_execute_via_skills("analyze") is True


class TestCommandRouter:
    """Tests for CommandRouter."""

    def test_should_use_skills_no_runtime(self, resolver):
        """Return False when no skills runtime."""
        router = CommandRouter(
            resolver=resolver,
            skills_runtime=None,
        )
        assert router.should_use_skills("analyze") is False

    def test_should_use_skills_delegates_to_resolver(
        self, resolver, mock_skills_runtime
    ):
        """Delegate to resolver.can_execute_via_skills."""
        router = CommandRouter(
            resolver=resolver,
            skills_runtime=mock_skills_runtime,
        )

        # By default, mock returns False for can_execute_via_skills
        assert router.should_use_skills("analyze") is False

    def test_get_runtime_mode_skills(self, resolver, mock_skills_runtime, tmp_path):
        """Return 'skills' when skill is executable."""
        # Set up skill with execute script
        skill = MagicMock()
        skill.skill_dir = str(tmp_path)
        mock_skills_runtime.get_skill.return_value = skill
        resolver.skills_runtime = mock_skills_runtime

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "execute.py").write_text("# execute")

        router = CommandRouter(
            resolver=resolver,
            skills_runtime=mock_skills_runtime,
        )

        assert router.get_runtime_mode("analyze") == "skills"

    def test_get_runtime_mode_python(self, resolver, mock_skills_runtime):
        """Return 'python' when skill not executable."""
        mock_skills_runtime.get_skill.return_value = None

        router = CommandRouter(
            resolver=resolver,
            skills_runtime=mock_skills_runtime,
        )

        assert router.get_runtime_mode("analyze") == "python"

    def test_plan_legacy_mode(
        self, resolver, mock_skills_runtime, sample_command_metadata
    ):
        """Create LEGACY plan when skill not available."""
        mock_skills_runtime.get_skill.return_value = None
        resolver.registry.get_command.return_value = sample_command_metadata

        router = CommandRouter(
            resolver=resolver,
            skills_runtime=mock_skills_runtime,
        )

        plan = router.plan("analyze")
        assert plan.command_name == "analyze"
        assert plan.runtime_mode == RuntimeMode.LEGACY
        assert plan.metadata == sample_command_metadata
        assert plan.skill_id is None

    def test_plan_skills_mode(
        self, resolver, mock_skills_runtime, sample_command_metadata, tmp_path
    ):
        """Create SKILLS plan when skill is executable."""
        skill = MagicMock()
        skill.skill_dir = str(tmp_path)
        mock_skills_runtime.get_skill.return_value = skill
        mock_skills_runtime.adapter = MagicMock()
        mock_skills_runtime.adapter.to_command_metadata.return_value = (
            sample_command_metadata
        )
        resolver.skills_runtime = mock_skills_runtime

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "execute.py").write_text("# execute")

        router = CommandRouter(
            resolver=resolver,
            skills_runtime=mock_skills_runtime,
        )

        plan = router.plan("analyze")
        assert plan.command_name == "analyze"
        assert plan.runtime_mode == RuntimeMode.SKILLS
        assert plan.skill_id == "sc-analyze"
