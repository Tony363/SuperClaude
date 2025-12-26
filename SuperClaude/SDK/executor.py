"""
SDK Executor for SuperClaude command execution.

This module provides the SDKExecutor class which handles routing decisions
and execution via the Claude Agent SDK, with fallback support.

The executor owns:
- SDK availability and feature flag gating
- Command allowlist checking
- Agent selection and confidence thresholds
- Hooks creation and evidence extraction
- Stream aggregation to final output

The calling facade simply tries SDK then falls back - no duplicate routing logic.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .client import SDKMessage, SuperClaudeSDKClient
from .hooks import CompositeHooks, QualityHooks, create_quality_hooks
from .types import TerminationReason

if TYPE_CHECKING:
    from ..Agents.selector import AgentSelector, SDKSelectionResult
    from ..Commands.execution.context import CommandContext

logger = logging.getLogger(__name__)

# Environment variable names
SDK_ENABLED_ENV_VAR = "SUPERCLAUDE_SDK_ENABLED"
SDK_COMMANDS_ENV_VAR = "SUPERCLAUDE_SDK_COMMANDS"


@dataclass
class SDKExecutorConfig:
    """Configuration for SDK executor.

    Attributes:
        enabled: Master toggle for SDK execution.
        confidence_threshold: Minimum confidence for SDK routing.
        allowlist: Set of command names allowed to use SDK.
                   Empty set means NO commands allowed (rollout safety).
    """

    enabled: bool = False
    confidence_threshold: float = 0.5
    allowlist: set[str] = field(default_factory=set)

    @classmethod
    def from_env(cls) -> SDKExecutorConfig:
        """Load configuration from environment variables.

        - SUPERCLAUDE_SDK_ENABLED: "1", "true", "yes" to enable
        - SUPERCLAUDE_SDK_COMMANDS: comma-separated list of allowed commands
        """
        enabled = os.environ.get(SDK_ENABLED_ENV_VAR, "").lower() in (
            "1",
            "true",
            "yes",
        )
        commands_str = os.environ.get(SDK_COMMANDS_ENV_VAR, "")
        # Empty allowlist = no commands allowed (safer for rollout)
        allowlist = {
            cmd.strip().lower() for cmd in commands_str.split(",") if cmd.strip()
        }
        return cls(enabled=enabled, allowlist=allowlist)


@dataclass
class SDKExecutionResult:
    """Result of SDK execution attempt.

    Attributes:
        success: Whether SDK execution completed successfully.
        output: The command output dictionary.
        should_fallback: If True, caller should try SkillRuntime/legacy.
        routing_decision: Why SDK was used or not used.
        fallback_reason: Specific reason for fallback (if should_fallback=True).
        agent_used: Name of the agent that executed the task.
        confidence: Agent selection confidence score.
        evidence: Collected execution evidence from hooks.
        error_type: Exception class name if execution failed.
        termination_reason: Why the agentic loop terminated (if loop was run).
        iteration_count: Number of iterations in agentic loop (1 = no loop).
    """

    success: bool
    output: dict[str, Any]
    should_fallback: bool
    routing_decision: str
    fallback_reason: str | None = None
    agent_used: str | None = None
    confidence: float = 0.0
    evidence: dict[str, Any] | None = None
    error_type: str | None = None
    termination_reason: TerminationReason | None = None
    iteration_count: int = 1

    def to_record(self) -> dict[str, Any]:
        """
        Convert to SDK execution record for quality scoring.

        Returns a standardized record dict that can be passed to
        QualityScorer.evaluate_sdk_execution().

        Returns:
            Dict with keys: result, success, evidence, agent_used,
            confidence, errors, routing_decision, termination_reason,
            iteration_count.
        """
        record: dict[str, Any] = {
            "result": self.output,
            "success": self.success,
            "evidence": self.evidence or {},
            "agent_used": self.agent_used,
            "confidence": self.confidence,
            "routing_decision": self.routing_decision,
            "iteration_count": self.iteration_count,
        }

        # Add termination reason if present (convert enum to string value)
        if self.termination_reason is not None:
            record["termination_reason"] = self.termination_reason.value

        # Add error info if present
        if self.error_type or self.fallback_reason:
            record["errors"] = {
                "type": self.error_type,
                "reason": self.fallback_reason,
            }

        return record


class SDKExecutor:
    """
    Executor for Claude Agent SDK integration.

    Handles all SDK routing decisions internally:
    - Feature flag and availability checks
    - Command allowlist gating
    - Agent selection and confidence thresholds
    - Hooks creation and evidence extraction
    - Stream aggregation to final output

    The calling facade only needs to check `should_fallback` to decide
    whether to proceed with Skills/Legacy execution.
    """

    def __init__(
        self,
        client: SuperClaudeSDKClient | None = None,
        selector: AgentSelector | None = None,
        config: SDKExecutorConfig | None = None,
    ):
        """
        Initialize SDK executor.

        Args:
            client: SuperClaude SDK client. If None, created lazily.
            selector: Agent selector for routing decisions.
            config: Executor configuration. Defaults to env-based config.
        """
        self._client = client
        self._selector = selector
        self.config = config or SDKExecutorConfig.from_env()

    @property
    def client(self) -> SuperClaudeSDKClient:
        """Lazy-initialize client."""
        if self._client is None:
            self._client = SuperClaudeSDKClient()
        return self._client

    @property
    def selector(self) -> AgentSelector | None:
        """Get selector, or None if not configured."""
        return self._selector

    def is_sdk_available(self) -> bool:
        """Check if SDK is available for use."""
        return self.client._sdk_available

    async def execute(
        self,
        context: CommandContext,
        force_sdk: bool = False,
        disable_sdk: bool = False,
    ) -> SDKExecutionResult:
        """
        Execute command via SDK with all routing gates.

        This method contains ALL SDK routing logic. The facade should not
        duplicate any of these checks.

        Args:
            context: Command execution context.
            force_sdk: Override to force SDK execution (still requires availability).
            disable_sdk: Override to disable SDK execution.

        Returns:
            SDKExecutionResult with success/fallback status and output.
        """
        command_name = context.command.name.lower()
        task = self._build_task_from_context(context)

        # Gate 1: Explicit disable override (highest priority)
        if disable_sdk:
            return self._fallback_result(
                routing_decision="sdk_disabled_override",
                fallback_reason="SDK disabled by override",
            )

        # Gate 2: SDK availability
        if not self.is_sdk_available():
            return self._fallback_result(
                routing_decision="sdk_unavailable",
                fallback_reason="Claude Agent SDK not installed",
            )

        # Gate 3: Feature flag (unless force_sdk)
        if not force_sdk and not self.config.enabled:
            return self._fallback_result(
                routing_decision="sdk_not_enabled",
                fallback_reason="SDK execution not enabled",
            )

        # Gate 4: Command allowlist (unless force_sdk)
        if not force_sdk and not self._is_command_allowed(command_name):
            return self._fallback_result(
                routing_decision="command_not_allowed",
                fallback_reason=f"Command '{command_name}' not in SDK allowlist",
            )

        # Gate 5: Agent selection and confidence (unless force_sdk)
        selection = self._select_agent(task, context)
        if selection is None:
            return self._fallback_result(
                routing_decision="no_selector",
                fallback_reason="Agent selector not configured",
            )

        if not force_sdk:
            # Check both use_sdk flag AND confidence threshold
            if not selection.use_sdk:
                return self._fallback_result(
                    routing_decision="selection_declined",
                    fallback_reason=f"Agent selection declined SDK (confidence={selection.confidence:.2f})",
                    confidence=selection.confidence,
                )
            if selection.confidence < self.config.confidence_threshold:
                return self._fallback_result(
                    routing_decision="low_confidence",
                    fallback_reason=f"Confidence {selection.confidence:.2f} < threshold {self.config.confidence_threshold}",
                    confidence=selection.confidence,
                )

        # Gate 6: SDK definition must exist
        if selection.sdk_definition is None:
            return self._fallback_result(
                routing_decision="no_sdk_definition",
                fallback_reason=f"No SDK definition for agent '{selection.agent_name}'",
                agent_used=selection.agent_name,
                confidence=selection.confidence,
            )

        # All gates passed - execute via SDK
        return await self._execute_sdk(
            task=task,
            context=context,
            selection=selection,
        )

    def _is_command_allowed(self, command_name: str) -> bool:
        """Check if command is in SDK allowlist.

        Empty allowlist = no commands allowed (rollout safety).
        """
        if not self.config.allowlist:
            return False
        return command_name.lower() in self.config.allowlist

    def _build_task_from_context(self, context: CommandContext) -> str:
        """Build task string from command context."""
        parts = [context.command.name]

        if context.command.arguments:
            parts.extend(context.command.arguments)

        if context.command.parameters:
            for key, value in context.command.parameters.items():
                parts.append(f"{key}={value}")

        return " ".join(parts)

    def _select_agent(
        self, task: str, context: CommandContext
    ) -> SDKSelectionResult | None:
        """Select agent for task."""
        if self.selector is None:
            return None

        # Build selection context
        selection_context = {
            "task": task,
            "command": context.command.name,
        }
        if hasattr(context, "cwd"):
            selection_context["cwd"] = str(context.cwd)

        return self.selector.select_for_sdk(selection_context)

    async def _execute_sdk(
        self,
        task: str,
        context: CommandContext,
        selection: SDKSelectionResult,
    ) -> SDKExecutionResult:
        """Execute task via SDK client."""
        # Create hooks for evidence collection
        hooks = create_quality_hooks(
            requires_evidence=getattr(context, "requires_evidence", False),
            require_tests=getattr(context, "require_tests", False),
        )

        # Build execution context for SDK
        sdk_context: dict[str, Any] = {
            "command": context.command.name,
        }
        if hasattr(context, "cwd"):
            sdk_context["cwd"] = str(context.cwd)
        if hasattr(context, "requires_evidence"):
            sdk_context["requires_evidence"] = context.requires_evidence

        try:
            # Collect all messages from stream
            messages: list[SDKMessage] = []
            async for msg in self.client.execute_with_agent(
                task=task,
                context=sdk_context,
                agent_name=selection.agent_name,
                hooks=hooks,
            ):
                messages.append(msg)

            # Check for error messages
            error_msgs = [m for m in messages if m.type == "error"]
            if error_msgs:
                # SDK returned error - fallback
                error_content = error_msgs[0].content
                logger.warning(f"SDK execution returned error: {error_content}")
                return self._fallback_result(
                    routing_decision="sdk_error_message",
                    fallback_reason="SDK execution returned error",
                    agent_used=selection.agent_name,
                    confidence=selection.confidence,
                    error_type="SDKErrorMessage",
                )

            # Aggregate messages to output
            output = self._aggregate_messages(messages, selection.agent_name)

            # Extract evidence from hooks
            evidence = self._extract_evidence(hooks)

            return SDKExecutionResult(
                success=True,
                output=output,
                should_fallback=False,
                routing_decision="sdk_executed",
                agent_used=selection.agent_name,
                confidence=selection.confidence,
                evidence=evidence,
                termination_reason=TerminationReason.SINGLE_ITERATION,
                iteration_count=1,
            )

        except Exception as e:
            logger.exception(f"SDK execution failed: {e}")
            return self._fallback_result(
                routing_decision="sdk_exception",
                fallback_reason="SDK execution exception",
                agent_used=selection.agent_name,
                confidence=selection.confidence,
                error_type=type(e).__name__,
            )

    def _aggregate_messages(
        self, messages: list[SDKMessage], agent_name: str
    ) -> dict[str, Any]:
        """Aggregate SDK messages to output dictionary.

        Priority:
        1. Last "result" message
        2. Last "text" message
        3. Empty output with metadata
        """
        result_msgs = [m for m in messages if m.type == "result"]
        text_msgs = [m for m in messages if m.type == "text"]

        if result_msgs:
            content = result_msgs[-1].content
        elif text_msgs:
            content = text_msgs[-1].content
        else:
            content = ""

        # Build facade-compatible output
        return {
            "status": "completed",
            "execution_mode": "sdk",
            "agent": agent_name,
            "output": content if isinstance(content, str) else str(content),
            "message_count": len(messages),
        }

    def _extract_evidence(self, hooks: CompositeHooks) -> dict[str, Any]:
        """Extract evidence from hooks."""
        for hook in hooks.hooks:
            if isinstance(hook, QualityHooks):
                return hook.evidence.to_dict()
        return {}

    def _fallback_result(
        self,
        routing_decision: str,
        fallback_reason: str,
        agent_used: str | None = None,
        confidence: float = 0.0,
        error_type: str | None = None,
        termination_reason: TerminationReason | None = None,
    ) -> SDKExecutionResult:
        """Create a fallback result."""
        # Infer termination reason from routing decision if not provided
        if termination_reason is None:
            if routing_decision == "sdk_unavailable":
                termination_reason = TerminationReason.SDK_UNAVAILABLE
            elif routing_decision in ("sdk_exception", "sdk_error_message"):
                termination_reason = TerminationReason.EXECUTION_ERROR
            else:
                termination_reason = TerminationReason.FALLBACK

        return SDKExecutionResult(
            success=False,
            output={},
            should_fallback=True,
            routing_decision=routing_decision,
            fallback_reason=fallback_reason,
            agent_used=agent_used,
            confidence=confidence,
            error_type=error_type,
            termination_reason=termination_reason,
            iteration_count=1,
        )
