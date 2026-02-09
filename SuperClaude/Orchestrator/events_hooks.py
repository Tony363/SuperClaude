"""
Events tracking hooks for SuperClaude orchestrator.

Writes real-time events to .superclaude_metrics/events.jsonl for consumption
by the Zed panel and other monitoring tools.

Event Format (compatible with Rust daemon):
    {"event_type": "iteration_start", "iteration": 0, "depth": 0, "node_id": "iter-0"}
    {"event_type": "tool_use", "tool": "Write", "summary": "Created src/main.rs", ...}
    {"event_type": "score_update", "new_score": 75, "dimensions": {...}}
    {"event_type": "iteration_complete", "iteration": 0, "score": 75, ...}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..Telemetry.interfaces import MetricType
from ..Telemetry.jsonl import JsonlTelemetryClient
from .evidence import EvidenceCollector


class EventsTracker:
    """
    Tracks and emits events for the Zed panel integration.

    This class manages the telemetry client and provides methods
    for recording various event types in the format expected by
    the superclaude-daemon.
    """

    def __init__(
        self,
        session_id: str | None = None,
        metrics_dir: str | Path | None = None,
    ):
        """
        Initialize the events tracker.

        Args:
            session_id: Unique session identifier (auto-generated if not provided)
            metrics_dir: Directory for events.jsonl (default: .superclaude_metrics/)
        """
        self.client = JsonlTelemetryClient(
            metrics_dir=metrics_dir,
            session_id=session_id,
            buffer_size=1,  # Flush immediately for real-time updates
            auto_flush=True,
        )
        self.current_iteration = 0
        self.current_depth = 0
        self._node_counter = 0

    def _next_node_id(self, prefix: str = "node") -> str:
        """Generate a unique node ID."""
        self._node_counter += 1
        return f"{prefix}-{self._node_counter}"

    def record_iteration_start(self, iteration: int, depth: int = 0) -> str:
        """
        Record the start of an iteration.

        Args:
            iteration: 0-indexed iteration number
            depth: Nesting depth for visualization

        Returns:
            Node ID for this iteration
        """
        self.current_iteration = iteration
        self.current_depth = depth
        node_id = f"iter-{iteration}"

        self.client.record_event(
            "iteration_start",
            {
                "event_type": "iteration_start",
                "iteration": iteration,
                "depth": depth,
                "node_id": node_id,
            },
        )

        return node_id

    def record_iteration_complete(
        self,
        iteration: int,
        score: float,
        improvements: list[str] | None = None,
        dimensions: dict[str, float] | None = None,
        duration_seconds: float = 0.0,
    ) -> None:
        """
        Record the completion of an iteration.

        Args:
            iteration: 0-indexed iteration number
            score: Quality score (0-100)
            improvements: List of improvement suggestions
            dimensions: Quality dimension scores
            duration_seconds: Time taken for this iteration
        """
        node_id = f"iter-{iteration}"

        payload = {
            "event_type": "iteration_complete",
            "iteration": iteration,
            "score": score,
            "improvements": improvements or [],
            "duration_seconds": duration_seconds,
            "node_id": node_id,
        }

        if dimensions:
            payload["dimensions"] = dimensions

        self.client.record_event("iteration_complete", payload)

        # Also record as a metric for aggregation
        self.client.record_metric("quality.score", score, MetricType.GAUGE)

    def record_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any = None,
        blocked: bool = False,
        block_reason: str = "",
        parent_node_id: str | None = None,
    ) -> str:
        """
        Record a tool invocation.

        Args:
            tool_name: Name of the tool (Write, Edit, Bash, etc.)
            tool_input: Tool input parameters
            tool_output: Tool output/response
            blocked: Whether the tool was blocked by safety hooks
            block_reason: Reason for blocking
            parent_node_id: Parent node for tree visualization

        Returns:
            Node ID for this tool invocation
        """
        node_id = self._next_node_id("tool")

        # Generate a human-readable summary
        summary = self._summarize_tool(tool_name, tool_input, tool_output)

        self.client.record_event(
            "tool_use",
            {
                "event_type": "tool_use",
                "tool": tool_name,
                "summary": summary,
                "blocked": blocked,
                "block_reason": block_reason,
                "depth": self.current_depth + 1,
                "node_id": node_id,
                "parent_node_id": parent_node_id or f"iter-{self.current_iteration}",
            },
        )

        # Increment tool counter
        self.client.increment("tools.invoked")

        return node_id

    def record_file_change(
        self,
        path: str,
        action: str,
        lines_added: int = 0,
        lines_removed: int = 0,
    ) -> str:
        """
        Record a file change.

        Args:
            path: File path
            action: Action type (write, edit, read, delete)
            lines_added: Number of lines added
            lines_removed: Number of lines removed

        Returns:
            Node ID for this file change
        """
        node_id = self._next_node_id("file")

        self.client.record_event(
            "file_change",
            {
                "event_type": "file_change",
                "path": path,
                "action": action,
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "node_id": node_id,
            },
        )

        return node_id

    def record_test_result(
        self,
        framework: str,
        passed: int,
        failed: int,
        skipped: int = 0,
        coverage: float = 0.0,
        failed_tests: list[str] | None = None,
    ) -> str:
        """
        Record test execution results.

        Args:
            framework: Test framework (pytest, jest, cargo, go)
            passed: Number of passed tests
            failed: Number of failed tests
            skipped: Number of skipped tests
            coverage: Code coverage percentage
            failed_tests: List of failed test names

        Returns:
            Node ID for this test result
        """
        node_id = self._next_node_id("test")

        self.client.record_event(
            "test_result",
            {
                "event_type": "test_result",
                "framework": framework,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "coverage": coverage,
                "failed_tests": failed_tests or [],
                "node_id": node_id,
            },
        )

        # Record metrics
        self.client.record_metric("tests.passed", passed, MetricType.GAUGE)
        self.client.record_metric("tests.failed", failed, MetricType.GAUGE)
        if coverage > 0:
            self.client.record_metric("tests.coverage", coverage, MetricType.GAUGE)

        return node_id

    def record_score_update(
        self,
        old_score: float,
        new_score: float,
        reason: str = "",
        dimensions: dict[str, float] | None = None,
    ) -> None:
        """
        Record a quality score update.

        Args:
            old_score: Previous score
            new_score: New score
            reason: Reason for the change
            dimensions: Quality dimension breakdown
        """
        payload = {
            "event_type": "score_update",
            "old_score": old_score,
            "new_score": new_score,
            "reason": reason,
        }

        if dimensions:
            payload["dimensions"] = dimensions

        self.client.record_event("score_update", payload)

    def record_subagent_spawn(
        self,
        subagent_id: str,
        subagent_type: str,
        task: str,
        parent_node_id: str | None = None,
    ) -> str:
        """
        Record a subagent being spawned.

        Args:
            subagent_id: Unique identifier for the subagent
            subagent_type: Type of subagent (Explore, Plan, etc.)
            task: Task assigned to the subagent
            parent_node_id: Parent node for tree visualization

        Returns:
            Node ID for this subagent
        """
        node_id = self._next_node_id("subagent")

        self.client.record_event(
            "subagent_spawn",
            {
                "event_type": "subagent_spawn",
                "subagent_id": subagent_id,
                "subagent_type": subagent_type,
                "task": task,
                "depth": self.current_depth + 1,
                "node_id": node_id,
                "parent_node_id": parent_node_id or f"iter-{self.current_iteration}",
            },
        )

        self.client.increment("subagents.spawned")

        return node_id

    def record_subagent_complete(
        self,
        subagent_id: str,
        node_id: str,
        success: bool,
        result: str = "",
    ) -> None:
        """
        Record a subagent completing.

        Args:
            subagent_id: Unique identifier for the subagent
            node_id: Node ID from spawn event
            success: Whether the subagent succeeded
            result: Result summary
        """
        self.client.record_event(
            "subagent_complete",
            {
                "event_type": "subagent_complete",
                "subagent_id": subagent_id,
                "node_id": node_id,
                "success": success,
                "result": result,
            },
        )

    def record_artifact(
        self,
        path: str,
        artifact_type: str,
        title: str,
    ) -> None:
        """
        Record an artifact being written (e.g., Obsidian note).

        Args:
            path: Path to the artifact
            artifact_type: Type (decision, evidence, summary)
            title: Human-readable title
        """
        self.client.record_event(
            "artifact",
            {
                "event_type": "artifact",
                "path": path,
                "type": artifact_type,
                "title": title,
            },
        )

    def record_error(
        self,
        error_type: str,
        message: str,
        traceback: str = "",
        recoverable: bool = True,
    ) -> None:
        """
        Record an error.

        Args:
            error_type: Type of error
            message: Error message
            traceback: Stack trace if available
            recoverable: Whether execution can continue
        """
        self.client.record_event(
            "error",
            {
                "event_type": "error",
                "error_type": error_type,
                "message": message,
                "traceback": traceback,
                "recoverable": recoverable,
            },
        )

    def record_log(
        self,
        level: str,
        message: str,
        source: str = "",
    ) -> None:
        """
        Record a log message.

        Args:
            level: Log level (debug, info, warn, error)
            message: Log message
            source: Source of the log
        """
        self.client.record_event(
            "log",
            {
                "event_type": "log",
                "level": level,
                "message": message,
                "source": source,
            },
        )

    def record_state_change(
        self,
        old_state: str,
        new_state: str,
        reason: str = "",
    ) -> None:
        """
        Record an execution state change.

        Args:
            old_state: Previous state
            new_state: New state
            reason: Reason for the change
        """
        self.client.record_event(
            "state_change",
            {
                "event_type": "state_change",
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
            },
        )

    def _summarize_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
    ) -> str:
        """Generate a human-readable summary for a tool invocation."""
        if tool_name == "Write":
            path = tool_input.get("file_path", "file")
            return f"Created {path}"

        elif tool_name == "Edit":
            path = tool_input.get("file_path", "file")
            return f"Modified {path}"

        elif tool_name == "Read":
            path = tool_input.get("file_path", "file")
            return f"Read {path}"

        elif tool_name == "Bash":
            cmd = tool_input.get("command", "")
            # Truncate long commands
            if len(cmd) > 60:
                cmd = cmd[:57] + "..."
            return f"Ran: {cmd}"

        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"Searched for: {pattern}"

        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            return f"Found files: {pattern}"

        elif tool_name == "Task":
            desc = tool_input.get("description", "task")
            return f"Spawned: {desc}"

        else:
            return f"Used {tool_name}"

    def flush(self) -> None:
        """Flush any buffered events."""
        self.client.flush()

    def close(self) -> None:
        """Close the tracker and flush remaining events."""
        self.client.close()


def create_events_hooks(
    evidence: EvidenceCollector,
    tracker: EventsTracker | None = None,
    session_id: str | None = None,
) -> dict[str, list[dict]]:
    """
    Create SDK hooks for event tracking.

    Args:
        evidence: EvidenceCollector instance
        tracker: Optional EventsTracker (created if not provided)
        session_id: Session ID for the tracker

    Returns:
        Hook configuration dict for merge_hooks()
    """
    if tracker is None:
        tracker = EventsTracker(session_id=session_id)

    async def on_tool_use(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PostToolUse: Record tool invocations."""
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", "")

        # Check if this was blocked
        blocked = False
        block_reason = ""
        hook_output = input_data.get("hookSpecificOutput", {})
        if hook_output.get("permissionDecision") == "deny":
            blocked = True
            block_reason = hook_output.get("permissionDecisionReason", "")

        tracker.record_tool_use(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_response,
            blocked=blocked,
            block_reason=block_reason,
        )

        # Record file changes specifically
        if tool_name == "Write":
            path = tool_input.get("file_path", "")
            content = tool_input.get("content", "")
            lines = content.count("\n") + 1 if content else 0
            tracker.record_file_change(path, "write", lines_added=lines)

        elif tool_name == "Edit":
            path = tool_input.get("file_path", "")
            old_str = tool_input.get("old_string", "")
            new_str = tool_input.get("new_string", "")
            lines_removed = old_str.count("\n") + 1 if old_str else 0
            lines_added = new_str.count("\n") + 1 if new_str else 0
            tracker.record_file_change(
                path,
                "edit",
                lines_added=lines_added,
                lines_removed=lines_removed,
            )

        return {}

    async def on_subagent(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """SubagentStop: Record subagent completions."""
        if input_data.get("hook_event_name") != "SubagentStop":
            return {}

        subagent_id = input_data.get("subagent_id", "")
        result = input_data.get("result", "")

        # Try to find the node_id from context
        node_id = context.get(f"subagent_node_{subagent_id}", "")

        tracker.record_subagent_complete(
            subagent_id=subagent_id,
            node_id=node_id,
            success=True,  # Assume success if we get here
            result=str(result)[:200] if result else "",
        )

        return {}

    async def on_stop(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Stop: Flush events and record completion."""
        if input_data.get("hook_event_name") != "Stop":
            return {}

        # Record any test results from evidence
        if evidence.tests_run:
            for test_result in evidence.test_results:
                tracker.record_test_result(
                    framework=test_result.get("framework", "unknown"),
                    passed=test_result.get("passed", 0),
                    failed=test_result.get("failed", 0),
                    skipped=test_result.get("skipped", 0),
                    coverage=test_result.get("coverage", 0.0),
                    failed_tests=test_result.get("failed_tests", []),
                )

        tracker.flush()
        return {}

    return {
        "PostToolUse": [{"hooks": [on_tool_use]}],
        "SubagentStop": [{"hooks": [on_subagent]}],
        "Stop": [{"hooks": [on_stop]}],
    }


def create_iteration_callback(
    tracker: EventsTracker,
) -> callable:
    """
    Create an on_iteration callback for the loop runner.

    Args:
        tracker: EventsTracker instance

    Returns:
        Callback function for run_agentic_loop(on_iteration=...)
    """

    def on_iteration(result: "IterationResult") -> None:  # noqa: F821
        """Called after each iteration completes."""
        # Extract quality dimensions from evidence
        dimensions = None
        if "quality_dimensions" in result.evidence:
            dimensions = result.evidence["quality_dimensions"]

        tracker.record_iteration_complete(
            iteration=result.iteration,
            score=result.score,
            improvements=result.improvements,
            dimensions=dimensions,
            duration_seconds=result.duration_seconds,
        )

        # Ensure events are flushed immediately
        tracker.flush()

    return on_iteration
