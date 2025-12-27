"""
SuperClaude-aware Claude Agent SDK client.

This module provides a client that wraps the Claude Agent SDK with SuperClaude's
agent orchestration, quality scoring, and evidence collection capabilities.

Key Features:
    - Automatic agent selection from 131 SuperClaude agents
    - Quality hooks for evidence collection and scoring
    - Integration with SuperClaude's multi-model routing
    - Session management with context preservation

Example:
    client = SuperClaudeSDKClient(
        registry=agent_registry,
        selector=agent_selector,
        quality_scorer=quality_scorer,
    )

    async for message in client.execute_with_agent(
        task="Fix the authentication bug in auth.py",
        context={"cwd": "/project", "requires_evidence": True},
    ):
        process_message(message)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .adapter import AgentToSDKAdapter, SDKAgentDefinition
from .hooks import CompositeHooks, QualityHooks, create_quality_hooks

if TYPE_CHECKING:
    from ..Agents.registry import AgentRegistry
    from ..Agents.selector import AgentSelector
    from ..Quality.quality_scorer import QualityScorer

logger = logging.getLogger(__name__)


@dataclass
class SDKMessage:
    """Message from SDK execution."""

    type: str  # text, tool_use, tool_result, result, error
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SDKOptions:
    """Options for SDK execution."""

    # Model selection
    model: str = "sonnet"

    # Tool permissions
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None

    # Execution settings
    max_turns: int = 50
    timeout_seconds: int = 300

    # Permission mode
    permission_mode: str = "default"  # default, acceptEdits, bypassPermissions, plan

    # Session management
    session_id: str | None = None
    resume: bool = False

    # MCP servers
    mcp_servers: dict[str, Any] | None = None


@dataclass
class ExecutionResult:
    """Result of SDK execution."""

    success: bool
    messages: list[SDKMessage]
    session_id: str | None
    cost: dict[str, Any] | None
    evidence: dict[str, Any] | None
    quality_score: float | None
    error: str | None = None


class SuperClaudeSDKClient:
    """
    Claude Agent SDK client with SuperClaude integration.

    Provides a high-level interface for executing tasks using the Claude Agent SDK
    with automatic agent selection, quality scoring, and evidence collection.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        selector: AgentSelector | None = None,
        quality_scorer: QualityScorer | None = None,
        default_options: SDKOptions | None = None,
    ):
        """
        Initialize the SuperClaude SDK client.

        Args:
            registry: Agent registry for accessing SuperClaude agents.
            selector: Agent selector for automatic agent selection.
            quality_scorer: Quality scorer for evaluation.
            default_options: Default SDK options.
        """
        self.registry = registry
        self.selector = selector
        self.quality_scorer = quality_scorer
        self.default_options = default_options or SDKOptions()
        self.adapter = AgentToSDKAdapter(registry) if registry else None

        # Track active sessions
        self._sessions: dict[str, dict[str, Any]] = {}

        # Check SDK availability
        self._sdk_available = self._check_sdk_available()

    def _check_sdk_available(self) -> bool:
        """Check if the Claude Agent SDK is installed."""
        try:
            import claude_agent_sdk  # noqa: F401

            return True
        except ImportError:
            logger.warning(
                "claude-agent-sdk not installed. "
                "Install with: pip install claude-agent-sdk"
            )
            return False

    async def execute(
        self,
        prompt: str,
        options: SDKOptions | None = None,
        hooks: CompositeHooks | None = None,
    ) -> AsyncIterator[SDKMessage]:
        """
        Execute a prompt using the Claude Agent SDK.

        Args:
            prompt: The task prompt to execute.
            options: SDK execution options.
            hooks: Custom hooks for execution.

        Yields:
            SDKMessage objects from the execution stream.

        Raises:
            ImportError: If claude-agent-sdk is not installed.
        """
        if not self._sdk_available:
            yield SDKMessage(
                type="error",
                content="claude-agent-sdk not installed",
                metadata={"recoverable": False},
            )
            return

        opts = options or self.default_options

        try:
            from claude_agent_sdk import ClaudeAgentOptions, query

            # Build SDK options
            sdk_options = ClaudeAgentOptions(
                model=opts.model,
                max_turns=opts.max_turns,
                allowed_tools=opts.allowed_tools,
                disallowed_tools=opts.disallowed_tools,
                permission_mode=opts.permission_mode,
            )

            # Add session management
            if opts.session_id and opts.resume:
                sdk_options.session_id = opts.session_id

            # Add MCP servers if configured
            if opts.mcp_servers:
                sdk_options.mcp_servers = opts.mcp_servers

            # Convert hooks to SDK format if provided
            sdk_hooks = None
            if hooks:
                sdk_hooks = self._convert_hooks(hooks)

            # Execute via SDK
            async for message in query(
                prompt=prompt,
                options=sdk_options,
                hooks=sdk_hooks,
            ):
                yield self._convert_message(message)

        except Exception as e:
            logger.error(f"SDK execution error: {e}")
            yield SDKMessage(
                type="error",
                content=str(e),
                metadata={"exception": type(e).__name__},
            )

    async def execute_with_agent(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        agent_name: str | None = None,
        max_agents: int = 1,
        options: SDKOptions | None = None,
        hooks: CompositeHooks | None = None,
    ) -> AsyncIterator[SDKMessage]:
        """
        Execute a task with automatic agent selection.

        Uses SuperClaude's agent selection to choose the best agent for the task,
        then executes using the Claude Agent SDK with the agent's configuration.

        Args:
            task: The task description.
            context: Additional execution context.
            agent_name: Specific agent to use (bypasses selection).
            max_agents: Maximum agents for multi-agent scenarios.
            options: SDK execution options.
            hooks: Optional external hooks. If provided, these are used instead
                   of creating internal quality hooks. The caller is responsible
                   for any pre/post configuration but session lifecycle
                   (session_start/session_end) is still managed here.

        Yields:
            SDKMessage objects from the execution stream.
        """
        context = context or {}
        opts = options or self.default_options

        # Use external hooks if provided, otherwise create internal ones
        if hooks is not None:
            quality_hooks = hooks
        else:
            quality_hooks = create_quality_hooks(
                scorer=self.quality_scorer,
                requires_evidence=context.get("requires_evidence", False),
                require_tests=context.get("require_tests", False),
                base_path=Path(context.get("cwd", ".")) if context.get("cwd") else None,
            )

        # Start hook session
        session_id = opts.session_id or self._generate_session_id()
        for hook in quality_hooks.hooks:
            hook.session_start(session_id)

        try:
            # Get agent definition
            agent_def = self._get_agent_definition(
                task=task,
                context=context,
                agent_name=agent_name,
                max_agents=max_agents,
            )

            if agent_def:
                # Build prompt with agent context
                enhanced_prompt = self._build_enhanced_prompt(task, agent_def, context)

                # Execute with agent's tool restrictions
                agent_opts = SDKOptions(
                    model=agent_def.model or opts.model,
                    allowed_tools=agent_def.tools or opts.allowed_tools,
                    max_turns=opts.max_turns,
                    permission_mode=opts.permission_mode,
                    session_id=session_id,
                    mcp_servers=opts.mcp_servers,
                )

                async for message in self.execute(
                    prompt=enhanced_prompt,
                    options=agent_opts,
                    hooks=quality_hooks,
                ):
                    yield message
            else:
                # Fallback to direct execution
                logger.info("No specific agent selected, using direct execution")
                async for message in self.execute(
                    prompt=task,
                    options=opts,
                    hooks=quality_hooks,
                ):
                    yield message

        finally:
            # End hook session
            for hook in quality_hooks.hooks:
                hook.session_end(session_id)

    async def execute_multi_agent(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        max_agents: int = 3,
        options: SDKOptions | None = None,
    ) -> AsyncIterator[SDKMessage]:
        """
        Execute a task with multiple agents as subagents.

        Uses the SDK's Task tool to spawn multiple specialized agents
        for complex tasks that benefit from different expertise.

        Args:
            task: The task description.
            context: Additional execution context.
            max_agents: Maximum number of agents to involve.
            options: SDK execution options.

        Yields:
            SDKMessage objects from the execution stream.
        """
        context = context or {}
        opts = options or self.default_options

        if not self.adapter:
            # Fallback to single execution
            async for msg in self.execute_with_agent(task, context, options=opts):
                yield msg
            return

        # Get multiple agent definitions
        agents_dict = self.adapter.build_agents(
            task=task,
            context=context,
            max_agents=max_agents,
        )

        if not agents_dict:
            # Fallback to single execution
            async for msg in self.execute_with_agent(task, context, options=opts):
                yield msg
            return

        # Build orchestrator prompt that will spawn subagents
        orchestrator_prompt = self._build_orchestrator_prompt(
            task=task,
            agents=agents_dict,
            context=context,
        )

        # Execute with Task tool available for subagent spawning
        exec_opts = SDKOptions(
            model=opts.model,
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task"],
            max_turns=opts.max_turns * max_agents,  # Allow more turns for multi-agent
            permission_mode=opts.permission_mode,
            mcp_servers=opts.mcp_servers,
        )

        async for message in self.execute(
            prompt=orchestrator_prompt,
            options=exec_opts,
        ):
            yield message

    def _get_agent_definition(
        self,
        task: str,
        context: dict[str, Any],
        agent_name: str | None = None,
        max_agents: int = 1,
    ) -> SDKAgentDefinition | None:
        """Get agent definition for the task."""
        if not self.adapter:
            return None

        # If specific agent requested
        if agent_name and self.registry:
            agent = self.registry.get_agent(agent_name)
            if agent:
                return self.adapter.to_agent_definition(agent)
            logger.warning(f"Agent '{agent_name}' not found in registry")

        # Use selector if available
        if self.selector and max_agents == 1:
            try:
                scores = self.selector.select_agent({"task": task, **context})
                if scores:
                    top_agent_name, _ = scores[0]
                    agent = (
                        self.registry.get_agent(top_agent_name)
                        if self.registry
                        else None
                    )
                    if agent:
                        return self.adapter.to_agent_definition(agent)
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}")

        return None

    def _build_enhanced_prompt(
        self,
        task: str,
        agent_def: SDKAgentDefinition,
        context: dict[str, Any],
    ) -> str:
        """Build enhanced prompt incorporating agent context."""
        parts = []

        # Add agent prompt/persona
        if agent_def.prompt:
            parts.append(agent_def.prompt)
            parts.append("")

        # Add task
        parts.append("## Task")
        parts.append(task)
        parts.append("")

        # Add relevant context
        if context.get("cwd"):
            parts.append(f"Working directory: {context['cwd']}")

        if context.get("files"):
            parts.append(f"Relevant files: {', '.join(context['files'])}")

        if context.get("requirements"):
            parts.append("## Requirements")
            for req in context["requirements"]:
                parts.append(f"- {req}")

        return "\n".join(parts)

    def _build_orchestrator_prompt(
        self,
        task: str,
        agents: dict[str, SDKAgentDefinition],
        context: dict[str, Any],
    ) -> str:
        """Build orchestrator prompt for multi-agent execution."""
        parts = [
            "You are an orchestrator managing multiple specialized agents.",
            "",
            "## Available Agents",
        ]

        for name, agent_def in agents.items():
            parts.append(f"- **{name}**: {agent_def.description}")

        parts.extend(
            [
                "",
                "## Task",
                task,
                "",
                "## Instructions",
                "1. Analyze the task and break it into subtasks",
                "2. Delegate subtasks to the most appropriate agent using the Task tool",
                "3. Coordinate results and synthesize the final output",
                "4. Ensure quality by reviewing agent outputs",
                "",
            ]
        )

        if context.get("cwd"):
            parts.append(f"Working directory: {context['cwd']}")

        return "\n".join(parts)

    def _convert_message(self, sdk_message: Any) -> SDKMessage:
        """Convert SDK message to SDKMessage."""
        # Handle different SDK message types
        msg_type = getattr(sdk_message, "type", "unknown")

        if hasattr(sdk_message, "content"):
            content = sdk_message.content
        elif hasattr(sdk_message, "text"):
            content = sdk_message.text
        else:
            content = str(sdk_message)

        metadata = {}
        if hasattr(sdk_message, "tool_name"):
            metadata["tool_name"] = sdk_message.tool_name
        if hasattr(sdk_message, "session_id"):
            metadata["session_id"] = sdk_message.session_id

        return SDKMessage(
            type=str(msg_type),
            content=content,
            metadata=metadata,
        )

    def _convert_hooks(self, hooks: CompositeHooks) -> Any:
        """Convert SuperClaude hooks to SDK hook format."""
        # The SDK expects specific hook structure
        # We create a wrapper that translates our hooks

        class SDKHookWrapper:
            def __init__(self, composite: CompositeHooks):
                self.composite = composite

            def pre_tool_use(self, tool_name: str, tool_input: dict) -> dict | None:
                return self.composite.pre_tool_use(tool_name, tool_input)

            def post_tool_use(
                self, tool_name: str, tool_input: dict, tool_output: Any
            ) -> None:
                self.composite.post_tool_use(tool_name, tool_input, tool_output)

            def session_start(self, session_id: str) -> None:
                self.composite.session_start(session_id)

            def session_end(self, session_id: str) -> None:
                self.composite.session_end(session_id)

        return SDKHookWrapper(hooks)

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        import uuid

        return f"sc-{uuid.uuid4().hex[:12]}"

    def get_session_evidence(self, session_id: str) -> dict[str, Any] | None:
        """Get collected evidence for a session."""
        session = self._sessions.get(session_id)
        if session and "hooks" in session:
            for hook in session["hooks"].hooks:
                if isinstance(hook, QualityHooks):
                    return hook.get_evidence().to_dict()
        return None


# Convenience function for simple usage
async def execute_task(
    task: str,
    context: dict[str, Any] | None = None,
    model: str = "sonnet",
    **kwargs: Any,
) -> AsyncIterator[SDKMessage]:
    """
    Simple function to execute a task via the SDK.

    Args:
        task: The task to execute.
        context: Optional execution context.
        model: Model to use (default: sonnet).
        **kwargs: Additional options passed to SDKOptions.

    Yields:
        SDKMessage objects from execution.
    """
    client = SuperClaudeSDKClient()
    options = SDKOptions(model=model, **kwargs)

    async for message in client.execute_with_agent(
        task=task,
        context=context or {},
        options=options,
    ):
        yield message
