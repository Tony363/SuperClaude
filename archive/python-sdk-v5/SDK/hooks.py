"""
Hooks for Claude Agent SDK integration with SuperClaude quality system.

This module provides hook implementations that intercept SDK execution
at key points to collect evidence, enforce quality gates, and integrate
with SuperClaude's scoring and validation systems.

Key Hook Classes:
    - QualityHooks: Collect evidence and feed into QualityScorer
    - EvidenceHooks: Enforce requires_evidence gate
    - FileChangeHooks: Track file modifications for evidence

Example:
    from SuperClaude.SDK.hooks import QualityHooks, EvidenceHooks

    hooks = QualityHooks(scorer=quality_scorer)
    hooks.extend(EvidenceHooks(requires_evidence=True))

    # Pass to SDK client
    async for msg in query(prompt, options=ClaudeAgentOptions(hooks=hooks)):
        print(msg)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..Quality.quality_scorer import DeterministicSignals, QualityScorer

logger = logging.getLogger(__name__)


class HookType(Enum):
    """SDK hook event types."""

    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"


@dataclass
class ToolInvocation:
    """Record of a tool invocation."""

    tool_name: str
    timestamp: datetime
    input_params: dict[str, Any]
    output: Any = None
    success: bool = True
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class FileChange:
    """Record of a file change."""

    path: str
    action: str  # read, write, edit, create, delete
    timestamp: datetime
    content_hash: str | None = None
    lines_changed: int = 0


@dataclass
class ExecutionEvidence:
    """
    Collected execution evidence for quality scoring.

    This dataclass aggregates all evidence collected during SDK execution
    to be fed into the QualityScorer for deterministic grounding.
    """

    # Tool invocations
    tool_invocations: list[ToolInvocation] = field(default_factory=list)

    # File changes
    files_read: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    files_edited: list[str] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)

    # Command execution
    commands_run: list[str] = field(default_factory=list)
    command_results: list[dict[str, Any]] = field(default_factory=list)

    # Test results
    tests_run: bool = False
    test_passed: int = 0
    test_failed: int = 0
    test_coverage: float = 0.0

    # Subagent tracking
    subagents_spawned: int = 0
    subagent_names: list[str] = field(default_factory=list)

    # Session info
    session_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    def has_file_modifications(self) -> bool:
        """Check if any files were modified."""
        return bool(self.files_written or self.files_edited)

    def has_execution_evidence(self) -> bool:
        """Check if there's evidence of actual execution (not just planning)."""
        return (
            self.has_file_modifications() or bool(self.commands_run) or self.tests_run
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "tool_count": len(self.tool_invocations),
            "files_read": len(self.files_read),
            "files_written": len(self.files_written),
            "files_edited": len(self.files_edited),
            "commands_run": len(self.commands_run),
            "tests_run": self.tests_run,
            "test_passed": self.test_passed,
            "test_failed": self.test_failed,
            "test_coverage": self.test_coverage,
            "subagents_spawned": self.subagents_spawned,
            "has_file_modifications": self.has_file_modifications(),
            "has_execution_evidence": self.has_execution_evidence(),
            "session_id": self.session_id,
        }


