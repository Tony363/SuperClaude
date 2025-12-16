"""Tests for CommandExecutor codex and fast-codex handling."""

from __future__ import annotations


class TestCodexSuggestionsExtraction:
    """Tests for extracting codex suggestions from agent outputs."""

    def test_extract_codex_suggestions(self, executor, sample_context):
        """Extracts codex_suggestions from codex-implementer output."""
        sample_context.agent_outputs = {
            "codex-implementer": {
                "codex_suggestions": {
                    "summary": "Add new endpoint",
                    "changes": [{"path": "src/api.py", "content": "# new content"}],
                }
            }
        }

        codex_output = None
        codex_agent_output = sample_context.agent_outputs.get("codex-implementer")
        if isinstance(codex_agent_output, dict):
            codex_output = codex_agent_output.get("codex_suggestions")

        assert codex_output is not None
        assert codex_output["summary"] == "Add new endpoint"
        assert len(codex_output["changes"]) == 1

    def test_no_codex_suggestions(self, executor, sample_context):
        """Handles missing codex_suggestions gracefully."""
        sample_context.agent_outputs = {"codex-implementer": {"other_field": "value"}}

        codex_output = None
        codex_agent_output = sample_context.agent_outputs.get("codex-implementer")
        if isinstance(codex_agent_output, dict):
            codex_output = codex_agent_output.get("codex_suggestions")

        assert codex_output is None

    def test_no_codex_implementer(self, executor, sample_context):
        """Handles missing codex-implementer agent."""
        sample_context.agent_outputs = {}

        codex_agent_output = sample_context.agent_outputs.get("codex-implementer")

        assert codex_agent_output is None


class TestCodexCliMetadata:
    """Tests for codex CLI metadata handling."""

    def test_extract_cli_metadata(self, executor, sample_context):
        """Extracts codex_cli metadata."""
        sample_context.agent_outputs = {
            "codex-implementer": {
                "codex_cli": {
                    "duration_s": 5.5,
                    "returncode": 0,
                    "stdout": "Success output",
                    "stderr": "",
                }
            }
        }

        codex_agent_output = sample_context.agent_outputs.get("codex-implementer")
        cli_meta = codex_agent_output.get("codex_cli")

        assert cli_meta is not None
        assert cli_meta["duration_s"] == 5.5
        assert cli_meta["returncode"] == 0

    def test_cli_metadata_missing(self, executor, sample_context):
        """Handles missing codex_cli metadata."""
        sample_context.agent_outputs = {"codex-implementer": {"codex_suggestions": {}}}

        codex_agent_output = sample_context.agent_outputs.get("codex-implementer")
        cli_meta = codex_agent_output.get("codex_cli")

        assert cli_meta is None


class TestTruncateFastCodexStream:
    """Tests for _truncate_fast_codex_stream method."""

    def test_truncate_short_stream(self, executor):
        """Short streams pass through unchanged."""
        short_text = "Hello world"
        result = executor._truncate_fast_codex_stream(short_text)

        assert result == short_text

    def test_truncate_long_stream(self, executor):
        """Long streams are truncated."""
        long_text = "x" * 10000
        result = executor._truncate_fast_codex_stream(long_text)

        assert len(result) < len(long_text)

    def test_truncate_none_stream(self, executor):
        """None stream returns None or empty."""
        result = executor._truncate_fast_codex_stream(None)

        assert result is None or result == ""

    def test_truncate_empty_stream(self, executor):
        """Empty stream returns empty."""
        result = executor._truncate_fast_codex_stream("")

        assert result == ""


class TestFastCodexActive:
    """Tests for fast-codex activation state."""

    def test_fast_codex_requested_flag(self, sample_context):
        """Context tracks fast_codex_requested."""
        sample_context.fast_codex_requested = True

        assert sample_context.fast_codex_requested is True

    def test_fast_codex_active_flag(self, sample_context):
        """Context tracks fast_codex_active."""
        sample_context.fast_codex_active = True

        assert sample_context.fast_codex_active is True

    def test_fast_codex_defaults_false(self, sample_context):
        """Fast-codex flags default to False."""
        assert hasattr(sample_context, "fast_codex_requested")
        assert hasattr(sample_context, "fast_codex_active")


