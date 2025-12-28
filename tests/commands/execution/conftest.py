"""Shared fixtures for execution module tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

# Mark all tests in this directory as requiring archived SDK
pytestmark = pytest.mark.archived_sdk

# Guard imports that require archived SDK
_ARCHIVED_SDK_AVAILABLE = False
try:
    from SuperClaude.Commands.execution.context import CommandContext
    from SuperClaude.Commands.execution.routing import (
        CommandMetadataResolver,
        CommandRouter,
    )
    from SuperClaude.Commands.parser import ParsedCommand
    from SuperClaude.Commands.registry import CommandMetadata, CommandRegistry
    from SuperClaude.Modes.behavioral_manager import BehavioralMode

    _ARCHIVED_SDK_AVAILABLE = True
except ImportError:
    # Provide minimal stubs so module loads without error
    CommandContext = None  # type: ignore[misc, assignment]
    CommandMetadataResolver = None  # type: ignore[misc, assignment]
    CommandRouter = None  # type: ignore[misc, assignment]
    ParsedCommand = None  # type: ignore[misc, assignment]
    CommandMetadata = None  # type: ignore[misc, assignment]
    CommandRegistry = None  # type: ignore[misc, assignment]
    BehavioralMode = None  # type: ignore[misc, assignment]


@dataclass
class TelemetryCapture:
    """Captures telemetry events and metrics for testing."""

    events: list[dict[str, Any]] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)

    def record_event(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record an event."""
        self.events.append({"name": name, "payload": payload, "tags": tags})

    def record_metric(
        self,
        name: str,
        value: float | int,
        kind: Any,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Record a metric."""
        self.metrics.append({"name": name, "value": value, "kind": kind, "tags": tags})

    def increment(
        self,
        name: str,
        *,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter."""
        self.metrics.append({"name": name, "value": value, "kind": "increment", "tags": tags})

    def flush(self) -> None:
        """Flush (no-op for testing)."""
        pass

    def close(self) -> None:
        """Close (no-op for testing)."""
        pass

    def get_events_by_name(self, name: str) -> list[dict[str, Any]]:
        """Get all events with the given name."""
        return [e for e in self.events if e["name"] == name]

    def clear(self) -> None:
        """Clear all captured data."""
        self.events.clear()
        self.metrics.clear()


@pytest.fixture
def telemetry_capture():
    """Create a telemetry capture instance."""
    return TelemetryCapture()


@pytest.fixture
def env_isolation(monkeypatch):
    """Isolate environment variables for decomposed execution tests.

    Returns a context manager that can set/unset env vars.
    """

    class EnvManager:
        def __init__(self, monkeypatch):
            self._mp = monkeypatch

        def set_decomposed(self, enabled: bool = True):
            """Enable/disable decomposed execution."""
            if enabled:
                self._mp.setenv("SUPERCLAUDE_DECOMPOSED", "1")
            else:
                self._mp.delenv("SUPERCLAUDE_DECOMPOSED", raising=False)

        def set_allowlist(self, commands: list[str] | None):
            """Set the decomposed commands allowlist.

            Args:
                commands: List of command names, empty list for none,
                         None to use default
            """
            if commands is None:
                self._mp.delenv("SUPERCLAUDE_DECOMPOSED_COMMANDS", raising=False)
            elif len(commands) == 0:
                self._mp.setenv("SUPERCLAUDE_DECOMPOSED_COMMANDS", "")
            else:
                self._mp.setenv("SUPERCLAUDE_DECOMPOSED_COMMANDS", ",".join(commands))

        def clear(self):
            """Clear all decomposed-related env vars."""
            self._mp.delenv("SUPERCLAUDE_DECOMPOSED", raising=False)
            self._mp.delenv("SUPERCLAUDE_DECOMPOSED_COMMANDS", raising=False)

    # Start with clean state
    manager = EnvManager(monkeypatch)
    manager.clear()
    return manager


@pytest.fixture
def mock_registry():
    """Create a mock CommandRegistry."""
    if not _ARCHIVED_SDK_AVAILABLE:
        pytest.skip("Archived SDK not available")
    registry = MagicMock(spec=CommandRegistry)
    registry.list_commands.return_value = ["analyze", "implement", "build"]
    registry.get_command.return_value = None
    return registry


@pytest.fixture
def sample_command_metadata():
    """Create sample CommandMetadata for testing."""
    if not _ARCHIVED_SDK_AVAILABLE:
        pytest.skip("Archived SDK not available")
    return CommandMetadata(
        name="analyze",
        description="Analyze code",
        category="analysis",
        complexity="low",
        mcp_servers=[],
        personas=["analyst"],
        triggers=["analyze"],
        flags=[],
        parameters={},
        requires_evidence=False,
    )


@pytest.fixture
def evidence_command_metadata():
    """Create CommandMetadata that requires evidence."""
    if not _ARCHIVED_SDK_AVAILABLE:
        pytest.skip("Archived SDK not available")
    return CommandMetadata(
        name="implement",
        description="Implement code changes",
        category="development",
        complexity="high",
        mcp_servers=[],
        personas=["implementer"],
        triggers=["implement"],
        flags=[],
        parameters={},
        requires_evidence=True,
    )


@pytest.fixture
def mock_skills_runtime():
    """Create a mock SkillRuntime."""
    runtime = MagicMock()
    runtime.get_skill.return_value = None
    runtime.list_commands.return_value = []
    runtime.can_execute.return_value = False
    runtime.execute_command.return_value = {
        "success": True,
        "output": {"result": "skill executed"},
        "skill_id": "sc-test",
        "execution_mode": "script",
    }
    runtime.config = MagicMock()
    runtime.config.allow_instruction_only = False
    runtime.config.fallback_to_python = True
    return runtime


@pytest.fixture
def resolver(mock_registry, mock_skills_runtime):
    """Create a CommandMetadataResolver with mocks."""
    if not _ARCHIVED_SDK_AVAILABLE:
        pytest.skip("Archived SDK not available")
    return CommandMetadataResolver(
        registry=mock_registry,
        skills_runtime=mock_skills_runtime,
        skills_first=True,
    )


@pytest.fixture
def router(resolver, mock_skills_runtime):
    """Create a CommandRouter with mocks."""
    if not _ARCHIVED_SDK_AVAILABLE:
        pytest.skip("Archived SDK not available")
    return CommandRouter(
        resolver=resolver,
        skills_runtime=mock_skills_runtime,
    )


@pytest.fixture
def sample_parsed_command():
    """Create a sample ParsedCommand."""
    if not _ARCHIVED_SDK_AVAILABLE:
        pytest.skip("Archived SDK not available")
    return ParsedCommand(
        name="analyze",
        raw_string="/sc:analyze src/",
        arguments=["src/"],
        flags={},
        parameters={},
        description="Analyze source code",
    )


@pytest.fixture
def sample_command_context(sample_parsed_command, sample_command_metadata):
    """Create a sample CommandContext."""
    if not _ARCHIVED_SDK_AVAILABLE:
        pytest.skip("Archived SDK not available")
    return CommandContext(
        command=sample_parsed_command,
        metadata=sample_command_metadata,
        mcp_servers=[],
        agents=[],
        agent_instances={},
        agent_outputs={},
        results={},
        errors=[],
        session_id="test-session-001",
        behavior_mode=BehavioralMode.NORMAL.value,
    )