class BaseHook:
    """Base class for SDK hooks."""

    def pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Called before a tool is invoked.

        Args:
            tool_name: Name of the tool being invoked.
            tool_input: Input parameters for the tool.

        Returns:
            None to proceed, or dict with 'block' key to prevent execution.
        """
        return None

    def post_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
    ) -> None:
        """
        Called after a tool is invoked.

        Args:
            tool_name: Name of the tool that was invoked.
            tool_input: Input parameters that were used.
            tool_output: Output from the tool.
        """
        pass

    def session_start(self, session_id: str) -> None:
        """Called when a session starts."""
        pass

    def session_end(self, session_id: str) -> None:
        """Called when a session ends."""
        pass

    def subagent_start(self, agent_name: str, prompt: str) -> None:
        """Called when a subagent is spawned."""
        pass

    def subagent_stop(self, agent_name: str, result: Any) -> None:
        """Called when a subagent completes."""
        pass


class QualityHooks(BaseHook):
    """
    Hooks for collecting quality-relevant evidence during SDK execution.

    Tracks tool invocations, file changes, command results, and test
    outcomes to feed into the QualityScorer for deterministic grounding.
    """

    def __init__(
        self,
        scorer: QualityScorer | None = None,
    ):
        """
        Initialize quality hooks.

        Args:
            scorer: Optional QualityScorer instance for evaluation.
        """
        self.scorer = scorer
        self.evidence = ExecutionEvidence()
        self._current_invocation: ToolInvocation | None = None

    def reset(self) -> None:
        """Reset collected evidence."""
        self.evidence = ExecutionEvidence()
        self._current_invocation = None

    def get_evidence(self) -> ExecutionEvidence:
        """Get collected evidence."""
        return self.evidence

    def pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Track tool invocation start."""
        self._current_invocation = ToolInvocation(
            tool_name=tool_name,
            timestamp=datetime.now(),
            input_params=tool_input,
        )
        return None  # Allow all tools

    def post_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
    ) -> None:
        """
        Collect evidence from tool execution.

        Tracks file operations, command execution, and test results
        for quality scoring.
        """
        # Complete invocation record
        if self._current_invocation:
            self._current_invocation.output = tool_output
            self._current_invocation.duration_ms = (
                datetime.now() - self._current_invocation.timestamp
            ).total_seconds() * 1000
            self.evidence.tool_invocations.append(self._current_invocation)
            self._current_invocation = None

        # Track file operations
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            if file_path:
                self.evidence.files_read.append(file_path)
                self.evidence.file_changes.append(
                    FileChange(
                        path=file_path,
                        action="read",
                        timestamp=datetime.now(),
                    )
                )

        elif tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            if file_path:
                self.evidence.files_written.append(file_path)
                self.evidence.file_changes.append(
                    FileChange(
                        path=file_path,
                        action="write",
                        timestamp=datetime.now(),
                    )
                )
                logger.debug(f"Evidence: File written - {file_path}")

        elif tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            if file_path:
                self.evidence.files_edited.append(file_path)
                self.evidence.file_changes.append(
                    FileChange(
                        path=file_path,
                        action="edit",
                        timestamp=datetime.now(),
                    )
                )
                logger.debug(f"Evidence: File edited - {file_path}")

        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            if command:
                self.evidence.commands_run.append(command)

                # Track command result
                result_info = {
                    "command": command,
                    "timestamp": datetime.now().isoformat(),
                }
                if isinstance(tool_output, dict):
                    result_info["exit_code"] = tool_output.get("exit_code")
                    result_info["success"] = tool_output.get("exit_code", 0) == 0
                self.evidence.command_results.append(result_info)

                # Check for test execution
                if self._is_test_command(command):
                    self._parse_test_results(command, tool_output)

        elif tool_name == "Task":
            # Track subagent spawn
            self.evidence.subagents_spawned += 1
            agent_desc = tool_input.get("description", "unnamed")
            self.evidence.subagent_names.append(agent_desc)

    def session_start(self, session_id: str) -> None:
        """Record session start."""
        self.evidence.session_id = session_id
        self.evidence.start_time = datetime.now()
        logger.debug(f"Quality hooks: Session started - {session_id}")

    def session_end(self, session_id: str) -> None:
        """Record session end and optionally trigger scoring."""
        self.evidence.end_time = datetime.now()
        logger.debug(f"Quality hooks: Session ended - {session_id}")
        logger.info(f"Execution evidence: {self.evidence.to_dict()}")

    def subagent_start(self, agent_name: str, prompt: str) -> None:
        """Track subagent spawn."""
        logger.debug(f"Subagent started: {agent_name}")

    def subagent_stop(self, agent_name: str, result: Any) -> None:
        """Track subagent completion."""
        logger.debug(f"Subagent completed: {agent_name}")

    def to_deterministic_signals(self) -> DeterministicSignals:
        """
        Convert collected evidence to DeterministicSignals for quality scoring.

        Returns:
            DeterministicSignals instance for use with QualityScorer.
        """
        # Import here to avoid circular dependencies
        from ..Quality.quality_scorer import DeterministicSignals

        return DeterministicSignals(
            tests_passed=self.evidence.test_failed == 0 and self.evidence.tests_run,
            tests_total=self.evidence.test_passed + self.evidence.test_failed,
            tests_failed=self.evidence.test_failed,
            test_coverage=self.evidence.test_coverage,
        )

    def _is_test_command(self, command: str) -> bool:
        """Check if command is a test execution."""
        test_patterns = [
            "pytest",
            "python -m pytest",
            "npm test",
            "npm run test",
            "jest",
            "mocha",
            "cargo test",
            "go test",
        ]
        return any(pattern in command.lower() for pattern in test_patterns)

    def _parse_test_results(self, command: str, output: Any) -> None:
        """Parse test results from command output."""
        self.evidence.tests_run = True

        if isinstance(output, dict):
            # Try to extract test counts from structured output
            stdout = output.get("stdout", "")
            if isinstance(stdout, str):
                # Parse pytest-style output
                import re

                # Match patterns like "5 passed", "2 failed"
                passed_match = re.search(r"(\d+)\s+passed", stdout)
                failed_match = re.search(r"(\d+)\s+failed", stdout)
                coverage_match = re.search(r"(\d+)%", stdout)

                if passed_match:
                    self.evidence.test_passed = int(passed_match.group(1))
                if failed_match:
                    self.evidence.test_failed = int(failed_match.group(1))
                if coverage_match:
                    self.evidence.test_coverage = float(coverage_match.group(1))


