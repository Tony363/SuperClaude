"""Tests for events tracking hooks in SuperClaude.Orchestrator.events_hooks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from SuperClaude.Orchestrator.events_hooks import (
    EventsTracker,
    create_events_hooks,
    create_iteration_callback,
)
from SuperClaude.Orchestrator.evidence import EvidenceCollector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client():
    """Create a mock JsonlTelemetryClient."""
    client = MagicMock()
    client.record_event = MagicMock()
    client.record_metric = MagicMock()
    client.increment = MagicMock()
    client.flush = MagicMock()
    client.close = MagicMock()
    return client


def _make_tracker(**kwargs) -> EventsTracker:
    """Create an EventsTracker with a mocked telemetry client."""
    tracker = EventsTracker.__new__(EventsTracker)
    tracker.client = _make_mock_client()
    tracker.current_iteration = 0
    tracker.current_depth = 0
    tracker._node_counter = 0
    return tracker


# ===========================================================================
# EventsTracker
# ===========================================================================


class TestEventsTrackerInit:
    """Tests for EventsTracker initialization."""

    @patch("SuperClaude.Orchestrator.events_hooks.JsonlTelemetryClient")
    def test_init_defaults(self, mock_cls):
        """Test default initialization creates client with buffer_size=1."""
        tracker = EventsTracker()

        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["buffer_size"] == 1
        assert call_kwargs["auto_flush"] is True
        assert tracker.current_iteration == 0
        assert tracker.current_depth == 0
        assert tracker._node_counter == 0

    @patch("SuperClaude.Orchestrator.events_hooks.JsonlTelemetryClient")
    def test_init_custom_session_id(self, mock_cls):
        """Test initialization with custom session ID."""
        tracker = EventsTracker(session_id="test-session-42")

        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["session_id"] == "test-session-42"


class TestNodeIdGeneration:
    """Tests for node ID generation."""

    def test_next_node_id_increments(self):
        """Test _next_node_id generates incrementing IDs."""
        tracker = _make_tracker()

        id1 = tracker._next_node_id("tool")
        id2 = tracker._next_node_id("tool")
        id3 = tracker._next_node_id("file")

        assert id1 == "tool-1"
        assert id2 == "tool-2"
        assert id3 == "file-3"

    def test_next_node_id_default_prefix(self):
        """Test _next_node_id uses 'node' as default prefix."""
        tracker = _make_tracker()

        nid = tracker._next_node_id()
        assert nid == "node-1"


class TestRecordIteration:
    """Tests for iteration recording."""

    def test_record_iteration_start(self):
        """Test recording iteration start emits event and returns node ID."""
        tracker = _make_tracker()

        node_id = tracker.record_iteration_start(0, depth=0)

        assert node_id == "iter-0"
        assert tracker.current_iteration == 0
        assert tracker.current_depth == 0
        tracker.client.record_event.assert_called_once_with(
            "iteration_start",
            {
                "event_type": "iteration_start",
                "iteration": 0,
                "depth": 0,
                "node_id": "iter-0",
            },
        )

    def test_record_iteration_start_updates_state(self):
        """Test record_iteration_start updates internal state."""
        tracker = _make_tracker()

        tracker.record_iteration_start(2, depth=1)

        assert tracker.current_iteration == 2
        assert tracker.current_depth == 1

    def test_record_iteration_complete(self):
        """Test recording iteration complete emits event and metric."""
        tracker = _make_tracker()

        tracker.record_iteration_complete(
            iteration=1,
            score=85.0,
            improvements=["add tests"],
            dimensions={"code": 90.0, "tests": 80.0},
            duration_seconds=12.5,
        )

        assert tracker.client.record_event.call_count == 1
        call_args = tracker.client.record_event.call_args
        assert call_args[0][0] == "iteration_complete"
        payload = call_args[0][1]
        assert payload["iteration"] == 1
        assert payload["score"] == 85.0
        assert payload["improvements"] == ["add tests"]
        assert payload["dimensions"] == {"code": 90.0, "tests": 80.0}
        assert payload["duration_seconds"] == 12.5
        assert payload["node_id"] == "iter-1"

        tracker.client.record_metric.assert_called_once()

    def test_record_iteration_complete_no_dimensions(self):
        """Test iteration complete without dimensions omits the key."""
        tracker = _make_tracker()

        tracker.record_iteration_complete(iteration=0, score=50.0)

        payload = tracker.client.record_event.call_args[0][1]
        assert "dimensions" not in payload

    def test_record_iteration_complete_empty_improvements(self):
        """Test iteration complete defaults improvements to empty list."""
        tracker = _make_tracker()

        tracker.record_iteration_complete(iteration=0, score=50.0)

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["improvements"] == []


class TestRecordToolUse:
    """Tests for tool use recording."""

    def test_record_tool_use_basic(self):
        """Test recording a basic tool invocation."""
        tracker = _make_tracker()
        tracker.current_iteration = 1
        tracker.current_depth = 0

        node_id = tracker.record_tool_use(
            tool_name="Write",
            tool_input={"file_path": "src/main.py"},
        )

        assert node_id == "tool-1"
        tracker.client.record_event.assert_called_once()
        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "tool_use"
        assert payload["tool"] == "Write"
        assert payload["blocked"] is False
        assert payload["depth"] == 1
        assert payload["parent_node_id"] == "iter-1"
        tracker.client.increment.assert_called_once_with("tools.invoked")

    def test_record_tool_use_blocked(self):
        """Test recording a blocked tool invocation."""
        tracker = _make_tracker()

        node_id = tracker.record_tool_use(
            tool_name="Bash",
            tool_input={"command": "rm -rf /"},
            blocked=True,
            block_reason="Dangerous command",
        )

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["blocked"] is True
        assert payload["block_reason"] == "Dangerous command"

    def test_record_tool_use_custom_parent(self):
        """Test recording a tool invocation with custom parent node."""
        tracker = _make_tracker()

        tracker.record_tool_use(
            tool_name="Read",
            tool_input={"file_path": "README.md"},
            parent_node_id="subagent-5",
        )

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["parent_node_id"] == "subagent-5"


class TestRecordFileChange:
    """Tests for file change recording."""

    def test_record_file_change(self):
        """Test recording a file change."""
        tracker = _make_tracker()

        node_id = tracker.record_file_change(
            path="src/auth.py",
            action="write",
            lines_added=50,
            lines_removed=0,
        )

        assert node_id == "file-1"
        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "file_change"
        assert payload["path"] == "src/auth.py"
        assert payload["action"] == "write"
        assert payload["lines_added"] == 50
        assert payload["lines_removed"] == 0


class TestRecordTestResult:
    """Tests for test result recording."""

    def test_record_test_result(self):
        """Test recording test results with all fields."""
        tracker = _make_tracker()

        node_id = tracker.record_test_result(
            framework="pytest",
            passed=10,
            failed=2,
            skipped=1,
            coverage=85.0,
            failed_tests=["test_auth", "test_login"],
        )

        assert node_id == "test-1"
        payload = tracker.client.record_event.call_args[0][1]
        assert payload["framework"] == "pytest"
        assert payload["passed"] == 10
        assert payload["failed"] == 2
        assert payload["skipped"] == 1
        assert payload["coverage"] == 85.0
        assert payload["failed_tests"] == ["test_auth", "test_login"]

        # Should record 3 metrics: passed, failed, coverage
        assert tracker.client.record_metric.call_count == 3

    def test_record_test_result_no_coverage(self):
        """Test recording test results without coverage skips coverage metric."""
        tracker = _make_tracker()

        tracker.record_test_result(
            framework="jest",
            passed=5,
            failed=0,
            coverage=0.0,
        )

        # Should record 2 metrics: passed, failed (not coverage)
        assert tracker.client.record_metric.call_count == 2

    def test_record_test_result_defaults(self):
        """Test recording test results with defaults."""
        tracker = _make_tracker()

        tracker.record_test_result(framework="cargo", passed=3, failed=0)

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["skipped"] == 0
        assert payload["coverage"] == 0.0
        assert payload["failed_tests"] == []


class TestRecordScoreUpdate:
    """Tests for score update recording."""

    def test_record_score_update(self):
        """Test recording a score update."""
        tracker = _make_tracker()

        tracker.record_score_update(
            old_score=60.0,
            new_score=75.0,
            reason="Tests now passing",
            dimensions={"tests": 100.0},
        )

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "score_update"
        assert payload["old_score"] == 60.0
        assert payload["new_score"] == 75.0
        assert payload["reason"] == "Tests now passing"
        assert payload["dimensions"] == {"tests": 100.0}

    def test_record_score_update_no_dimensions(self):
        """Test score update without dimensions omits the key."""
        tracker = _make_tracker()

        tracker.record_score_update(old_score=50.0, new_score=60.0)

        payload = tracker.client.record_event.call_args[0][1]
        assert "dimensions" not in payload


class TestRecordSubagent:
    """Tests for subagent recording."""

    def test_record_subagent_spawn(self):
        """Test recording subagent spawn."""
        tracker = _make_tracker()
        tracker.current_iteration = 0
        tracker.current_depth = 0

        node_id = tracker.record_subagent_spawn(
            subagent_id="agent-abc",
            subagent_type="Explore",
            task="Find error handlers",
        )

        assert node_id == "subagent-1"
        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "subagent_spawn"
        assert payload["subagent_id"] == "agent-abc"
        assert payload["subagent_type"] == "Explore"
        assert payload["task"] == "Find error handlers"
        assert payload["depth"] == 1
        assert payload["parent_node_id"] == "iter-0"
        tracker.client.increment.assert_called_with("subagents.spawned")

    def test_record_subagent_complete(self):
        """Test recording subagent completion."""
        tracker = _make_tracker()

        tracker.record_subagent_complete(
            subagent_id="agent-abc",
            node_id="subagent-1",
            success=True,
            result="Found 3 error handlers",
        )

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "subagent_complete"
        assert payload["success"] is True
        assert payload["result"] == "Found 3 error handlers"


class TestRecordMisc:
    """Tests for miscellaneous recording methods."""

    def test_record_artifact(self):
        """Test recording an artifact."""
        tracker = _make_tracker()

        tracker.record_artifact(
            path="vault/decisions/auth.md",
            artifact_type="decision",
            title="Auth Strategy",
        )

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "artifact"
        assert payload["path"] == "vault/decisions/auth.md"
        assert payload["type"] == "decision"
        assert payload["title"] == "Auth Strategy"

    def test_record_error(self):
        """Test recording an error."""
        tracker = _make_tracker()

        tracker.record_error(
            error_type="ImportError",
            message="Module not found",
            traceback="Traceback ...",
            recoverable=False,
        )

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "error"
        assert payload["error_type"] == "ImportError"
        assert payload["recoverable"] is False

    def test_record_error_defaults(self):
        """Test recording an error with defaults."""
        tracker = _make_tracker()

        tracker.record_error(error_type="ValueError", message="bad input")

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["traceback"] == ""
        assert payload["recoverable"] is True

    def test_record_log(self):
        """Test recording a log message."""
        tracker = _make_tracker()

        tracker.record_log(level="warn", message="Retry limit", source="loop_runner")

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "log"
        assert payload["level"] == "warn"
        assert payload["message"] == "Retry limit"
        assert payload["source"] == "loop_runner"

    def test_record_state_change(self):
        """Test recording a state change."""
        tracker = _make_tracker()

        tracker.record_state_change(
            old_state="running",
            new_state="completed",
            reason="quality_threshold_met",
        )

        payload = tracker.client.record_event.call_args[0][1]
        assert payload["event_type"] == "state_change"
        assert payload["old_state"] == "running"
        assert payload["new_state"] == "completed"


class TestFlushAndClose:
    """Tests for flush and close."""

    def test_flush_delegates_to_client(self):
        """Test flush delegates to telemetry client."""
        tracker = _make_tracker()
        tracker.flush()
        tracker.client.flush.assert_called_once()

    def test_close_delegates_to_client(self):
        """Test close delegates to telemetry client."""
        tracker = _make_tracker()
        tracker.close()
        tracker.client.close.assert_called_once()


# ===========================================================================
# _summarize_tool
# ===========================================================================


class TestSummarizeTool:
    """Tests for the _summarize_tool helper."""

    def test_summarize_write(self):
        """Test summary for Write tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool(
            "Write", {"file_path": "src/main.py"}, None
        )
        assert result == "Created src/main.py"

    def test_summarize_edit(self):
        """Test summary for Edit tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool(
            "Edit", {"file_path": "src/config.py"}, None
        )
        assert result == "Modified src/config.py"

    def test_summarize_read(self):
        """Test summary for Read tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool(
            "Read", {"file_path": "README.md"}, None
        )
        assert result == "Read README.md"

    def test_summarize_bash(self):
        """Test summary for Bash tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool(
            "Bash", {"command": "pytest tests/"}, None
        )
        assert result == "Ran: pytest tests/"

    def test_summarize_bash_truncates_long_commands(self):
        """Test summary truncates long bash commands."""
        tracker = _make_tracker()
        long_cmd = "a" * 100
        result = tracker._summarize_tool("Bash", {"command": long_cmd}, None)
        assert len(result) <= 65  # "Ran: " + 57 chars + "..."
        assert result.endswith("...")

    def test_summarize_grep(self):
        """Test summary for Grep tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool(
            "Grep", {"pattern": "def main"}, None
        )
        assert result == "Searched for: def main"

    def test_summarize_glob(self):
        """Test summary for Glob tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool(
            "Glob", {"pattern": "**/*.py"}, None
        )
        assert result == "Found files: **/*.py"

    def test_summarize_task(self):
        """Test summary for Task tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool(
            "Task", {"description": "search codebase"}, None
        )
        assert result == "Spawned: search codebase"

    def test_summarize_unknown_tool(self):
        """Test summary for unknown tool."""
        tracker = _make_tracker()
        result = tracker._summarize_tool("LSP", {}, None)
        assert result == "Used LSP"


