"""Tests for core/pal_integration.py - PAL MCP integration."""

from core.pal_integration import (
    PALReviewSignal,
    _detect_pattern,
    incorporate_pal_feedback,
)
from core.types import QualityAssessment


class TestPALReviewSignalConstants:
    """Tests for PALReviewSignal class constants."""

    def test_tool_names_defined(self):
        """All PAL MCP tool names should be defined."""
        assert PALReviewSignal.TOOL_CODEREVIEW == "mcp__pal__codereview"
        assert PALReviewSignal.TOOL_DEBUG == "mcp__pal__debug"
        assert PALReviewSignal.TOOL_THINKDEEP == "mcp__pal__thinkdeep"
        assert PALReviewSignal.TOOL_CONSENSUS == "mcp__pal__consensus"


class TestGenerateReviewSignal:
    """Tests for PALReviewSignal.generate_review_signal() method."""

    def test_basic_signal_structure(self):
        """Signal should have required structure."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
        )
        assert signal["action_required"] is True
        assert signal["tool"] == "mcp__pal__codereview"
        assert signal["iteration"] == 0
        assert "instruction" in signal
        assert signal["files"] == ["main.py"]

    def test_context_includes_quality_info(self):
        """Context should include quality assessment info."""
        assessment = QualityAssessment(
            overall_score=55.0,
            passed=False,
            threshold=70.0,
            band="needs_review",
            improvements_needed=["Add tests", "Fix lint"],
        )
        signal = PALReviewSignal.generate_review_signal(
            iteration=1,
            changed_files=["src/app.py"],
            quality_assessment=assessment,
        )
        context = signal["context"]
        assert context["current_score"] == 55.0
        assert context["target_score"] == 70.0
        assert context["quality_band"] == "needs_review"
        assert "Add tests" in context["improvements_needed"]

    def test_auto_review_type_low_score(self):
        """Auto review type should be 'full' for low scores."""
        assessment = QualityAssessment(overall_score=40.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
            review_type="auto",
        )
        assert signal["review_type"] == "full"

    def test_auto_review_type_early_iteration(self):
        """Auto review type should be 'quick' for early iterations with good score."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
            review_type="auto",
        )
        assert signal["review_type"] == "quick"

    def test_auto_review_type_later_iteration(self):
        """Auto review type should be 'full' for later iterations."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=3,
            changed_files=["main.py"],
            quality_assessment=assessment,
            review_type="auto",
        )
        assert signal["review_type"] == "full"

    def test_explicit_review_type(self):
        """Explicit review type should override auto."""
        assessment = QualityAssessment(overall_score=40.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
            review_type="security",
        )
        assert signal["review_type"] == "security"

    def test_custom_model(self):
        """Custom model should be included."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
            model="claude-3-opus",
        )
        assert signal["model"] == "claude-3-opus"

    def test_parameters_for_pal_tool(self):
        """Parameters should be structured for PAL tool invocation."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=2,
            changed_files=["main.py", "utils.py"],
            quality_assessment=assessment,
        )
        params = signal["parameters"]
        assert params["step_number"] == 1
        assert params["total_steps"] == 2
        assert params["next_step_required"] is True
        assert params["relevant_files"] == ["main.py", "utils.py"]


class TestGenerateDebugSignal:
    """Tests for PALReviewSignal.generate_debug_signal() method."""

    def test_basic_debug_signal(self):
        """Debug signal should have required structure."""
        signal = PALReviewSignal.generate_debug_signal(
            iteration=3,
            termination_reason="oscillation",
            score_history=[50.0, 60.0, 52.0, 61.0],
        )
        assert signal["action_required"] is True
        assert signal["tool"] == "mcp__pal__debug"
        assert signal["iteration"] == 3
        assert "oscillation" in signal["instruction"]

    def test_debug_context(self):
        """Debug context should include history and pattern."""
        scores = [50.0, 60.0, 52.0, 61.0]
        signal = PALReviewSignal.generate_debug_signal(
            iteration=3,
            termination_reason="oscillation",
            score_history=scores,
        )
        context = signal["context"]
        assert context["termination_reason"] == "oscillation"
        assert context["score_history"] == scores
        assert "pattern" in context

    def test_debug_parameters(self):
        """Debug parameters should not require next step."""
        signal = PALReviewSignal.generate_debug_signal(
            iteration=3,
            termination_reason="stagnation",
            score_history=[65.0, 65.5, 65.2],
        )
        params = signal["parameters"]
        assert params["next_step_required"] is False
        assert params["total_steps"] == 1


class TestGenerateFinalValidationSignal:
    """Tests for PALReviewSignal.generate_final_validation_signal() method."""

    def test_basic_final_signal(self):
        """Final validation signal should have required structure."""
        assessment = QualityAssessment(overall_score=85.0, passed=True)
        signal = PALReviewSignal.generate_final_validation_signal(
            changed_files=["main.py", "tests/test_main.py"],
            quality_assessment=assessment,
            iteration_count=3,
        )
        assert signal["action_required"] is True
        assert signal["tool"] == "mcp__pal__codereview"
        assert signal["is_final"] is True
        assert signal["review_type"] == "full"

    def test_final_context(self):
        """Final context should include completion info."""
        assessment = QualityAssessment(
            overall_score=85.0,
            passed=True,
            threshold=70.0,
            band="acceptable",
        )
        signal = PALReviewSignal.generate_final_validation_signal(
            changed_files=["main.py"],
            quality_assessment=assessment,
            iteration_count=2,
        )
        context = signal["context"]
        assert context["final_score"] == 85.0
        assert context["threshold"] == 70.0
        assert context["total_iterations"] == 2

    def test_final_parameters(self):
        """Final parameters should not require next step."""
        assessment = QualityAssessment(overall_score=85.0, passed=True)
        signal = PALReviewSignal.generate_final_validation_signal(
            changed_files=["main.py"],
            quality_assessment=assessment,
            iteration_count=2,
        )
        params = signal["parameters"]
        assert params["next_step_required"] is False
        assert params["step_number"] == 2
        assert "Quality score: 85.0" in params["findings"]


class TestDetectPattern:
    """Tests for _detect_pattern helper function."""

    def test_insufficient_data(self):
        """Single score should return insufficient_data."""
        assert _detect_pattern([50.0]) == "insufficient_data"

    def test_empty_list(self):
        """Empty list should return insufficient_data."""
        assert _detect_pattern([]) == "insufficient_data"

    def test_oscillating_pattern(self):
        """Alternating up/down should return oscillating."""
        scores = [50.0, 60.0, 52.0, 63.0]
        assert _detect_pattern(scores) == "oscillating"

    def test_stagnating_pattern(self):
        """Flat scores should return stagnating."""
        scores = [65.0, 65.5, 65.2]
        assert _detect_pattern(scores) == "stagnating"

    def test_improving_pattern(self):
        """Increasing scores should return improving."""
        scores = [50.0, 55.0, 60.0, 65.0]
        assert _detect_pattern(scores) == "improving"

    def test_declining_pattern(self):
        """Decreasing scores should return declining."""
        scores = [70.0, 60.0, 55.0]
        assert _detect_pattern(scores) == "declining"


class TestIncorporatePalFeedback:
    """Tests for incorporate_pal_feedback function."""

    def test_empty_feedback(self):
        """Empty feedback should not modify context."""
        context = {"task": "implement feature"}
        result = incorporate_pal_feedback(context, {})
        assert result["task"] == "implement feature"

    def test_no_issues(self):
        """Feedback without issues should not add improvements."""
        context = {"improvements_needed": []}
        result = incorporate_pal_feedback(context, {"issues_found": []})
        assert result["improvements_needed"] == []

    def test_critical_issues_prepended(self):
        """Critical issues should be prepended to improvements."""
        context = {"improvements_needed": ["Existing issue"]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": "Security vulnerability"},
            ]
        }
        result = incorporate_pal_feedback(context, feedback)
        assert result["improvements_needed"][0] == "Security vulnerability"
        assert "Existing issue" in result["improvements_needed"]

    def test_high_issues_prepended(self):
        """High severity issues should be prepended."""
        context = {"improvements_needed": ["Existing"]}
        feedback = {
            "issues_found": [
                {"severity": "high", "description": "Performance issue"},
            ]
        }
        result = incorporate_pal_feedback(context, feedback)
        assert result["improvements_needed"][0] == "Performance issue"

    def test_medium_issues_appended(self):
        """Medium severity issues should be appended."""
        context = {"improvements_needed": ["Existing"]}
        feedback = {
            "issues_found": [
                {"severity": "medium", "description": "Code style"},
            ]
        }
        result = incorporate_pal_feedback(context, feedback)
        assert result["improvements_needed"][-1] == "Code style"
        assert result["improvements_needed"][0] == "Existing"

    def test_max_10_improvements(self):
        """Improvements should be capped at 10."""
        context = {"improvements_needed": [f"Issue {i}" for i in range(8)]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": f"Critical {i}"} for i in range(5)
            ]
        }
        result = incorporate_pal_feedback(context, feedback)
        assert len(result["improvements_needed"]) == 10

    def test_pal_feedback_stored(self):
        """PAL feedback should be stored in context."""
        context = {}
        feedback = {"tool": "codereview", "score": 80}
        result = incorporate_pal_feedback(context, feedback)
        assert result["pal_feedback"] == feedback

    def test_no_duplicate_issues(self):
        """Duplicate issues should not be added."""
        context = {"improvements_needed": ["Fix bug"]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": "Fix bug"},  # Duplicate
            ]
        }
        result = incorporate_pal_feedback(context, feedback)
        assert result["improvements_needed"].count("Fix bug") == 1
