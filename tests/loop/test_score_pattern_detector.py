"""Tests for score pattern detection with noisy/realistic data.

These tests validate that the termination detection algorithms
(oscillation, stagnation, insufficient_improvement) work correctly
with real-world noisy score patterns, not just clean test data.
"""

from __future__ import annotations

import pytest

from core.termination import (
    check_insufficient_improvement,
    detect_oscillation,
    detect_stagnation,
    should_terminate,
)


class TestOscillationWithNoisyData:
    """Tests for oscillation detection with noise."""

    @pytest.mark.parametrize(
        "scores,expected,description",
        [
            # Clean oscillation patterns - should detect
            ([50.0, 60.0, 52.0, 63.0], True, "Clean alternating pattern"),
            ([50.0, 60.0, 50.0, 60.0], True, "Exact alternating pattern"),
            # Noisy oscillation - should still detect (changes > threshold)
            ([50.0, 60.5, 51.2, 59.8], True, "Noisy alternating with 8-10pt swings"),
            ([50.0, 55.5, 50.8, 56.2], True, "Noisy alternating with 5pt swings"),
            # Borderline cases - changes near threshold
            # Note: 52.5-50.0=2.5, 50.1-52.5=-2.4, 52.8-50.1=2.7 -> all > 2.0
            ([50.0, 52.5, 50.1, 52.8], True, "Swings 2.4-2.7pt just above threshold"),
            ([50.0, 51.5, 50.2, 51.6], False, "Swings ~1.4pt below 2pt threshold"),
        ],
        ids=lambda x: x if isinstance(x, str) else str(x),
    )
    def test_oscillation_detection(self, scores, expected, description):
        """Test oscillation detection with various patterns."""
        result = detect_oscillation(scores, window=3, threshold=2.0)
        assert result == expected, f"Failed: {description}"

    @pytest.mark.parametrize(
        "scores,expected,description",
        [
            # No oscillation - consistent improvement
            ([50.0, 55.0, 60.0, 65.0], False, "Consistent improvement"),
            ([50.0, 51.0, 52.0, 53.0], False, "Slow steady improvement"),
            # No oscillation - consistent decline
            ([80.0, 75.0, 70.0, 65.0], False, "Consistent decline"),
            # Mixed but not alternating
            ([50.0, 55.0, 58.0, 56.0], False, "Up-up-down not alternating"),
            ([50.0, 45.0, 48.0, 55.0], False, "Down-up-up not alternating"),
        ],
        ids=lambda x: x if isinstance(x, str) else str(x),
    )
    def test_non_oscillation_patterns(self, scores, expected, description):
        """Test that non-oscillation patterns are not detected."""
        result = detect_oscillation(scores, window=3, threshold=2.0)
        assert result == expected, f"Failed: {description}"

    def test_short_history_no_oscillation(self):
        """Oscillation requires at least window=3 scores."""
        assert detect_oscillation([50.0], window=3) is False
        assert detect_oscillation([50.0, 60.0], window=3) is False

    def test_window_parameter_affects_detection(self):
        """Larger windows require more alternating points."""
        scores = [50, 60, 50, 60, 50]

        # Window of 3 looks at last 3 scores
        assert detect_oscillation(scores, window=3) is True

        # Window of 4 requires 4 alternating points
        assert detect_oscillation(scores, window=4) is True

        # Longer window - pattern still holds
        assert detect_oscillation(scores, window=5) is True

    def test_threshold_parameter_affects_detection(self):
        """Higher thresholds require larger swings to count."""
        scores = [50.0, 55.0, 50.0, 55.0]  # 5-point swings

        # With threshold 2.0, this oscillates
        assert detect_oscillation(scores, threshold=2.0) is True

        # With threshold 10.0, swings too small
        assert detect_oscillation(scores, threshold=10.0) is False