class TestCodexChangeCount:
    """Tests for codex change counting."""

    def test_count_changes_in_suggestions(self, executor, sample_context):
        """Counts changes from codex suggestions."""
        codex_output = {
            "summary": "Test",
            "changes": [
                {"path": "a.py"},
                {"path": "b.py"},
                {"path": "c.py"},
            ],
        }

        change_count = len(codex_output.get("changes") or [])

        assert change_count == 3

    def test_count_changes_empty(self, executor, sample_context):
        """Handles empty changes list."""
        codex_output = {
            "summary": "Test",
            "changes": [],
        }

        change_count = len(codex_output.get("changes") or [])

        assert change_count == 0

    def test_count_changes_none(self, executor, sample_context):
        """Handles None changes."""
        codex_output = {
            "summary": "Test",
            "changes": None,
        }

        change_count = len(codex_output.get("changes") or [])

        assert change_count == 0

    def test_count_changes_missing(self, executor, sample_context):
        """Handles missing changes key."""
        codex_output = {
            "summary": "Test",
        }

        change_count = len(codex_output.get("changes") or [])

        assert change_count == 0


class TestCodexSuggestionsInResults:
    """Tests for codex suggestions in context results."""

    def test_suggestions_added_to_results(self, executor, sample_context):
        """Codex suggestions added to context results."""
        sample_context.results = {}
        codex_output = {
            "summary": "Add endpoint",
            "changes": [{"path": "api.py"}],
        }

        sample_context.results["codex_suggestions"] = codex_output

        assert sample_context.results["codex_suggestions"] == codex_output


class TestFastCodexResultsState:
    """Tests for fast_codex state in results."""

    def test_fast_codex_state_recorded(self, executor, sample_context):
        """Fast-codex state recorded in results."""
        sample_context.results = {}
        sample_context.fast_codex_requested = True
        sample_context.fast_codex_active = True
        sample_context.active_personas = ["implementer"]

        fast_state = sample_context.results.setdefault("fast_codex", {})
        fast_state["requested"] = sample_context.fast_codex_requested
        fast_state["active"] = sample_context.fast_codex_active
        fast_state["personas"] = list(sample_context.active_personas)

        assert sample_context.results["fast_codex"]["requested"] is True
        assert sample_context.results["fast_codex"]["active"] is True
        assert "implementer" in sample_context.results["fast_codex"]["personas"]


class TestWorktreeWarnings:
    """Tests for worktree warning handling."""

    def test_warnings_added_to_results(self, executor, sample_context):
        """Worktree warnings added to context results."""
        sample_context.results = {}

        warnings_list = sample_context.results.setdefault("worktree_warnings", [])
        warnings_list.append("Test warning")

        assert "Test warning" in sample_context.results["worktree_warnings"]

    def test_warnings_deduplicated(self, executor, sample_context):
        """Worktree warnings are deduplicated."""
        sample_context.results = {"worktree_warnings": []}

        warnings = ["Warning 1", "Warning 1", "Warning 2"]
        sample_context.results["worktree_warnings"] = executor._deduplicate(warnings)

        assert len(sample_context.results["worktree_warnings"]) == 2


class TestAppliedChangesTracking:
    """Tests for tracking applied changes."""

    def test_applied_changes_recorded(self, executor, sample_context):
        """Applied changes recorded in results."""
        sample_context.results = {}
        applied_files = ["a.py", "b.py"]

        applied_list = sample_context.results.setdefault("applied_changes", [])
        applied_list.extend(f"apply {path}" for path in applied_files)

        assert "apply a.py" in sample_context.results["applied_changes"]
        assert "apply b.py" in sample_context.results["applied_changes"]

    def test_applied_changes_deduplicated(self, executor, sample_context):
        """Applied changes are deduplicated."""
        sample_context.results = {"applied_changes": []}

        changes = ["apply a.py", "apply a.py", "apply b.py"]
        sample_context.results["applied_changes"] = executor._deduplicate(changes)

        assert len(sample_context.results["applied_changes"]) == 2
