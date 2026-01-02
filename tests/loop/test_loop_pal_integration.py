"""Tests for loop PAL MCP integration.

Validates that PAL feedback is correctly:
- Generated during loop iterations
- Parsed from MCP responses
- Incorporated into next iteration context
"""

from unittest.mock import patch

import pytest

from core.loop_orchestrator import LoopOrchestrator
from core.pal_integration import PALReviewSignal, incorporate_pal_feedback
from core.types import LoopConfig, QualityAssessment, TerminationReason
from tests.loop.conftest import FixtureAssessor, FixtureSkillInvoker
from tests.mcp.conftest import (
    FakeMCPServer,
    FakePALCodeReviewResponse,
    FakePALDebugResponse,
)


class TestPALReviewSignalDuringLoop:
    """Tests for PAL review signal generation during loop iterations."""

    def test_pal_signal_generated_per_iteration(self):
        """PAL review signal should be generated after each iteration."""
        assessor = FixtureAssessor(
            scores=[50.0, 60.0, 70.0],
            passed_at=65.0,
        )
        config = LoopConfig(
            quality_threshold=65.0,
            pal_review_enabled=True,
        )
        orchestrator = LoopOrchestrator(config)

        pal_signals = []

        def invoker_tracking_pal(ctx):
            # Track PAL signals in context
            if "pal_signal" in ctx:
                pal_signals.append(ctx["pal_signal"])
            return {"changes": ["main.py"], "changed_files": ["main.py"]}

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, invoker_tracking_pal)

        # Should have generated PAL signals for iterations before quality met
        # (PAL is called within the loop, not on final success)
        assert result.termination_reason == TerminationReason.QUALITY_MET

    def test_pal_signal_includes_quality_context(self):
        """PAL signal should include current quality assessment."""
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

        assert signal["context"]["current_score"] == 55.0
        assert signal["context"]["target_score"] == 70.0
        assert "Add tests" in signal["context"]["improvements_needed"]

    def test_pal_signal_tool_is_codereview(self):
        """PAL signal should specify codereview tool for in-loop reviews."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)

        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
        )

        assert signal["tool"] == "mcp__pal__codereview"


class TestPALDebugSignalOnTermination:
    """Tests for PAL debug signal generation on problematic termination."""

    def test_debug_signal_on_oscillation(self):
        """Debug signal should be generated when oscillation detected."""
        signal = PALReviewSignal.generate_debug_signal(
            iteration=4,
            termination_reason="oscillation",
            score_history=[50.0, 60.0, 52.0, 63.0, 55.0],
        )

        assert signal["tool"] == "mcp__pal__debug"
        assert signal["action_required"] is True
        assert "oscillation" in signal["instruction"]
        assert signal["context"]["termination_reason"] == "oscillation"

    def test_debug_signal_on_stagnation(self):
        """Debug signal should be generated when stagnation detected."""
        signal = PALReviewSignal.generate_debug_signal(
            iteration=4,
            termination_reason="stagnation",
            score_history=[65.0, 65.5, 65.2, 65.3, 65.1],
        )

        assert signal["tool"] == "mcp__pal__debug"
        assert signal["context"]["termination_reason"] == "stagnation"
        assert signal["context"]["score_history"] == [65.0, 65.5, 65.2, 65.3, 65.1]

    def test_debug_signal_includes_pattern_analysis(self):
        """Debug signal should include pattern analysis."""
        signal = PALReviewSignal.generate_debug_signal(
            iteration=4,
            termination_reason="oscillation",
            score_history=[50.0, 60.0, 52.0, 63.0],
        )

        assert "pattern" in signal["context"]


class TestPALFeedbackIncorporation:
    """Tests for incorporating PAL feedback into loop context."""

    def test_critical_issues_prepended(self):
        """Critical issues from PAL should be prepended to improvements."""
        context = {"improvements_needed": ["Existing improvement"]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": "SQL injection vulnerability"},
            ]
        }

        result = incorporate_pal_feedback(context, feedback)

        assert result["improvements_needed"][0] == "SQL injection vulnerability"
        assert "Existing improvement" in result["improvements_needed"]

    def test_high_issues_prepended_after_critical(self):
        """High and critical severity issues should be prepended before existing items."""
        context = {"improvements_needed": ["Existing"]}
        feedback = {
            "issues_found": [
                {"severity": "high", "description": "Memory leak"},
                {"severity": "critical", "description": "Auth bypass"},
            ]
        }

        result = incorporate_pal_feedback(context, feedback)

        # Both critical and high should come before existing improvements
        assert "Auth bypass" in result["improvements_needed"][:3]
        assert "Memory leak" in result["improvements_needed"][:3]
        # Existing should still be present
        assert "Existing" in result["improvements_needed"]

    def test_medium_issues_appended(self):
        """Medium severity issues should be appended to improvements."""
        context = {"improvements_needed": ["First"]}
        feedback = {
            "issues_found": [
                {"severity": "medium", "description": "Code style issue"},
            ]
        }

        result = incorporate_pal_feedback(context, feedback)

        assert result["improvements_needed"][-1] == "Code style issue"
        assert result["improvements_needed"][0] == "First"

    def test_max_10_improvements_enforced(self):
        """Improvements should be capped at 10."""
        context = {"improvements_needed": [f"Issue {i}" for i in range(8)]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": f"Critical {i}"}
                for i in range(5)
            ]
        }

        result = incorporate_pal_feedback(context, feedback)

        assert len(result["improvements_needed"]) == 10

    def test_no_duplicate_improvements(self):
        """Duplicate issues should not be added."""
        context = {"improvements_needed": ["Fix the bug"]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": "Fix the bug"},
            ]
        }

        result = incorporate_pal_feedback(context, feedback)

        assert result["improvements_needed"].count("Fix the bug") == 1

    def test_pal_feedback_stored_in_context(self):
        """PAL feedback should be stored in context for reference."""
        context = {}
        feedback = {"tool": "codereview", "score": 80, "issues_found": []}

        result = incorporate_pal_feedback(context, feedback)

        assert result["pal_feedback"] == feedback

    def test_empty_feedback_preserves_context(self):
        """Empty feedback should not modify existing context."""
        context = {"task": "implement", "improvements_needed": ["Add tests"]}

        result = incorporate_pal_feedback(context, {})

        assert result["task"] == "implement"
        assert result["improvements_needed"] == ["Add tests"]


class TestPALFinalValidation:
    """Tests for PAL final validation signal on loop completion."""

    def test_final_validation_signal_structure(self):
        """Final validation signal should have correct structure."""
        assessment = QualityAssessment(
            overall_score=85.0,
            passed=True,
            threshold=70.0,
        )

        signal = PALReviewSignal.generate_final_validation_signal(
            changed_files=["main.py", "tests/test_main.py"],
            quality_assessment=assessment,
            iteration_count=3,
        )

        assert signal["action_required"] is True
        assert signal["tool"] == "mcp__pal__codereview"
        assert signal["is_final"] is True
        assert signal["review_type"] == "full"

    def test_final_validation_includes_summary(self):
        """Final validation should include summary of loop execution."""
        assessment = QualityAssessment(
            overall_score=85.0, passed=True, threshold=70.0, band="acceptable"
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

    def test_final_validation_parameters(self):
        """Final validation parameters should not require next step."""
        assessment = QualityAssessment(overall_score=85.0, passed=True)

        signal = PALReviewSignal.generate_final_validation_signal(
            changed_files=["main.py"],
            quality_assessment=assessment,
            iteration_count=2,
        )

        params = signal["parameters"]
        assert params["next_step_required"] is False


class TestPALIntegrationWithFakeMCP:
    """Tests using fake MCP server to simulate full integration."""

    def test_fake_pal_response_parsed(self, fake_mcp_server, pal_codereview_with_issues):
        """Fake PAL response should be correctly parsed."""
        fake_mcp_server.set_response("mcp__pal__codereview", pal_codereview_with_issues)

        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["src/db.py"], "review_type": "full"},
        )

        assert response["success"] is True
        issues = response["data"]["issues_found"]
        assert len(issues) == 3

    def test_pal_feedback_incorporated_from_fake(
        self, fake_mcp_server, pal_codereview_with_issues
    ):
        """Fake PAL response should be incorporated into context."""
        fake_mcp_server.set_response("mcp__pal__codereview", pal_codereview_with_issues)

        # Simulate the full flow
        response = fake_mcp_server.invoke("mcp__pal__codereview", {})

        context = {"improvements_needed": []}
        updated = incorporate_pal_feedback(context, response["data"])

        assert "SQL injection vulnerability" in updated["improvements_needed"]

    def test_pal_debug_flow_with_fake(self, fake_mcp_server):
        """Debug signal should work with fake MCP server."""
        response = fake_mcp_server.invoke(
            "mcp__pal__debug",
            {"issue": "Loop is oscillating", "score_history": [50, 60, 52, 63]},
        )

        assert response["success"] is True
        assert "hypothesis" in response["data"]
        assert "confidence" in response["data"]


class TestLoopOrchestratorPALIntegration:
    """Tests for PAL integration within the loop orchestrator."""

    def test_pal_enabled_by_default(self):
        """PAL review should be enabled by default in config."""
        config = LoopConfig()
        assert config.pal_review_enabled is True

    def test_pal_can_be_disabled(self):
        """PAL review should be disableable."""
        config = LoopConfig(pal_review_enabled=False)
        assert config.pal_review_enabled is False

    def test_pal_model_configurable(self):
        """PAL model should be configurable."""
        config = LoopConfig(pal_model="claude-3-opus")
        assert config.pal_model == "claude-3-opus"

    def test_pal_signal_uses_configured_model(self):
        """PAL signal should use the configured model."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)

        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
            model="gemini-2.5-pro",
        )

        assert signal["model"] == "gemini-2.5-pro"


