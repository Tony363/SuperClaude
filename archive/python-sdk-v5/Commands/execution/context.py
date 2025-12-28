"""
Execution context dataclasses for SuperClaude Commands.

Contains CommandContext and CommandResult used throughout command execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...Modes.behavioral_manager import BehavioralMode
from ..parser import ParsedCommand
from ..registry import CommandMetadata


@dataclass
class CommandContext:
    """Execution context for a command."""

    command: ParsedCommand
    metadata: CommandMetadata
    mcp_servers: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    agent_instances: dict[str, Any] = field(default_factory=dict)
    agent_outputs: dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    session_id: str = ""
    behavior_mode: str = BehavioralMode.NORMAL.value
    consensus_summary: dict[str, Any] | None = None
    artifact_records: list[dict[str, Any]] = field(default_factory=list)
    think_level: int = 2
    loop_enabled: bool = False
    loop_iterations: int | None = None
    loop_min_improvement: float | None = None
    consensus_forced: bool = False
    delegated_agents: list[str] = field(default_factory=list)
    delegation_strategy: str | None = None
    active_personas: list[str] = field(default_factory=list)
    fast_codex_requested: bool = False
    fast_codex_active: bool = False
    fast_codex_blocked: list[str] = field(default_factory=list)


@dataclass
class CommandResult:
    """Result of command execution."""

    success: bool
    command_name: str
    output: Any
    errors: list[str] = field(default_factory=list)
    execution_time: float = 0.0
    mcp_servers_used: list[str] = field(default_factory=list)
    agents_used: list[str] = field(default_factory=list)
    executed_operations: list[str] = field(default_factory=list)
    applied_changes: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    consensus: dict[str, Any] | None = None
    behavior_mode: str = BehavioralMode.NORMAL.value
    status: str = "plan-only"