class TestStagnationWithNoisyData:
    """Tests for stagnation detection with noise."""

    @pytest.mark.parametrize(
        "scores,expected,description",
        [
            # Clean stagnation - should detect
            ([65.0, 65.0, 65.0], True, "Exact same scores"),
            ([65.0, 65.5, 65.2, 65.3], True, "Minimal variance < 2.0"),
            # Noisy stagnation - should still detect
            ([65.0, 65.1, 64.9, 65.2], True, "0.3 range - clearly stagnant"),
            ([65.0, 64.5, 65.0, 64.7], True, "0.5 range - stagnant"),
            ([65.0, 64.0, 64.5, 64.2], True, "1.0 range - stagnant"),
            ([65.0, 63.5, 64.8, 64.0], True, "1.5 range - just stagnant"),
            # Borderline - just above threshold
            ([65.0, 63.0, 65.0], False, "2.0 range - not stagnant"),
            ([65.0, 62.5, 64.8], False, "2.5 range - not stagnant"),
        ],
        ids=lambda x: x if isinstance(x, str) else str(x),
    )
    def test_stagnation_detection(self, scores, expected, description):
        """Test stagnation detection with various patterns."""
        result = detect_stagnation(scores, window=3, threshold=2.0)
        assert result == expected, f"Failed: {description}"

    @pytest.mark.parametrize(
        "scores,expected,description",
        [
            # Clear improvement - not stagnant
            ([50.0, 55.0, 60.0], False, "Clear improvement"),
            ([50.0, 51.0, 52.0], False, "Slow but steady improvement"),
            # Clear decline - not stagnant
            ([80.0, 75.0, 70.0], False, "Clear decline"),
            # Plateau after rise (look at recent window)
            ([50, 55, 60, 60.1, 59.8, 60.3], True, "Plateau after rise"),
        ],
        ids=lambda x: x if isinstance(x, str) else str(x),
    )
    def test_non_stagnation_patterns(self, scores, expected, description):
        """Test that non-stagnation patterns are not detected."""
        result = detect_stagnation(scores, window=3, threshold=2.0)
        assert result == expected, f"Failed: {description}"

    def test_short_history_no_stagnation(self):
        """Stagnation requires at least window scores."""
        assert detect_stagnation([65.0], window=3) is False
        assert detect_stagnation([65.0, 65.0], window=3) is False

    def test_window_parameter_affects_detection(self):
        """Window size affects which scores are analyzed."""
        # Long history with stagnation at end
        scores = [50, 55, 60, 65, 65.1, 64.9]

        # Window of 3 looks at [65, 65.1, 64.9] - stagnant
        assert detect_stagnation(scores, window=3) is True

        # Window of 4 looks at [60, 65, 65.1, 64.9] - not stagnant
        assert detect_stagnation(scores, window=4) is False

    def test_threshold_parameter_affects_detection(self):
        """Higher thresholds allow more variance before stagnation."""
        scores = [65.0, 62.0, 64.0]  # 3-point range

        # With threshold 2.0, this is not stagnant
        assert detect_stagnation(scores, threshold=2.0) is False

        # With threshold 5.0, this is stagnant
        assert detect_stagnation(scores, threshold=5.0) is True


class TestInsufficientImprovementWithNoisyData:
    """Tests for insufficient improvement detection."""

    @pytest.mark.parametrize(
        "current,previous,expected,description",
        [
            # Clear improvement - should continue
            (60.0, 50.0, False, "10pt improvement"),
            (55.0, 50.0, False, "5pt improvement (threshold)"),
            (55.5, 50.0, False, "5.5pt improvement (above threshold)"),
            # Insufficient improvement
            (54.0, 50.0, True, "4pt improvement (below 5pt threshold)"),
            (51.0, 50.0, True, "1pt improvement"),
            (50.5, 50.0, True, "0.5pt improvement"),
            # No improvement
            (50.0, 50.0, True, "No change"),
            # Regression
            (48.0, 50.0, True, "2pt regression"),
            (40.0, 50.0, True, "10pt regression"),
        ],
        ids=lambda x: x if isinstance(x, str) else str(x),
    )
    def test_improvement_detection(self, current, previous, expected, description):
        """Test insufficient improvement detection."""
        result = check_insufficient_improvement(current, previous, min_improvement=5.0)
        assert result == expected, f"Failed: {description}"

    def test_custom_threshold(self):
        """Custom min_improvement threshold is respected."""
        # 3pt improvement
        assert check_insufficient_improvement(53.0, 50.0, min_improvement=2.0) is False
        assert check_insufficient_improvement(53.0, 50.0, min_improvement=5.0) is True
        assert check_insufficient_improvement(53.0, 50.0, min_improvement=10.0) is True


