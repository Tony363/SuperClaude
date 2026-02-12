"""Tests for core/__init__.py - Module exports after simplification.

Verifies that all expected symbols are exported and removed symbols are gone.
"""


class TestCoreExports:
    """Tests for core module public API."""

    def test_loop_orchestrator_exported(self):
        """LoopOrchestrator should be importable from core."""
        from core import LoopOrchestrator

        assert LoopOrchestrator is not None

    def test_pal_review_signal_exported(self):
        """PALReviewSignal should be importable from core."""
        from core import PALReviewSignal

        assert PALReviewSignal is not None

    def test_quality_assessor_exported(self):
        """QualityAssessor should be importable from core."""
        from core import QualityAssessor

        assert QualityAssessor is not None

    def test_iteration_result_exported(self):
        """IterationResult should be importable from core."""
        from core import IterationResult

        assert IterationResult is not None

    def test_loop_config_exported(self):
        """LoopConfig should be importable from core."""
        from core import LoopConfig

        assert LoopConfig is not None

    def test_loop_result_exported(self):
        """LoopResult should be importable from core."""
        from core import LoopResult

        assert LoopResult is not None

    def test_quality_assessment_exported(self):
        """QualityAssessment should be importable from core."""
        from core import QualityAssessment

        assert QualityAssessment is not None

    def test_termination_reason_exported(self):
        """TerminationReason should be importable from core."""
        from core import TerminationReason

        assert TerminationReason is not None

    def test_all_list_complete(self):
        """__all__ should contain all expected exports."""
        import core

        expected = {
            "LoopOrchestrator",
            "PALReviewSignal",
            "QualityAssessor",
            "IterationResult",
            "LoopConfig",
            "LoopResult",
            "QualityAssessment",
            "TerminationReason",
        }
        assert set(core.__all__) == expected

    def test_all_list_length(self):
        """__all__ should have exactly 8 entries after simplification."""
        import core

        assert len(core.__all__) == 8


class TestRemovedExports:
    """Tests verifying removed symbols are not exported."""

    def test_detect_oscillation_not_exported(self):
        """detect_oscillation should NOT be importable from core."""
        import core

        assert not hasattr(core, "detect_oscillation")

    def test_detect_stagnation_not_exported(self):
        """detect_stagnation should NOT be importable from core."""
        import core

        assert not hasattr(core, "detect_stagnation")

    def test_termination_module_not_exported(self):
        """termination module should not be accessible from core."""
        import core

        assert "detect_oscillation" not in dir(core)
        assert "detect_stagnation" not in dir(core)

    def test_no_oscillation_in_termination_reason(self):
        """OSCILLATION should not be in TerminationReason."""
        from core import TerminationReason

        assert not hasattr(TerminationReason, "OSCILLATION")

    def test_no_stagnation_in_termination_reason(self):
        """STAGNATION should not be in TerminationReason."""
        from core import TerminationReason

        assert not hasattr(TerminationReason, "STAGNATION")

    def test_no_insufficient_improvement_in_termination_reason(self):
        """INSUFFICIENT_IMPROVEMENT should not be in TerminationReason."""
        from core import TerminationReason

        assert not hasattr(TerminationReason, "INSUFFICIENT_IMPROVEMENT")

    def test_no_oscillation_window_in_loop_config(self):
        """oscillation_window should not be in LoopConfig."""
        from core import LoopConfig

        assert not hasattr(LoopConfig, "oscillation_window")

    def test_no_stagnation_threshold_in_loop_config(self):
        """stagnation_threshold should not be in LoopConfig."""
        from core import LoopConfig

        assert not hasattr(LoopConfig, "stagnation_threshold")

    def test_no_min_improvement_in_loop_config(self):
        """min_improvement should not be in LoopConfig."""
        from core import LoopConfig

        config = LoopConfig()
        assert not hasattr(config, "min_improvement")