class EvidenceHooks(BaseHook):
    """
    Hooks for enforcing evidence requirements.

    When requires_evidence is True, these hooks track whether actual
    work was performed and can block session completion without
    proof of changes.
    """

    def __init__(
        self,
        requires_evidence: bool = True,
        min_file_changes: int = 0,
        require_tests: bool = False,
    ):
        """
        Initialize evidence hooks.

        Args:
            requires_evidence: Whether to require execution evidence.
            min_file_changes: Minimum number of file changes required.
            require_tests: Whether test execution is required.
        """
        self.requires_evidence = requires_evidence
        self.min_file_changes = min_file_changes
        self.require_tests = require_tests
        self._quality_hooks: QualityHooks | None = None

    def attach_quality_hooks(self, quality_hooks: QualityHooks) -> None:
        """Attach quality hooks to share evidence collection."""
        self._quality_hooks = quality_hooks

    def get_evidence(self) -> ExecutionEvidence | None:
        """Get evidence from attached quality hooks."""
        if self._quality_hooks:
            return self._quality_hooks.get_evidence()
        return None

    def validate_evidence(self) -> tuple[bool, list[str]]:
        """
        Validate that evidence requirements are met.

        Returns:
            Tuple of (is_valid, list_of_issues).
        """
        if not self.requires_evidence:
            return True, []

        evidence = self.get_evidence()
        if not evidence:
            return False, ["No evidence collector attached"]

        issues = []

        # Check for execution evidence
        if not evidence.has_execution_evidence():
            issues.append(
                "No execution evidence found (no file changes, commands, or tests)"
            )

        # Check minimum file changes
        if self.min_file_changes > 0:
            total_changes = len(evidence.files_written) + len(evidence.files_edited)
            if total_changes < self.min_file_changes:
                issues.append(
                    f"Insufficient file changes: {total_changes} < {self.min_file_changes}"
                )

        # Check test requirement
        if self.require_tests and not evidence.tests_run:
            issues.append("Tests were not executed")

        is_valid = len(issues) == 0
        return is_valid, issues

    def session_end(self, session_id: str) -> None:
        """Validate evidence at session end."""
        is_valid, issues = self.validate_evidence()

        if not is_valid:
            logger.warning(f"Evidence validation failed for session {session_id}:")
            for issue in issues:
                logger.warning(f"  - {issue}")


