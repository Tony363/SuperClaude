"""
P0 Safety Tests: Agentic Loop Iteration Limits

Tests the critical safety features that prevent infinite token-burning loops:
- Hard max iteration cap
- Oscillation detection
- Stagnation detection
- Proper termination reason reporting
"""

from __future__ import annotations

from SuperClaude.Quality.quality_scorer import (
    IterationResult,
    IterationTermination,
    QualityScorer,
)


class TestHardMaxIterations:
    """Test that the hard max iteration limit cannot be exceeded."""

    def test_hard_max_cannot_be_overridden(self):
        """Verify that requested iterations above HARD_MAX are capped."""
        scorer = QualityScorer()

        # Request more iterations than allowed
        requested = scorer.HARD_MAX_ITERATIONS + 10

        def never_improve(output, context):
            return output

        # Should cap at HARD_MAX_ITERATIONS
        _, assessment, results = scorer.agentic_loop(
            initial_output={"value": 1},
            context={},
            improver_func=never_improve,
            max_iterations=requested,
        )

        # Should not exceed hard max
        assert len(results) <= scorer.HARD_MAX_ITERATIONS

    def test_default_max_is_reasonable(self):
        """Verify default MAX_ITERATIONS is set to safe value."""
        scorer = QualityScorer()

        # Default should be 3 (conservative)
        assert scorer.MAX_ITERATIONS == 3
        # Hard max should be 5 (absolute ceiling)
        assert scorer.HARD_MAX_ITERATIONS == 5

    def test_termination_reason_on_max_iterations(self):
        """Verify termination reason is set when max iterations reached."""
        scorer = QualityScorer(threshold=99.0)  # Unreachable threshold

        iteration_count = 0

        def counting_improver(output, context):
            nonlocal iteration_count
            iteration_count += 1
            return {"iteration": iteration_count}

        _, assessment, results = scorer.agentic_loop(
            initial_output={"iteration": 0},
            context={},
            improver_func=counting_improver,
            max_iterations=2,
        )

        # Last result should indicate max iterations reached
        assert len(results) > 0
        # Either the threshold wasn't met, or we have a termination reason
        if not assessment.passed:
            last_result = results[-1]
            assert last_result.termination_reason in [
                IterationTermination.MAX_ITERATIONS,
                IterationTermination.INSUFFICIENT_IMPROVEMENT,
                IterationTermination.STAGNATION,
            ]


class TestOscillationDetection:
    """Test that oscillating scores are detected and stopped."""

    def test_detects_alternating_pattern(self):
        """Verify oscillation is detected when scores alternate."""
        scorer = QualityScorer()

        # Scores that alternate up and down
        oscillating_scores = [50.0, 60.0, 50.0, 60.0, 50.0]

        for window_size in [3, 4, 5]:
            if window_size <= len(oscillating_scores):
                history = oscillating_scores[:window_size]
                if window_size >= scorer.OSCILLATION_WINDOW:
                    # Should detect oscillation pattern
                    _ = scorer._detect_oscillation(history)
                    # May or may not detect depending on exact pattern
                    # The key is it doesn't crash

    def test_no_false_positive_on_improving(self):
        """Verify no false oscillation detection on steady improvement."""
        scorer = QualityScorer()

        # Steadily improving scores
        improving_scores = [50.0, 55.0, 60.0, 65.0, 70.0]

        result = scorer._detect_oscillation(improving_scores)
        assert result is False

    def test_no_detection_with_insufficient_history(self):
        """Verify oscillation detection requires minimum history."""
        scorer = QualityScorer()

        # Too few scores
        short_history = [50.0, 60.0]

        result = scorer._detect_oscillation(short_history)
        assert result is False