# ===========================================================================
# create_events_hooks
# ===========================================================================


class TestCreateEventsHooks:
    """Tests for create_events_hooks factory."""

    def test_returns_hook_config(self):
        """Test returns valid hook configuration dict."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()

        hooks = create_events_hooks(evidence, tracker)

        assert isinstance(hooks, dict)
        assert "PostToolUse" in hooks
        assert "SubagentStop" in hooks
        assert "Stop" in hooks

    @patch("SuperClaude.Orchestrator.events_hooks.EventsTracker")
    def test_creates_tracker_if_none(self, mock_tracker_cls):
        """Test creates a new tracker when none provided."""
        evidence = EvidenceCollector()
        mock_tracker_cls.return_value = _make_tracker()

        hooks = create_events_hooks(evidence, tracker=None, session_id="sess-1")

        mock_tracker_cls.assert_called_once_with(session_id="sess-1")

    def test_uses_provided_tracker(self):
        """Test uses the provided tracker instead of creating one."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()

        hooks = create_events_hooks(evidence, tracker)

        # Should not have created a new tracker - just used ours
        assert "PostToolUse" in hooks

    @pytest.mark.asyncio
    async def test_on_tool_use_records_event(self):
        """Test PostToolUse hook records tool invocation."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["PostToolUse"][0]["hooks"][0]
        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "test.py"},
                "tool_response": "contents",
            },
            None,
            {},
        )

        tracker.client.record_event.assert_called()
        call_args = tracker.client.record_event.call_args_list
        # Should have at least one tool_use event
        event_types = [c[0][0] for c in call_args]
        assert "tool_use" in event_types

    @pytest.mark.asyncio
    async def test_on_tool_use_tracks_write_file_change(self):
        """Test PostToolUse hook records file change for Write tool."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["PostToolUse"][0]["hooks"][0]
        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "new.py", "content": "line1\nline2\nline3"},
                "tool_response": "ok",
            },
            None,
            {},
        )

        # Should record both tool_use and file_change events
        call_args = tracker.client.record_event.call_args_list
        event_types = [c[0][0] for c in call_args]
        assert "tool_use" in event_types
        assert "file_change" in event_types

    @pytest.mark.asyncio
    async def test_on_tool_use_tracks_edit_file_change(self):
        """Test PostToolUse hook records file change for Edit tool."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["PostToolUse"][0]["hooks"][0]
        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "app.py",
                    "old_string": "old_line\n",
                    "new_string": "new_line_1\nnew_line_2\n",
                },
                "tool_response": "ok",
            },
            None,
            {},
        )

        call_args = tracker.client.record_event.call_args_list
        event_types = [c[0][0] for c in call_args]
        assert "file_change" in event_types

    @pytest.mark.asyncio
    async def test_on_tool_use_records_blocked(self):
        """Test PostToolUse hook records blocked tool invocations."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["PostToolUse"][0]["hooks"][0]
        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf /"},
                "tool_response": "",
                "hookSpecificOutput": {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Dangerous command",
                },
            },
            None,
            {},
        )

        call_args = tracker.client.record_event.call_args_list
        tool_use_calls = [c for c in call_args if c[0][0] == "tool_use"]
        assert len(tool_use_calls) == 1

    @pytest.mark.asyncio
    async def test_on_tool_use_ignores_non_posttooluse(self):
        """Test PostToolUse hook ignores non-PostToolUse events."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["PostToolUse"][0]["hooks"][0]
        result = await hook_fn(
            {"hook_event_name": "PreToolUse", "tool_name": "Read"},
            None,
            {},
        )

        assert result == {}
        tracker.client.record_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_stop_flushes_tracker(self):
        """Test Stop hook flushes the tracker."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["Stop"][0]["hooks"][0]
        await hook_fn(
            {"hook_event_name": "Stop"},
            None,
            {},
        )

        tracker.client.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_stop_ignores_non_stop(self):
        """Test Stop hook ignores non-Stop events."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["Stop"][0]["hooks"][0]
        result = await hook_fn(
            {"hook_event_name": "PostToolUse"},
            None,
            {},
        )

        assert result == {}
        tracker.client.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_subagent_records_completion(self):
        """Test SubagentStop hook records subagent completion."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["SubagentStop"][0]["hooks"][0]
        await hook_fn(
            {
                "hook_event_name": "SubagentStop",
                "subagent_id": "agent-xyz",
                "result": "Done searching",
            },
            None,
            {"subagent_node_agent-xyz": "subagent-1"},
        )

        call_args = tracker.client.record_event.call_args_list
        event_types = [c[0][0] for c in call_args]
        assert "subagent_complete" in event_types

    @pytest.mark.asyncio
    async def test_on_subagent_ignores_non_subagent_stop(self):
        """Test SubagentStop hook ignores non-SubagentStop events."""
        evidence = EvidenceCollector()
        tracker = _make_tracker()
        hooks = create_events_hooks(evidence, tracker)

        hook_fn = hooks["SubagentStop"][0]["hooks"][0]
        result = await hook_fn(
            {"hook_event_name": "PostToolUse"},
            None,
            {},
        )

        assert result == {}
        tracker.client.record_event.assert_not_called()