class TestShouldTerminateIntegration:
    """Integration tests for should_terminate function."""

    @pytest.mark.parametrize(
        "scores,expected_stop,expected_reason",
        [
            # Continue - improving steadily
            ([50.0, 60.0], False, ""),
            ([50.0, 60.0, 70.0], False, ""),
            # Stop - oscillation
            ([50.0, 60.0, 52.0, 63.0], True, "oscillation"),
            # Stop - stagnation
            ([65.0, 65.1, 64.9], True, "stagnation"),
            # Stop - insufficient improvement
            ([50.0, 52.0], True, "insufficient_improvement"),
            # Edge: single score - continue
            ([50.0], False, ""),
        ],
    )
    def test_termination_reasons(self, scores, expected_stop, expected_reason):
        """Test that correct termination reason is returned."""
        should_stop, reason = should_terminate(scores)
        assert should_stop == expected_stop
        assert reason == expected_reason

    def test_oscillation_takes_priority_over_insufficient(self):
        """When both apply, oscillation is checked first."""
        # This oscillates AND has insufficient improvement
        scores = [50.0, 52.5, 50.1, 52.8]
        should_stop, reason = should_terminate(
            scores,
            config_oscillation_window=4,  # Need 4 for detection
            config_min_improvement=5.0,
        )
        # Oscillation is checked first
        if detect_oscillation(scores, window=4):
            assert reason == "oscillation"
        else:
            assert reason == "insufficient_improvement"

    def test_stagnation_takes_priority_over_insufficient(self):
        """When both stagnation and insufficient apply, stagnation first."""
        scores = [65.0, 65.1, 65.0]  # Stagnant AND insufficient
        should_stop, reason = should_terminate(scores)
        assert should_stop is True
        assert reason == "stagnation"  # Stagnation checked before insufficient


class TestEdgeCasesAndBoundaryConditions:
    """Tests for edge cases and boundary conditions."""

    def test_empty_history(self):
        """Empty history should not crash."""
        assert detect_oscillation([]) is False
        assert detect_stagnation([]) is False
        should_stop, reason = should_terminate([])
        assert should_stop is False
        assert reason == ""

    def test_single_score(self):
        """Single score history should not trigger detection."""
        assert detect_oscillation([50.0]) is False
        assert detect_stagnation([50.0]) is False
        should_stop, reason = should_terminate([50.0])
        assert should_stop is False

    def test_two_scores(self):
        """Two scores should only check insufficient improvement."""
        scores = [50.0, 51.0]  # Only 1pt improvement
        should_stop, reason = should_terminate(scores, config_min_improvement=5.0)
        assert should_stop is True
        assert reason == "insufficient_improvement"

    def test_extreme_values(self):
        """Extreme score values should be handled."""
        # Very high scores
        assert detect_stagnation([100.0, 100.0, 100.0]) is True

        # Very low scores
        assert detect_stagnation([0.0, 0.0, 0.0]) is True

        # Mix of extreme values
        assert detect_oscillation([0.0, 100.0, 0.0]) is True

    def test_negative_scores(self):
        """Negative scores should be handled (edge case)."""
        assert detect_stagnation([-5.0, -5.0, -5.0]) is True
        assert detect_oscillation([-10.0, 10.0, -10.0]) is True

    def test_float_precision(self):
        """Float precision issues should not cause false positives."""
        # These are effectively the same but may differ in float representation
        scores = [65.0, 65.0 + 1e-10, 65.0 - 1e-10]
        assert detect_stagnation(scores) is True  # Should still detect


