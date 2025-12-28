"""
Command routing service for SuperClaude Commands.

Resolves command metadata from Skills or CommandRegistry.
Enables Skills-first execution with Python fallback.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ..registry import CommandMetadata, CommandRegistry

logger = logging.getLogger(__name__)


class RuntimeMode(Enum):
    """Execution runtime modes."""

    SKILLS = "skills"
    LEGACY = "legacy"


@dataclass
class ExecutionPlan:
    """
    Execution plan for a command.

    Captures the routing decision and resolved metadata.
    """

    command_name: str
    runtime_mode: RuntimeMode
    metadata: CommandMetadata | None = None
    skill_id: str | None = None

    @property
    def requires_worktree(self) -> bool:
        """Check if command requires worktree based on metadata.

        Note: Currently tied to requires_evidence. Will diverge when
        CommandMetadata supports distinct worktree/consensus flags.
        """
        if not self.metadata:
            return False
        return bool(self.metadata.requires_evidence)

    @property
    def requires_consensus(self) -> bool:
        """Check if command requires consensus based on metadata.

        Note: Currently tied to requires_evidence. Will diverge when
        CommandMetadata supports distinct worktree/consensus flags.
        """
        if not self.metadata:
            return False
        return bool(self.metadata.requires_evidence)


class CommandMetadataResolver:
    """
    Resolves command metadata from Skills or legacy CommandRegistry.

    Implements Skills-first resolution with Python fallback.
    """

    def __init__(
        self,
        registry: CommandRegistry,
        skills_runtime: Any | None = None,  # SkillRuntime when available
        skills_first: bool = True,
    ):
        """
        Initialize metadata resolver.

        Args:
            registry: Legacy CommandRegistry for Python commands
            skills_runtime: Optional SkillRuntime for Skills-first resolution
            skills_first: Whether to try skills before registry
        """
        self.registry = registry
        self.skills_runtime = skills_runtime
        self.skills_first = skills_first

    def resolve(self, command_name: str) -> CommandMetadata | None:
        """
        Resolve command metadata by name.

        If skills_first is True, tries Skills first, then falls back to registry.

        Args:
            command_name: Command name (without /sc: prefix)

        Returns:
            CommandMetadata or None if not found
        """
        # Strip /sc: prefix if present (use removeprefix for safety)
        command_name = command_name.removeprefix("/sc:").strip()

        if self.skills_first and self.skills_runtime:
            metadata = self._resolve_from_skills(command_name)
            if metadata:
                return metadata

        # Fall back to registry
        return self.registry.get_command(command_name)

    def _resolve_from_skills(self, command_name: str) -> CommandMetadata | None:
        """
        Resolve command metadata from Skills system.

        Args:
            command_name: Command name

        Returns:
            CommandMetadata or None
        """
        if not self.skills_runtime:
            return None

        try:
            # Try to get skill by sc-{command_name} pattern
            skill_id = f"sc-{command_name}"
            skill = self.skills_runtime.get_skill(skill_id)

            if skill:
                # Convert SkillMetadata to CommandMetadata via adapter
                return self.skills_runtime.adapter.to_command_metadata(skill)

        except Exception as e:
            logger.debug(f"Skills resolution failed for {command_name}: {e}")

        return None

    def list_commands(self) -> list[str]:
        """
        List all available commands from both sources.

        Returns:
            List of command names
        """
        commands = set(self.registry.list_commands())

        if self.skills_runtime:
            try:
                skill_commands = self.skills_runtime.list_commands()
                # Convert sc-{name} to {name}
                for skill_id in skill_commands:
                    if skill_id.startswith("sc-"):
                        commands.add(skill_id[3:])
            except Exception as e:
                logger.debug(f"Failed to list skill commands: {e}")

        return sorted(commands)

    def can_execute_via_skills(self, command_name: str) -> bool:
        """
        Check if a command can be executed via Skills runtime.

        Args:
            command_name: Command name

        Returns:
            True if executable via Skills
        """
        if not self.skills_runtime:
            return False

        try:
            skill_id = f"sc-{command_name}"
            skill = self.skills_runtime.get_skill(skill_id)
            if not skill:
                return False

            # Check if skill has execute script
            skill_dir = Path(skill.skill_dir) if hasattr(skill, "skill_dir") else None
            if skill_dir:
                execute_script = skill_dir / "scripts" / "execute.py"
                if execute_script.exists():
                    return True

            # Check if skills runtime allows instruction-only execution via fallback
            # Note: Uses fallback_to_python config field (allow_instruction_only doesn't exist)
            config = getattr(self.skills_runtime, "config", None)
            if config and getattr(config, "fallback_to_python", False):
                return True

        except Exception as e:
            logger.debug(f"Skills execution check failed for {command_name}: {e}")

        return False


class CommandRouter:
    """
    Routes commands to appropriate execution runtime.

    Decides between Skills runtime and Python handlers.
    """

    def __init__(
        self,
        resolver: CommandMetadataResolver,
        skills_runtime: Any | None = None,
    ):
        """
        Initialize command router.

        Args:
            resolver: Command metadata resolver
            skills_runtime: Optional SkillRuntime for execution
        """
        self.resolver = resolver
        self.skills_runtime = skills_runtime

    def should_use_skills(self, command_name: str) -> bool:
        """
        Determine if command should be executed via Skills runtime.

        Args:
            command_name: Command name

        Returns:
            True if should use Skills runtime
        """
        if not self.skills_runtime:
            return False

        return self.resolver.can_execute_via_skills(command_name)

    def get_runtime_mode(self, command_name: str) -> str:
        """
        Get the runtime mode for a command.

        Args:
            command_name: Command name

        Returns:
            'skills' or 'python'
        """
        if self.should_use_skills(command_name):
            return "skills"
        return "python"

    def plan(self, command_name: str) -> ExecutionPlan:
        """
        Create an execution plan for a command.

        Args:
            command_name: Command name

        Returns:
            ExecutionPlan with routing decision and metadata
        """
        # Resolve metadata
        metadata = self.resolver.resolve(command_name)

        # Determine runtime mode
        if self.should_use_skills(command_name):
            return ExecutionPlan(
                command_name=command_name,
                runtime_mode=RuntimeMode.SKILLS,
                metadata=metadata,
                skill_id=f"sc-{command_name}",
            )

        return ExecutionPlan(
            command_name=command_name,
            runtime_mode=RuntimeMode.LEGACY,
            metadata=metadata,
            skill_id=None,
        )