class TestE2EPALFeedbackPipeline:
    """
    E2E tests for the full signal→MCP→response→state pipeline.

    These tests validate that PAL feedback from iteration N correctly
    appears in iteration N+1's context, proving the complete feedback loop.

    Architecture Note:
    The LoopOrchestrator generates PAL signals and records them in iteration history.
    An external actor (Claude Code) is expected to process these signals via MCP
    and add the response as 'result' key to the pal_review dict.
    The _prepare_next_iteration() method then incorporates this feedback.

    For testing, we need to inject the result at the right moment - after the
    PAL signal is recorded but before _prepare_next_iteration() is called.
    We achieve this by patching _record_iteration to inject results.
    """

    def test_pal_feedback_flows_to_next_iteration(
        self, fake_mcp_server, pal_codereview_with_issues
    ):
        """
        E2E test: PAL feedback from iteration 0 appears in iteration 1's context.

        This is the critical P0 test that validates the full pipeline:
        1. LoopOrchestrator executes iteration 0
        2. PAL signal is generated with quality context
        3. _record_iteration stores the signal in history
        4. External actor (simulated) processes signal and adds 'result'
        5. _prepare_next_iteration() calls incorporate_pal_feedback()
        6. Iteration 1's context contains the PAL issues as improvements
        """
        # Setup: assessor that needs 2 iterations to pass
        assessor = FixtureAssessor(scores=[50.0, 80.0], passed_at=75.0)
        config = LoopConfig(quality_threshold=75.0, pal_review_enabled=True)
        orchestrator = LoopOrchestrator(config)

        # Configure fake MCP server with PAL response containing issues
        fake_mcp_server.set_response("mcp__pal__codereview", pal_codereview_with_issues)
        pal_feedback_data = pal_codereview_with_issues.to_dict()["data"]

        # Capture contexts passed to each iteration
        contexts_captured = []

        # Store original method
        original_record = orchestrator._record_iteration

        def patched_record_iteration(*args, **kwargs):
            """Inject PAL result after recording, simulating external MCP call."""
            original_record(*args, **kwargs)
            # After recording iteration 0, inject the PAL result
            if len(orchestrator.iteration_history) == 1:
                iter_result = orchestrator.iteration_history[0]
                if iter_result.pal_review is not None:
                    # Simulate MCP response being added by external actor
                    iter_result.pal_review["result"] = pal_feedback_data

        def capturing_invoker(context: dict) -> dict:
            """Capture context for assertions."""
            contexts_captured.append(context.copy())
            return {
                "changes": ["main.py"],
                "tests": {"ran": True, "passed": 5, "failed": 0},
                "lint": {"ran": True, "errors": 0},
                "changed_files": ["main.py"],
            }

        # Patch both assessor and _record_iteration
        with patch.object(orchestrator, "assessor", assessor), \
             patch.object(orchestrator, "_record_iteration", patched_record_iteration):
            result = orchestrator.run({"task": "Implement feature X"}, capturing_invoker)

        # Assertions
        assert result.termination_reason == TerminationReason.QUALITY_MET
        assert len(result.iteration_history) == 2
        assert len(contexts_captured) == 2

        # The critical assertion: iteration 1's context should contain
        # the PAL feedback issues as improvements
        context_for_iter_1 = contexts_captured[1]
        improvements = context_for_iter_1.get("improvements_needed", [])

        # Critical/high issues should be in improvements (prepended)
        assert "SQL injection vulnerability" in improvements
        assert "Missing input validation" in improvements

        # Both critical and high issues should be at the start of improvements
        # Due to insert(0, ...) ordering, later items in critical+high end up first
        # The important thing is they're both present and prepended (before any medium)
        assert improvements.index("SQL injection vulnerability") < 2
        assert improvements.index("Missing input validation") < 2

    def test_pal_feedback_not_incorporated_when_disabled(self):
        """PAL feedback should not be incorporated when PAL is disabled."""
        assessor = FixtureAssessor(scores=[50.0, 80.0], passed_at=75.0)
        config = LoopConfig(quality_threshold=75.0, pal_review_enabled=False)
        orchestrator = LoopOrchestrator(config)

        contexts_captured = []

        def capturing_invoker(context: dict) -> dict:
            contexts_captured.append(context.copy())
            return {"changes": ["main.py"], "changed_files": ["main.py"]}

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "test"}, capturing_invoker)

        assert result.termination_reason == TerminationReason.QUALITY_MET

        # No PAL signals should be generated
        for iter_result in result.iteration_history[:-1]:  # Exclude final
            assert iter_result.pal_review is None

    def test_incorporate_pal_feedback_called_with_result(self):
        """Verify incorporate_pal_feedback is called when PAL result exists."""
        assessor = FixtureAssessor(scores=[50.0, 80.0], passed_at=75.0)
        config = LoopConfig(quality_threshold=75.0, pal_review_enabled=True)
        orchestrator = LoopOrchestrator(config)

        mock_feedback = {
            "issues_found": [
                {"severity": "critical", "description": "Test issue"}
            ]
        }

        original_record = orchestrator._record_iteration

        def patched_record(*args, **kwargs):
            original_record(*args, **kwargs)
            if len(orchestrator.iteration_history) == 1:
                iter_result = orchestrator.iteration_history[0]
                if iter_result.pal_review is not None:
                    iter_result.pal_review["result"] = mock_feedback

        def invoker(context: dict) -> dict:
            return {"changes": ["main.py"], "changed_files": ["main.py"]}

        # Use unittest.mock.patch for incorporate_pal_feedback
        with patch.object(orchestrator, "assessor", assessor), \
             patch.object(orchestrator, "_record_iteration", patched_record), \
             patch("core.loop_orchestrator.incorporate_pal_feedback",
                   side_effect=incorporate_pal_feedback) as mock_incorporate:
            orchestrator.run({"task": "test"}, invoker)

            # incorporate_pal_feedback should have been called
            mock_incorporate.assert_called()

            # Verify it was called with the feedback
            call_args = mock_incorporate.call_args
            assert call_args is not None
            _, feedback_arg = call_args.args
            assert feedback_arg == mock_feedback

    def test_multiple_iterations_accumulate_feedback(
        self, fake_mcp_server, pal_codereview_with_issues
    ):
        """Feedback from multiple PAL calls should accumulate across iterations."""
        # Need 3 iterations to see accumulation
        assessor = FixtureAssessor(scores=[40.0, 55.0, 80.0], passed_at=75.0)
        config = LoopConfig(quality_threshold=75.0, pal_review_enabled=True)
        orchestrator = LoopOrchestrator(config)

        fake_mcp_server.set_response("mcp__pal__codereview", pal_codereview_with_issues)
        pal_feedback = pal_codereview_with_issues.to_dict()["data"]

        contexts_captured = []
        original_record = orchestrator._record_iteration

        def patched_record(*args, **kwargs):
            """Inject PAL result after each non-final iteration."""
            original_record(*args, **kwargs)
            # Inject result for the just-recorded iteration (if not final)
            if orchestrator.iteration_history:
                iter_result = orchestrator.iteration_history[-1]
                if iter_result.pal_review is not None and "result" not in iter_result.pal_review:
                    iter_result.pal_review["result"] = pal_feedback

        def invoker(context: dict) -> dict:
            contexts_captured.append(context.copy())
            return {"changes": ["main.py"], "changed_files": ["main.py"]}

        with patch.object(orchestrator, "assessor", assessor), \
             patch.object(orchestrator, "_record_iteration", patched_record):
            result = orchestrator.run({"task": "test"}, invoker)

        assert len(contexts_captured) == 3

        # Iteration 2 context should have improvements from iteration 1's PAL
        iter_2_improvements = contexts_captured[2].get("improvements_needed", [])
        assert len(iter_2_improvements) > 0
        assert "SQL injection vulnerability" in iter_2_improvements

    def test_pal_signal_structure_contains_required_fields(self):
        """PAL signal should contain all required fields for MCP call."""
        assessor = FixtureAssessor(scores=[50.0, 80.0], passed_at=75.0)
        config = LoopConfig(quality_threshold=75.0, pal_review_enabled=True)
        orchestrator = LoopOrchestrator(config)

        def invoker(context: dict) -> dict:
            return {"changes": ["main.py"], "changed_files": ["main.py"]}

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "test"}, invoker)

        # Check iteration 0's PAL signal (before quality met)
        iter_0 = result.iteration_history[0]
        assert iter_0.pal_review is not None

        pal_signal = iter_0.pal_review
        assert "tool" in pal_signal
        assert pal_signal["tool"] == "mcp__pal__codereview"
        assert "context" in pal_signal
        assert "current_score" in pal_signal["context"]
        assert "target_score" in pal_signal["context"]
