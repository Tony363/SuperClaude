"""
Claude Agent SDK integration for SuperClaude.

This module provides integration between SuperClaude's agent orchestration
framework and the Claude Agent SDK, enabling:

- Conversion of SuperClaude agents to SDK AgentDefinition format
- Quality hooks for evidence collection and scoring
- Session management across command executions
- MCP server configuration for PAL and Rube integrations

Usage:
    from SuperClaude.SDK import SuperClaudeSDKClient, AgentToSDKAdapter
    from SuperClaude.SDK.hooks import QualityHooks, EvidenceHooks

Example:
    # Create SDK client with SuperClaude context
    client = SuperClaudeSDKClient(
        registry=agent_registry,
        selector=agent_selector,
        quality_scorer=quality_scorer
    )

    # Execute with automatic agent selection
    async for message in client.execute_with_agent(
        task="Fix the bug in auth.py",
        context={"cwd": "/project"}
    ):
        print(message)
"""

from __future__ import annotations

__version__ = "0.1.0"

# Explicit imports for CodeQL compatibility
# These modules have no external dependencies that would fail
from .adapter import AgentToSDKAdapter
from .agentic_loop import create_sdk_loop_context, run_sdk_loop
from .client import SDKMessage, SDKOptions, SuperClaudeSDKClient
from .executor import SDKExecutionResult, SDKExecutor, SDKExecutorConfig
from .hooks import EvidenceHooks, QualityHooks
from .types import TerminationReason

__all__ = [
    # Client
    "SuperClaudeSDKClient",
    # Adapter
    "AgentToSDKAdapter",
    # Executor
    "SDKExecutor",
    "SDKExecutorConfig",
    "SDKExecutionResult",
    # Agentic Loop
    "run_sdk_loop",
    "create_sdk_loop_context",
    # Hooks
    "QualityHooks",
    "EvidenceHooks",
    # Types (re-exported for convenience)
    "SDKMessage",
    "SDKOptions",
    "TerminationReason",
]


def is_sdk_available() -> bool:
    """Check if the Claude Agent SDK is installed and available."""
    try:
        import claude_agent_sdk  # noqa: F401

        return True
    except ImportError:
        return False


def get_sdk_version() -> str | None:
    """Get the installed Claude Agent SDK version, if available."""
    try:
        import claude_agent_sdk

        return getattr(claude_agent_sdk, "__version__", "unknown")
    except ImportError:
        return None