# ===========================================================================
# create_iteration_callback
# ===========================================================================


class TestCreateIterationCallback:
    """Tests for create_iteration_callback factory."""

    def test_returns_callable(self):
        """Test returns a callable."""
        tracker = _make_tracker()
        callback = create_iteration_callback(tracker)
        assert callable(callback)

    def test_records_iteration_complete(self):
        """Test callback records iteration complete event."""
        from SuperClaude.Orchestrator.loop_runner import IterationResult

        tracker = _make_tracker()
        callback = create_iteration_callback(tracker)

        result = IterationResult(
            iteration=0,
            score=75.0,
            improvements=["add error handling"],
            evidence={"quality_dimensions": {"code": 80.0, "tests": 70.0}},
            duration_seconds=10.0,
            messages_count=5,
        )

        callback(result)

        # Should have recorded iteration_complete event
        tracker.client.record_event.assert_called()
        call_args = tracker.client.record_event.call_args
        assert call_args[0][0] == "iteration_complete"
        payload = call_args[0][1]
        assert payload["iteration"] == 0
        assert payload["score"] == 75.0
        assert payload["dimensions"] == {"code": 80.0, "tests": 70.0}

    def test_records_without_dimensions(self):
        """Test callback handles missing quality_dimensions."""
        from SuperClaude.Orchestrator.loop_runner import IterationResult

        tracker = _make_tracker()
        callback = create_iteration_callback(tracker)

        result = IterationResult(
            iteration=1,
            score=60.0,
            improvements=[],
            evidence={},
            duration_seconds=5.0,
            messages_count=3,
        )

        callback(result)

        tracker.client.record_event.assert_called()

    def test_flushes_after_recording(self):
        """Test callback flushes tracker after recording."""
        from SuperClaude.Orchestrator.loop_runner import IterationResult

        tracker = _make_tracker()
        callback = create_iteration_callback(tracker)

        result = IterationResult(
            iteration=0,
            score=50.0,
            improvements=[],
            evidence={},
            duration_seconds=1.0,
            messages_count=1,
        )

        callback(result)

        tracker.client.flush.assert_called_once()