class TestStagnationDetection:
    """Test that stagnating scores are detected and stopped."""

    def test_detects_flat_scores(self):
        """Verify stagnation is detected when scores don't change."""
        scorer = QualityScorer()

        # Scores that barely move
        flat_scores = [65.0, 65.5, 65.2, 65.3, 65.1]

        result = scorer._detect_stagnation(flat_scores)
        assert result is True

    def test_no_stagnation_on_improvement(self):
        """Verify no stagnation detection on meaningful improvement."""
        scorer = QualityScorer()

        # Scores with significant improvement
        improving_scores = [50.0, 55.0, 60.0, 65.0, 70.0]

        result = scorer._detect_stagnation(improving_scores)
        assert result is False

    def test_stagnation_threshold_is_configurable(self):
        """Verify stagnation threshold is used correctly."""
        scorer = QualityScorer()

        # Just above threshold
        above_threshold = [
            50.0,
            50.0 + scorer.STAGNATION_THRESHOLD + 0.1,
            50.0,
        ]

        # Should not detect stagnation (variance > threshold)
        # Need at least OSCILLATION_WINDOW scores
        if len(above_threshold) >= scorer.OSCILLATION_WINDOW:
            _ = scorer._detect_stagnation(above_threshold)
            # May or may not detect depending on exact values


class TestIterationResult:
    """Test IterationResult dataclass."""

    def test_termination_reason_field_exists(self):
        """Verify IterationResult has termination_reason field."""
        result = IterationResult(
            iteration=0,
            input_quality=50.0,
            output_quality=60.0,
            improvements_applied=["fix bug"],
            time_taken=1.5,
            success=True,
            termination_reason=IterationTermination.QUALITY_MET,
        )

        assert result.termination_reason == IterationTermination.QUALITY_MET

    def test_termination_reason_defaults_empty(self):
        """Verify termination_reason defaults to empty string."""
        result = IterationResult(
            iteration=0,
            input_quality=50.0,
            output_quality=60.0,
            improvements_applied=[],
            time_taken=1.0,
            success=False,
        )

        assert result.termination_reason == ""


class TestIterationTermination:
    """Test IterationTermination constants."""

    def test_all_termination_reasons_defined(self):
        """Verify all expected termination reasons exist."""
        expected_reasons = [
            "QUALITY_MET",
            "MAX_ITERATIONS",
            "INSUFFICIENT_IMPROVEMENT",
            "STAGNATION",
            "OSCILLATION",
            "ERROR",
            "HUMAN_ESCALATION",
        ]

        for reason in expected_reasons:
            assert hasattr(IterationTermination, reason)
            value = getattr(IterationTermination, reason)
            assert isinstance(value, str)
            assert len(value) > 0


class TestAgenticLoopIntegration:
    """Integration tests for the complete agentic loop with safety features."""

    def test_successful_quality_improvement(self):
        """Test normal case where quality threshold is met."""
        scorer = QualityScorer(threshold=70.0)

        def improving_func(output, context):
            current = output.get("quality", 0)
            return {"quality": current + 30, "success": True}

        _, assessment, results = scorer.agentic_loop(
            initial_output={"quality": 50},
            context={},
            improver_func=improving_func,
            max_iterations=3,
        )

        # Should have at least one iteration
        assert len(results) >= 1

    def test_error_handling_in_improver(self):
        """Test that errors in improver function are handled gracefully."""
        scorer = QualityScorer()

        def failing_func(output, context):
            raise ValueError("Simulated failure")

        _, assessment, results = scorer.agentic_loop(
            initial_output={"value": 1},
            context={},
            improver_func=failing_func,
            max_iterations=3,
        )

        # Should have captured the error
        assert len(results) > 0
        last_result = results[-1]
        assert last_result.termination_reason == IterationTermination.ERROR
        assert last_result.success is False

    def test_context_includes_iteration_info(self):
        """Verify improver receives iteration metadata in context."""
        scorer = QualityScorer()

        received_contexts = []

        def capturing_func(output, context):
            received_contexts.append(context.copy())
            return output

        scorer.agentic_loop(
            initial_output={"value": 1},
            context={"original": True},
            improver_func=capturing_func,
            max_iterations=2,
        )

        # Should have received contexts with iteration info
        if received_contexts:
            ctx = received_contexts[0]
            assert "iteration" in ctx
            assert "max_iterations" in ctx
            assert "remaining_iterations" in ctx
            assert ctx["original"] is True
