"""Tests for core/types.py - Loop orchestration data types."""


from core.types import (
    IterationResult,
    LoopConfig,
    LoopResult,
    QualityAssessment,
    TerminationReason,
)


class TestTerminationReason:
    """Tests for TerminationReason enum."""

    def test_all_reasons_have_string_values(self):
        """All termination reasons should have descriptive string values."""
        for reason in TerminationReason:
            assert isinstance(reason.value, str)
            assert len(reason.value) > 0

    def test_expected_reasons_exist(self):
        """All expected termination reasons should be defined."""
        expected = [
            "QUALITY_MET",
            "MAX_ITERATIONS",
            "INSUFFICIENT_IMPROVEMENT",
            "STAGNATION",
            "OSCILLATION",
            "ERROR",
            "HUMAN_ESCALATION",
            "TIMEOUT",
        ]
        for name in expected:
            assert hasattr(TerminationReason, name)

    def test_quality_met_value(self):
        """QUALITY_MET should have the expected value."""
        assert TerminationReason.QUALITY_MET.value == "quality_threshold_met"

    def test_oscillation_value(self):
        """OSCILLATION should have the expected value."""
        assert TerminationReason.OSCILLATION.value == "score_oscillation"


class TestLoopConfig:
    """Tests for LoopConfig dataclass."""

    def test_default_values(self):
        """Default configuration should have sensible values."""
        config = LoopConfig()
        assert config.max_iterations == 3
        assert config.hard_max_iterations == 5
        assert config.min_improvement == 5.0
        assert config.quality_threshold == 70.0
        assert config.oscillation_window == 3
        assert config.stagnation_threshold == 2.0
        assert config.timeout_seconds is None
        assert config.pal_review_enabled is True
        assert config.pal_model == "gpt-5"

    def test_hard_max_cannot_be_exceeded(self):
        """P0 SAFETY: max_iterations should be capped at hard_max_iterations."""
        config = LoopConfig(max_iterations=10)
        assert config.max_iterations == 5  # Capped at hard_max

    def test_hard_max_with_exact_value(self):
        """Setting max_iterations to exactly hard_max should work."""
        config = LoopConfig(max_iterations=5)
        assert config.max_iterations == 5

    def test_custom_values_below_hard_max(self):
        """Custom max_iterations below hard_max should be preserved."""
        config = LoopConfig(max_iterations=2)
        assert config.max_iterations == 2

    def test_custom_threshold(self):
        """Custom quality_threshold should be preserved."""
        config = LoopConfig(quality_threshold=85.0)
        assert config.quality_threshold == 85.0

    def test_pal_disabled(self):
        """PAL review can be disabled."""
        config = LoopConfig(pal_review_enabled=False)
        assert config.pal_review_enabled is False

    def test_timeout_can_be_set(self):
        """Timeout can be configured."""
        config = LoopConfig(timeout_seconds=300.0)
        assert config.timeout_seconds == 300.0


class TestQualityAssessment:
    """Tests for QualityAssessment dataclass."""

    def test_minimal_construction(self):
        """QualityAssessment can be created with minimal required args."""
        assessment = QualityAssessment(overall_score=75.0, passed=True)
        assert assessment.overall_score == 75.0
        assert assessment.passed is True
        assert assessment.threshold == 70.0  # Default

    def test_default_improvements_list(self):
        """improvements_needed defaults to empty list."""
        assessment = QualityAssessment(overall_score=50.0, passed=False)
        assert assessment.improvements_needed == []

    def test_default_metrics_dict(self):
        """metrics defaults to empty dict."""
        assessment = QualityAssessment(overall_score=50.0, passed=False)
        assert assessment.metrics == {}

    def test_with_improvements(self):
        """QualityAssessment can include improvements list."""
        improvements = ["Add tests", "Fix lint errors"]
        assessment = QualityAssessment(
            overall_score=60.0,
            passed=False,
            improvements_needed=improvements,
        )
        assert assessment.improvements_needed == improvements

    def test_quality_band(self):
        """Quality band can be set."""
        assessment = QualityAssessment(
            overall_score=85.0,
            passed=True,
            band="excellent",
        )
        assert assessment.band == "excellent"