class FileChangeHooks(BaseHook):
    """
    Hooks specifically for tracking file changes.

    Provides detailed tracking of file modifications including
    content hashes and line counts for change detection.
    """

    def __init__(self, base_path: Path | None = None):
        """
        Initialize file change hooks.

        Args:
            base_path: Base path for resolving relative file paths.
        """
        self.base_path = base_path or Path.cwd()
        self.changes: list[FileChange] = []
        self._file_hashes: dict[str, str] = {}

    def reset(self) -> None:
        """Reset tracked changes."""
        self.changes = []
        self._file_hashes = {}

    def get_changes(self) -> list[FileChange]:
        """Get list of file changes."""
        return self.changes

    def get_modified_files(self) -> list[str]:
        """Get list of modified file paths."""
        return [
            change.path
            for change in self.changes
            if change.action in ("write", "edit", "create")
        ]

    def pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Capture file state before modification."""
        if tool_name in ("Write", "Edit"):
            file_path = tool_input.get("file_path", "")
            if file_path:
                self._capture_file_hash(file_path)
        return None

    def post_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
    ) -> None:
        """Track file changes after tool execution."""
        file_path = tool_input.get("file_path", "")
        if not file_path:
            return

        if tool_name == "Read":
            self.changes.append(
                FileChange(
                    path=file_path,
                    action="read",
                    timestamp=datetime.now(),
                )
            )

        elif tool_name == "Write":
            # Determine if create or overwrite
            existed = file_path in self._file_hashes
            action = "write" if existed else "create"

            content = tool_input.get("content", "")
            lines = content.count("\n") + 1 if content else 0

            self.changes.append(
                FileChange(
                    path=file_path,
                    action=action,
                    timestamp=datetime.now(),
                    lines_changed=lines,
                )
            )

        elif tool_name == "Edit":
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")

            # Estimate lines changed
            old_lines = old_string.count("\n")
            new_lines = new_string.count("\n")
            lines_changed = abs(new_lines - old_lines) + 1

            self.changes.append(
                FileChange(
                    path=file_path,
                    action="edit",
                    timestamp=datetime.now(),
                    lines_changed=lines_changed,
                )
            )

    def _capture_file_hash(self, file_path: str) -> None:
        """Capture hash of file contents for change detection."""
        import hashlib

        try:
            path = Path(file_path)
            if not path.is_absolute():
                path = self.base_path / path

            if path.exists():
                content = path.read_bytes()
                self._file_hashes[file_path] = hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.debug(f"Could not hash file {file_path}: {e}")


class CompositeHooks(BaseHook):
    """
    Composite hook that delegates to multiple hook implementations.

    Allows combining QualityHooks, EvidenceHooks, and FileChangeHooks
    into a single hook instance for the SDK.
    """

    def __init__(self, hooks: list[BaseHook] | None = None):
        """
        Initialize composite hooks.

        Args:
            hooks: List of hook implementations to delegate to.
        """
        self.hooks = hooks or []

    def add(self, hook: BaseHook) -> CompositeHooks:
        """Add a hook to the composite."""
        self.hooks.append(hook)
        return self

    def extend(self, hooks: list[BaseHook]) -> CompositeHooks:
        """Add multiple hooks to the composite."""
        self.hooks.extend(hooks)
        return self

    def pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Delegate to all hooks; first block wins."""
        for hook in self.hooks:
            result = hook.pre_tool_use(tool_name, tool_input)
            if result and result.get("block"):
                return result
        return None

    def post_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
    ) -> None:
        """Delegate to all hooks."""
        for hook in self.hooks:
            hook.post_tool_use(tool_name, tool_input, tool_output)

    def session_start(self, session_id: str) -> None:
        """Delegate to all hooks."""
        for hook in self.hooks:
            hook.session_start(session_id)

    def session_end(self, session_id: str) -> None:
        """Delegate to all hooks."""
        for hook in self.hooks:
            hook.session_end(session_id)

    def subagent_start(self, agent_name: str, prompt: str) -> None:
        """Delegate to all hooks."""
        for hook in self.hooks:
            hook.subagent_start(agent_name, prompt)

    def subagent_stop(self, agent_name: str, result: Any) -> None:
        """Delegate to all hooks."""
        for hook in self.hooks:
            hook.subagent_stop(agent_name, result)


def create_quality_hooks(
    scorer: QualityScorer | None = None,
    requires_evidence: bool = True,
    require_tests: bool = False,
    track_file_changes: bool = True,
    base_path: Path | None = None,
) -> CompositeHooks:
    """
    Factory function to create a configured set of quality hooks.

    Args:
        scorer: Optional QualityScorer for evaluation.
        requires_evidence: Whether to require execution evidence.
        require_tests: Whether test execution is required.
        track_file_changes: Whether to track detailed file changes.
        base_path: Base path for file change tracking.

    Returns:
        Configured CompositeHooks instance.
    """
    quality_hooks = QualityHooks(scorer=scorer)
    evidence_hooks = EvidenceHooks(
        requires_evidence=requires_evidence,
        require_tests=require_tests,
    )
    evidence_hooks.attach_quality_hooks(quality_hooks)

    composite = CompositeHooks([quality_hooks, evidence_hooks])

    if track_file_changes:
        file_hooks = FileChangeHooks(base_path=base_path)
        composite.add(file_hooks)

    return composite
