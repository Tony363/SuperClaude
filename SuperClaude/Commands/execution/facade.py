"""
Execution facade for SuperClaude Commands.

Thin orchestration layer that composes services and routes
between Skills and legacy execution paths.
"""

import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from .context import CommandContext
from .routing import CommandRouter, ExecutionPlan, RuntimeMode

logger = logging.getLogger(__name__)

# Feature flag for decomposed execution
DECOMPOSED_ENV_VAR = "SUPERCLAUDE_DECOMPOSED"
DECOMPOSED_COMMANDS_ENV_VAR = "SUPERCLAUDE_DECOMPOSED_COMMANDS"

# Default allowlist - start with low-risk, read-only commands
DEFAULT_DECOMPOSED_COMMANDS = {"analyze"}


class ExecutionFacade:
    """
    Facade for command execution.

    Composes routing, consensus, artifacts, and telemetry
    into a single orchestration layer. Routes between Skills
    and legacy execution paths based on configuration.
    """

    def __init__(
        self,
        router: CommandRouter,
        telemetry_client: Any | None = None,
        allowlist: set[str] | None = None,
    ):
        """
        Initialize execution facade.

        Args:
            router: CommandRouter for routing decisions
            telemetry_client: Optional telemetry client for events
            allowlist: Optional set of commands to route through facade
        """
        self.router = router
        self.telemetry = telemetry_client
        self._allowlist = allowlist or self._load_allowlist()

    def _load_allowlist(self) -> set[str]:
        """
        Load decomposed commands allowlist from environment.

        Behavior:
        - Env var unset: use DEFAULT_DECOMPOSED_COMMANDS
        - Env var set to empty string "": no commands allowed (empty set)
        - Env var set to "cmd1,cmd2": parse as allowlist
        """
        env_value = os.environ.get(DECOMPOSED_COMMANDS_ENV_VAR)
        if env_value is None:
            # Unset - use default
            return DEFAULT_DECOMPOSED_COMMANDS.copy()
        if env_value == "":
            # Explicitly empty - no commands allowed
            return set()
        # Parse comma-separated list (handles whitespace)
        return {cmd.strip().lower() for cmd in env_value.split(",") if cmd.strip()}

    @staticmethod
    def is_enabled() -> bool:
        """Check if decomposed execution is enabled."""
        return os.environ.get(DECOMPOSED_ENV_VAR, "").lower() in ("1", "true", "yes")

    def is_command_allowed(self, command_name: str) -> bool:
        """Check if command is in the decomposed allowlist."""
        return command_name.lower() in self._allowlist

    def should_handle(self, command_name: str) -> bool:
        """
        Check if facade should handle this command.

        Args:
            command_name: Command name

        Returns:
            True if facade is enabled AND command is in allowlist
        """
        return self.is_enabled() and self.is_command_allowed(command_name)

    async def execute(
        self,
        context: CommandContext,
        legacy_executor: Callable[[CommandContext], Awaitable[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """
        Execute command via facade orchestration.

        Routes to Skills or legacy execution based on ExecutionPlan.
        Legacy execution requires a legacy_executor callable.

        Args:
            context: Command execution context
            legacy_executor: Callable for legacy execution path
                            (REQUIRED when plan is LEGACY)

        Returns:
            Command output dictionary

        Raises:
            RuntimeError: If legacy execution requested but no executor provided
        """
        command_name = context.command.name

        # Create execution plan
        plan = self.router.plan(command_name)

        # Record routing decision in telemetry
        self._record_routing_event(context, plan)

        # Route based on plan
        if plan.runtime_mode == RuntimeMode.SKILLS:
            return await self._execute_via_skills(context, plan)
        else:
            return await self._execute_via_legacy(context, plan, legacy_executor)

    async def _execute_via_skills(
        self,
        context: CommandContext,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:
        """
        Execute command via Skills runtime.

        Args:
            context: Command execution context
            plan: Execution plan

        Returns:
            Command output dictionary
        """
        if not self.router.skills_runtime:
            logger.warning(
                f"Skills runtime not available for {plan.command_name}, "
                "falling back to error response"
            )
            return {
                "status": "error",
                "error": "Skills runtime not available",
                "command": plan.command_name,
            }

        try:
            # Prepare arguments from context
            args = {
                "arguments": context.command.arguments,
                "parameters": context.command.parameters,
                "flags": context.command.flags,
            }

            # Execute via skills runtime
            result = self.router.skills_runtime.execute_command(
                plan.command_name,
                args,
                context,
            )

            # Record success
            self._record_execution_event(context, plan, success=True)

            # Normalize output (defensive copy to avoid mutating runtime's dict)
            raw_output = result.get("output", {})
            if isinstance(raw_output, dict):
                output = {
                    **raw_output,
                    "execution_mode": "skills",
                    "skill_id": plan.skill_id,
                }
            else:
                output = {
                    "status": "completed",
                    "execution_mode": "skills",
                    "skill_id": plan.skill_id,
                    "result": raw_output,
                }

            return output

        except Exception as exc:
            logger.error(f"Skills execution failed for {plan.command_name}: {exc}")
            self._record_execution_event(context, plan, success=False, error=str(exc))
            return {
                "status": "error",
                "error": str(exc),
                "command": plan.command_name,
                "execution_mode": "skills",
            }

    async def _execute_via_legacy(
        self,
        context: CommandContext,
        plan: ExecutionPlan,
        legacy_executor: Callable[[CommandContext], Awaitable[dict[str, Any]]] | None,
    ) -> dict[str, Any]:
        """
        Execute command via legacy handler.

        Args:
            context: Command execution context
            plan: Execution plan
            legacy_executor: Callable for legacy execution

        Returns:
            Command output dictionary

        Raises:
            RuntimeError: If no legacy_executor provided
        """
        if legacy_executor is None:
            raise RuntimeError(
                f"Legacy execution requested for '{plan.command_name}' "
                "but no legacy_executor provided"
            )

        try:
            # Execute via legacy path
            output = await legacy_executor(context)

            # Record success
            self._record_execution_event(context, plan, success=True)

            # Annotate output with execution mode
            if isinstance(output, dict):
                output.setdefault("execution_mode", "legacy")

            return output

        except Exception as exc:
            logger.error(f"Legacy execution failed for {plan.command_name}: {exc}")
            self._record_execution_event(context, plan, success=False, error=str(exc))
            raise

    def _record_routing_event(
        self,
        context: CommandContext,
        plan: ExecutionPlan,
    ) -> None:
        """Record routing decision in telemetry."""
        if not self.telemetry:
            return

        try:
            self.telemetry.record_event(
                "execution.routed",
                {
                    "command": plan.command_name,
                    "runtime_mode": plan.runtime_mode.value,
                    "skill_id": plan.skill_id,
                    "session_id": context.session_id,
                    "requires_worktree": plan.requires_worktree,
                    "requires_consensus": plan.requires_consensus,
                },
            )
        except Exception as exc:
            logger.debug(f"Failed to record routing event: {exc}")

    def _record_execution_event(
        self,
        context: CommandContext,
        plan: ExecutionPlan,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record execution result in telemetry."""
        if not self.telemetry:
            return

        try:
            payload = {
                "command": plan.command_name,
                "runtime_mode": plan.runtime_mode.value,
                "session_id": context.session_id,
                "success": success,
            }
            if error:
                payload["error"] = error

            self.telemetry.record_event("execution.completed", payload)
        except Exception as exc:
            logger.debug(f"Failed to record execution event: {exc}")