class TestIterationResult:
    """Tests for IterationResult dataclass."""

    def test_minimal_construction(self):
        """IterationResult can be created with minimal args."""
        result = IterationResult(
            iteration=0,
            input_quality=50.0,
            output_quality=65.0,
        )
        assert result.iteration == 0
        assert result.input_quality == 50.0
        assert result.output_quality == 65.0

    def test_default_values(self):
        """Default values should be sensible."""
        result = IterationResult(
            iteration=0,
            input_quality=50.0,
            output_quality=65.0,
        )
        assert result.improvements_applied == []
        assert result.time_taken == 0.0
        assert result.success is False
        assert result.termination_reason == ""
        assert result.pal_review is None
        assert result.changed_files == []

    def test_with_pal_review(self):
        """IterationResult can include PAL review data."""
        pal_data = {"tool": "codereview", "score": 80}
        result = IterationResult(
            iteration=1,
            input_quality=65.0,
            output_quality=75.0,
            pal_review=pal_data,
        )
        assert result.pal_review == pal_data

    def test_with_changed_files(self):
        """IterationResult can include changed files."""
        files = ["src/main.py", "tests/test_main.py"]
        result = IterationResult(
            iteration=0,
            input_quality=0.0,
            output_quality=50.0,
            changed_files=files,
        )
        assert result.changed_files == files


class TestLoopResult:
    """Tests for LoopResult dataclass."""

    def test_construction(self):
        """LoopResult can be constructed with all required fields."""
        assessment = QualityAssessment(overall_score=75.0, passed=True)
        result = LoopResult(
            final_output={"status": "complete"},
            final_assessment=assessment,
            iteration_history=[],
            termination_reason=TerminationReason.QUALITY_MET,
            total_iterations=2,
            total_time=10.5,
        )
        assert result.total_iterations == 2
        assert result.total_time == 10.5
        assert result.termination_reason == TerminationReason.QUALITY_MET

    def test_to_dict_basic(self):
        """to_dict should produce a JSON-serializable dict."""
        assessment = QualityAssessment(overall_score=75.0, passed=True)
        result = LoopResult(
            final_output={"status": "complete"},
            final_assessment=assessment,
            iteration_history=[],
            termination_reason=TerminationReason.QUALITY_MET,
            total_iterations=1,
            total_time=5.0,
        )
        d = result.to_dict()
        assert d["loop_completed"] is True
        assert d["iterations"] == 1
        assert d["termination_reason"] == "quality_threshold_met"
        assert d["final_score"] == 75.0
        assert d["passed"] is True
        assert d["total_time"] == 5.0
        assert d["history"] == []

    def test_to_dict_with_history(self):
        """to_dict should include iteration history."""
        assessment = QualityAssessment(overall_score=80.0, passed=True)
        iteration = IterationResult(
            iteration=0,
            input_quality=50.0,
            output_quality=80.0,
            success=True,
            improvements_applied=["Add tests"],
            changed_files=["main.py"],
        )
        result = LoopResult(
            final_output={},
            final_assessment=assessment,
            iteration_history=[iteration],
            termination_reason=TerminationReason.QUALITY_MET,
            total_iterations=1,
        )
        d = result.to_dict()
        assert len(d["history"]) == 1
        assert d["history"][0]["iteration"] == 0
        assert d["history"][0]["input_score"] == 50.0
        assert d["history"][0]["output_score"] == 80.0
        assert d["history"][0]["success"] is True
        assert d["history"][0]["improvements"] == ["Add tests"]
        assert d["history"][0]["changed_files"] == ["main.py"]
