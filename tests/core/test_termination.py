"""Tests for core/termination.py - Loop termination detection."""

from core.termination import (
    check_insufficient_improvement,
    detect_oscillation,
    detect_stagnation,
    should_terminate,
)


class TestDetectOscillation:
    """Tests for detect_oscillation function."""

    def test_empty_history_no_oscillation(self):
        """Empty history should not trigger oscillation."""
        assert detect_oscillation([]) is False

    def test_single_score_no_oscillation(self):
        """Single score should not trigger oscillation."""
        assert detect_oscillation([50.0]) is False

    def test_two_scores_no_oscillation(self):
        """Two scores should not trigger oscillation (below window)."""
        assert detect_oscillation([50.0, 60.0]) is False

    def test_monotonic_increase_no_oscillation(self):
        """Monotonically increasing scores should not oscillate."""
        scores = [50.0, 55.0, 60.0, 65.0, 70.0]
        assert detect_oscillation(scores) is False

    def test_monotonic_decrease_no_oscillation(self):
        """Monotonically decreasing scores should not oscillate."""
        scores = [70.0, 65.0, 60.0, 55.0, 50.0]
        assert detect_oscillation(scores) is False

    def test_clear_oscillation(self):
        """Clear up/down/up pattern should trigger oscillation."""
        scores = [50.0, 60.0, 55.0, 62.0]  # Up, down, up
        assert detect_oscillation(scores) is True

    def test_oscillation_with_larger_window(self):
        """Oscillation should be detected with default window=3."""
        scores = [50.0, 60.0, 52.0, 63.0, 54.0]
        assert detect_oscillation(scores, window=3) is True

    def test_small_changes_not_oscillation(self):
        """Changes below threshold should not count as oscillation."""
        scores = [50.0, 51.0, 50.5, 51.5]  # Changes < 2.0
        assert detect_oscillation(scores, threshold=2.0) is False

    def test_oscillation_at_boundary(self):
        """Changes at exactly threshold should count."""
        scores = [50.0, 53.0, 50.0, 53.0]  # Exactly 3.0 changes
        assert detect_oscillation(scores, threshold=2.0) is True

    def test_custom_window(self):
        """Custom window size should be respected."""
        scores = [50.0, 60.0, 55.0]
        assert detect_oscillation(scores, window=4) is False  # Not enough data
        assert detect_oscillation(scores, window=3) is True


class TestDetectStagnation:
    """Tests for detect_stagnation function."""

    def test_empty_history_no_stagnation(self):
        """Empty history should not trigger stagnation."""
        assert detect_stagnation([]) is False

    def test_single_score_no_stagnation(self):
        """Single score should not trigger stagnation."""
        assert detect_stagnation([50.0]) is False

    def test_two_scores_no_stagnation(self):
        """Two scores below window should not trigger stagnation."""
        assert detect_stagnation([50.0, 50.5]) is False

    def test_flat_scores_stagnation(self):
        """Identical scores should trigger stagnation."""
        scores = [65.0, 65.0, 65.0]
        assert detect_stagnation(scores) is True

    def test_near_flat_scores_stagnation(self):
        """Scores within threshold should trigger stagnation."""
        scores = [65.0, 65.5, 64.8]  # Range < 2.0
        assert detect_stagnation(scores, threshold=2.0) is True

    def test_improving_scores_no_stagnation(self):
        """Improving scores should not trigger stagnation."""
        scores = [50.0, 55.0, 60.0]
        assert detect_stagnation(scores) is False

    def test_high_variance_no_stagnation(self):
        """High variance scores should not trigger stagnation."""
        scores = [50.0, 60.0, 55.0]  # Range = 10.0
        assert detect_stagnation(scores, threshold=2.0) is False

    def test_custom_threshold(self):
        """Custom threshold should be respected."""
        scores = [65.0, 66.5, 65.5]  # Range = 1.5
        assert detect_stagnation(scores, threshold=1.0) is False  # 1.5 > 1.0
        assert detect_stagnation(scores, threshold=2.0) is True  # 1.5 < 2.0

    def test_only_uses_recent_scores(self):
        """Only recent scores within window should be checked."""
        scores = [10.0, 20.0, 65.0, 65.5, 65.2]  # Last 3 are stagnant
        assert detect_stagnation(scores, window=3) is True


class TestCheckInsufficientImprovement:
    """Tests for check_insufficient_improvement function."""

    def test_large_improvement_sufficient(self):
        """Large improvement should not trigger insufficient."""
        assert check_insufficient_improvement(70.0, 50.0) is False  # +20

    def test_exact_min_improvement_sufficient(self):
        """Improvement at exactly min should not trigger."""
        assert check_insufficient_improvement(55.0, 50.0, min_improvement=5.0) is False

    def test_small_improvement_insufficient(self):
        """Small improvement should trigger insufficient."""
        assert check_insufficient_improvement(52.0, 50.0, min_improvement=5.0) is True

    def test_no_improvement_insufficient(self):
        """No improvement should trigger insufficient."""
        assert check_insufficient_improvement(50.0, 50.0) is True

    def test_negative_improvement_insufficient(self):
        """Negative improvement (regression) should trigger."""
        assert check_insufficient_improvement(45.0, 50.0) is True

    def test_custom_min_improvement(self):
        """Custom min_improvement should be respected."""
        # 3 point improvement
        assert check_insufficient_improvement(53.0, 50.0, min_improvement=2.0) is False
        assert check_insufficient_improvement(53.0, 50.0, min_improvement=5.0) is True


class TestShouldTerminate:
    """Tests for should_terminate composite function."""

    def test_single_score_no_termination(self):
        """Single score should not trigger termination."""
        should_stop, reason = should_terminate([50.0])
        assert should_stop is False
        assert reason == ""

    def test_insufficient_improvement_termination(self):
        """Insufficient improvement should terminate."""
        should_stop, reason = should_terminate(
            [50.0, 52.0],  # Only +2
            config_min_improvement=5.0,
        )
        assert should_stop is True
        assert reason == "insufficient_improvement"

    def test_oscillation_termination(self):
        """Oscillation should terminate."""
        should_stop, reason = should_terminate(
            [50.0, 60.0, 52.0, 63.0],  # Up/down/up
        )
        assert should_stop is True
        assert reason == "oscillation"

    def test_stagnation_termination(self):
        """Stagnation should terminate."""
        should_stop, reason = should_terminate(
            [65.0, 65.5, 65.2],  # Flat
            config_stagnation_threshold=2.0,
        )
        assert should_stop is True
        assert reason == "stagnation"

    def test_healthy_progress_no_termination(self):
        """Healthy progress should not terminate."""
        should_stop, reason = should_terminate(
            [50.0, 60.0, 70.0],  # Good progress
            config_min_improvement=5.0,
        )
        assert should_stop is False
        assert reason == ""

    def test_oscillation_checked_before_stagnation(self):
        """Oscillation should be checked before stagnation."""
        # This could match both oscillation and stagnation depending on thresholds
        # Oscillation should take priority
        scores = [50.0, 60.0, 52.0]
        should_stop, reason = should_terminate(scores)
        # With default threshold=2.0, this is oscillation
        assert should_stop is True
        assert reason == "oscillation"
