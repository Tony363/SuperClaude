"""Tests for .claude/skills/sc-implement/scripts/loop_entry.py.

Validates loop entry point functions: parse_context, build_config,
create_mock_skill_invoker, create_signal_only_response, run_loop.
"""

import sys
from pathlib import Path

# Add the scripts directory so loop_entry can be imported
_scripts_dir = str(
    Path(__file__).parent.parent.parent / ".claude" / "skills" / "sc-implement" / "scripts"
)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from loop_entry import (  # noqa: E402
    build_config,
    create_mock_skill_invoker,
    create_signal_only_response,
    parse_context,
    run_loop,
)


class TestParseContext:
    """Tests for parse_context()."""

    def test_valid_json(self):
        """Should parse valid JSON correctly."""
        result = parse_context('{"task": "implement feature", "max_iterations": 2}')
        assert result["task"] == "implement feature"
        assert result["max_iterations"] == 2

    def test_invalid_json_returns_error(self):
        """Should return error dict for invalid JSON."""
        result = parse_context("not valid json")
        assert "error" in result
        assert "Invalid JSON" in result["error"]

    def test_empty_string_returns_error(self):
        """Should return error for empty string."""
        result = parse_context("")
        assert "error" in result

    def test_empty_object(self):
        """Should parse empty JSON object."""
        result = parse_context("{}")
        assert result == {}


class TestBuildConfig:
    """Tests for build_config()."""

    def test_defaults(self):
        """Should use sensible defaults when keys missing."""
        config = build_config({})
        assert config.max_iterations == 3
        assert config.quality_threshold == 70.0
        assert config.pal_review_enabled is True
        assert config.pal_model == "gpt-5"
        assert config.timeout_seconds is None

    def test_custom_values(self):
        """Should use provided values."""
        config = build_config(
            {
                "max_iterations": 5,
                "quality_threshold": 85.0,
                "pal_review": False,
                "pal_model": "claude-3-opus",
                "timeout_seconds": 120.0,
            }
        )
        assert config.max_iterations == 5
        assert config.quality_threshold == 85.0
        assert config.pal_review_enabled is False
        assert config.pal_model == "claude-3-opus"
        assert config.timeout_seconds == 120.0

    def test_hard_max_still_enforced(self):
        """max_iterations should still be capped by hard_max."""
        config = build_config({"max_iterations": 100})
        assert config.max_iterations == 5  # Capped by LoopConfig.__post_init__


class TestCreateMockSkillInvoker:
    """Tests for create_mock_skill_invoker()."""

    def test_returns_callable(self):
        """Should return a callable."""
        invoker = create_mock_skill_invoker({"task": "test"})
        assert callable(invoker)

    def test_returns_signal_structure(self):
        """Should return a signal structure for Claude Code."""
        invoker = create_mock_skill_invoker({"task": "implement"})
        result = invoker({"task": "implement"})
        assert result["signal"] == "invoke_skill"
        assert result["skill"] == "sc-implement"
        assert result["iteration"] == 0

    def test_iteration_increments(self):
        """Iteration should increment on each call."""
        invoker = create_mock_skill_invoker({})
        r1 = invoker({})
        r2 = invoker({})
        r3 = invoker({})
        assert r1["iteration"] == 0
        assert r2["iteration"] == 1
        assert r3["iteration"] == 2

    def test_context_passed_through(self):
        """Context should be passed through in the result."""
        invoker = create_mock_skill_invoker({})
        ctx = {"task": "implement", "improvements_needed": ["Fix lint"]}
        result = invoker(ctx)
        assert result["context"] == ctx

    def test_instruction_includes_improvements(self):
        """Instruction should include improvements when present."""
        invoker = create_mock_skill_invoker({})
        result = invoker({"improvements_needed": ["Add tests"]})
        assert "Add tests" in result["instruction"]

    def test_default_evidence_fields(self):
        """Should include default empty evidence fields."""
        invoker = create_mock_skill_invoker({})
        result = invoker({})
        assert result["changes"] == []
        assert result["tests"] == {"ran": False}
        assert result["lint"] == {"ran": False}
        assert result["changed_files"] == []


class TestCreateSignalOnlyResponse:
    """Tests for create_signal_only_response()."""

    def test_basic_structure(self):
        """Should have the expected structure."""
        result = create_signal_only_response({})
        assert result["action"] == "execute_loop"
        assert "instruction" in result
        assert "safety" in result

    def test_defaults(self):
        """Should use defaults when no context values provided."""
        result = create_signal_only_response({})
        assert result["max_iterations"] == 3
        assert result["quality_threshold"] == 70.0
        assert result["pal_review"] is True

    def test_custom_values(self):
        """Should use provided context values."""
        result = create_signal_only_response(
            {
                "max_iterations": 5,
                "quality_threshold": 80.0,
                "pal_review": False,
            }
        )
        assert result["max_iterations"] == 5
        assert result["quality_threshold"] == 80.0
        assert result["pal_review"] is False

    def test_hard_max_in_safety(self):
        """Safety dict should include hard_max_iterations=5."""
        result = create_signal_only_response({})
        assert result["safety"]["hard_max_iterations"] == 5

    def test_no_oscillation_stagnation_in_safety(self):
        """Safety dict should NOT contain oscillation/stagnation keys."""
        result = create_signal_only_response({})
        assert "detect_oscillation" not in result["safety"]
        assert "detect_stagnation" not in result["safety"]


class TestRunLoop:
    """Tests for run_loop()."""

    def test_returns_dict(self):
        """Should return a dict result."""
        result = run_loop({"task": "implement feature"})
        assert isinstance(result, dict)

    def test_contains_loop_completed(self):
        """Result should contain loop_completed key."""
        result = run_loop({"task": "implement"})
        assert "loop_completed" in result

    def test_contains_termination_reason(self):
        """Result should contain termination_reason key."""
        result = run_loop({"task": "implement"})
        assert "termination_reason" in result

    def test_respects_max_iterations(self):
        """Result iterations should not exceed max_iterations."""
        result = run_loop({"task": "implement", "max_iterations": 2})
        assert result["iterations"] <= 2

    def test_fallback_when_core_unavailable(self):
        """Should return fallback when core module not available."""
        import loop_entry

        original_orchestrator = loop_entry.LoopOrchestrator
        try:
            loop_entry.LoopOrchestrator = None
            result = run_loop({"task": "implement"})
            assert result["error"] == "core module not available"
            assert result["fallback"] is True
            assert "signal" in result
        finally:
            loop_entry.LoopOrchestrator = original_orchestrator