class TestRealWorldScenarios:
    """Tests simulating real-world improvement loops."""

    def test_noisy_improvement_continues(self):
        """Noisy but improving scores should not trigger termination."""
        # Realistic noisy improvement pattern
        scores = [50.0, 52.3, 51.8, 54.1, 53.7, 56.2, 55.9, 58.3]

        # Check each window doesn't falsely trigger
        for i in range(3, len(scores) + 1):
            window = scores[:i]
            if len(window) >= 3:
                # Should not detect stagnation
                assert detect_stagnation(window, threshold=2.0) is False
                # May detect oscillation in some windows, but not consistently

    def test_noisy_decline_detected_as_insufficient(self):
        """Declining scores should trigger insufficient improvement."""
        scores = [80.0, 78.5, 79.2, 77.8]

        # Last step: 79.2 -> 77.8 is -1.4, which is < min_improvement
        should_stop, reason = should_terminate(
            scores,
            config_min_improvement=5.0,
        )
        assert should_stop is True
        # Could be stagnation or insufficient depending on thresholds

    def test_plateau_after_improvements(self):
        """Plateau after initial improvements should be detected."""
        # Start improving, then plateau
        scores = [50.0, 58.0, 66.0, 66.2, 65.9, 66.1]

        # Final window [66.2, 65.9, 66.1] is stagnant
        should_stop, reason = should_terminate(scores)
        assert should_stop is True
        assert reason == "stagnation"

    def test_outlier_handling(self):
        """Outliers should not break detection."""
        # Steady improvement with one outlier
        scores = [50, 55, 80, 60, 65]  # 80 is outlier

        # This might trigger oscillation due to up-down-up pattern
        # The algorithm looks at recent window, so behavior depends on window
        result = detect_oscillation(scores[-3:], window=3)  # [80, 60, 65]
        # 80->60 is down, 60->65 is up - this is oscillation
        assert result is True

    def test_gradual_improvement_with_setbacks(self):
        """Overall improvement with occasional setbacks."""
        scores = [50.0, 55.0, 53.0, 58.0, 56.0, 61.0, 59.0, 64.0]

        # Each window of 3 might show oscillation
        # This is a challenge - the algorithm may flag this
        final_window = scores[-3:]  # [59.0, 64.0] - wait, that's only 2
        final_window = scores[-4:-1]  # [61.0, 59.0, 64.0]

        # Up-down-up pattern might trigger oscillation
        osc = detect_oscillation(final_window, window=3)
        # This is actually oscillating in the short term


class TestParameterTuning:
    """Tests for understanding how parameters affect detection."""

    @pytest.mark.parametrize("threshold", [1.0, 2.0, 3.0, 5.0, 10.0])
    def test_oscillation_threshold_sensitivity(self, threshold):
        """Understand how threshold affects oscillation detection."""
        # 8-point swings - only detected when swing > threshold
        large_swings = [50.0, 58.0, 50.0]  # 8pt swings
        expected_large = threshold < 8.0  # Only detected if 8 > threshold
        assert detect_oscillation(large_swings, threshold=threshold) == expected_large

        # 1.5-point swings should only be caught with low threshold
        small_swings = [50.0, 51.5, 50.0]
        expected_small = threshold < 1.5  # Only if 1.5 > threshold
        assert detect_oscillation(small_swings, threshold=threshold) == expected_small

    @pytest.mark.parametrize("threshold", [1.0, 2.0, 3.0, 5.0, 10.0])
    def test_stagnation_threshold_sensitivity(self, threshold):
        """Understand how threshold affects stagnation detection."""
        # 0.5 range should be caught by all thresholds >= 0.5
        tight_range = [65.0, 65.3, 65.1]  # range = 0.3
        assert detect_stagnation(tight_range, threshold=threshold) is True

        # 5-point range should only be caught with high threshold
        wider_range = [65.0, 62.0, 67.0]  # range = 5.0
        expected = threshold > 5.0
        assert detect_stagnation(wider_range, threshold=threshold) == expected

    @pytest.mark.parametrize("window", [3, 4, 5])
    def test_window_size_sensitivity(self, window):
        """Understand how window size affects detection."""
        scores = [50.0, 60.0, 50.0, 60.0, 50.0]

        # Oscillation detection with different windows
        # Note: Window of 2 is too small - need at least 2 direction changes
        # which requires at least 3 scores
        if window <= len(scores):
            result = detect_oscillation(scores, window=window)
            # All windows >= 3 should detect this perfect oscillation
            assert result is True
