"""Tests for quality assessment in SuperClaude.Orchestrator.quality."""

from SuperClaude.Orchestrator.evidence import EvidenceCollector
from SuperClaude.Orchestrator.quality import (
    QualityAssessment,
    QualityBand,
    QualityConfig,
    assess_quality,
    compare_assessments,
)


class TestQualityBand:
    """Tests for QualityBand enumeration."""

    def test_quality_band_values(self):
        """Test quality band string values."""
        assert QualityBand.EXCELLENT.value == "excellent"
        assert QualityBand.GOOD.value == "good"
        assert QualityBand.ACCEPTABLE.value == "acceptable"
        assert QualityBand.NEEDS_WORK.value == "needs_work"
        assert QualityBand.POOR.value == "poor"


class TestQualityAssessment:
    """Tests for QualityAssessment dataclass."""

    def test_from_score_excellent(self):
        """Test creating assessment from excellent score."""
        assessment = QualityAssessment.from_score(95.0)

        assert assessment.score == 95.0
        assert assessment.passed is True
        assert assessment.band == QualityBand.EXCELLENT

    def test_from_score_good(self):
        """Test creating assessment from good score."""
        assessment = QualityAssessment.from_score(75.0)

        assert assessment.band == QualityBand.GOOD
        assert assessment.passed is True

    def test_from_score_acceptable(self):
        """Test creating assessment from acceptable score."""
        assessment = QualityAssessment.from_score(60.0)

        assert assessment.band == QualityBand.ACCEPTABLE
        assert assessment.passed is False  # Below default 70 threshold

    def test_from_score_needs_work(self):
        """Test creating assessment from needs_work score."""
        assessment = QualityAssessment.from_score(40.0)

        assert assessment.band == QualityBand.NEEDS_WORK

    def test_from_score_poor(self):
        """Test creating assessment from poor score."""
        assessment = QualityAssessment.from_score(20.0)

        assert assessment.band == QualityBand.POOR

    def test_from_score_custom_threshold(self):
        """Test creating assessment with custom threshold."""
        assessment = QualityAssessment.from_score(60.0, threshold=50.0)

        assert assessment.passed is True


class TestQualityConfig:
    """Tests for QualityConfig dataclass."""

    def test_default_weights_sum_to_one(self):
        """Test that default weights sum to 1.0."""
        config = QualityConfig()

        total = (
            config.weight_code_changes
            + config.weight_tests_run
            + config.weight_tests_pass
            + config.weight_coverage
            + config.weight_no_errors
        )

        assert abs(total - 1.0) < 0.001  # Allow for float precision

    def test_default_thresholds(self):
        """Test default threshold values."""
        config = QualityConfig()

        assert config.min_coverage == 80.0
        assert config.quality_threshold == 70.0


class TestAssessQuality:
    """Tests for assess_quality function."""

    def test_empty_evidence_low_score(self, empty_evidence):
        """Test that empty evidence results in low score."""
        assessment = assess_quality(empty_evidence)

        assert assessment.score < 50.0
        assert assessment.passed is False
        assert any("No code changes" in imp for imp in assessment.improvements_needed)

    def test_files_only_partial_score(self, evidence_with_files):
        """Test that files only gives partial score."""
        assessment = assess_quality(evidence_with_files)

        # Should get code_changes points (30% of max)
        # Tests not run, so tests_run is 0
        assert assessment.score > 0
        assert "Run tests" in " ".join(assessment.improvements_needed)

    def test_passing_tests_high_score(self, evidence_with_passing_tests):
        """Test that passing tests give high score."""
        assessment = assess_quality(evidence_with_passing_tests)

        # Should get: code_changes (30) + tests_run (25) + tests_pass (25) = 80+
        assert assessment.score >= 70.0
        assert assessment.passed is True

    def test_failing_tests_medium_score(self, evidence_with_failing_tests):
        """Test that failing tests reduce score."""
        assessment = assess_quality(evidence_with_failing_tests)

        # Has file changes and tests run, but some fail
        # Score will be decent due to file changes + tests running, but not excellent
        assert assessment.score < 90.0  # Not excellent due to failures
        assert "failing test" in " ".join(assessment.improvements_needed).lower()

    def test_complete_evidence_high_score(self, evidence_complete):
        """Test that complete evidence gives high score."""
        assessment = assess_quality(evidence_complete)

        # Multiple files, tests passing, coverage
        assert assessment.score >= 80.0
        assert assessment.passed is True

    def test_dimension_scores_populated(self, evidence_with_passing_tests):
        """Test that dimension scores are populated."""
        assessment = assess_quality(evidence_with_passing_tests)

        assert "code_changes" in assessment.dimension_scores
        assert "tests_run" in assessment.dimension_scores
        assert "tests_pass" in assessment.dimension_scores
        assert "coverage" in assessment.dimension_scores
        assert "no_errors" in assessment.dimension_scores

    def test_majority_failing_capped(self):
        """Test that majority failing tests caps score at 40."""
        evidence = EvidenceCollector()
        evidence.record_file_write("test.py", lines_changed=100)
        evidence.record_command(
            command="pytest tests/",
            output="2 passed, 10 failed",
        )

        assessment = assess_quality(evidence)

        assert assessment.score <= 40.0
        assert "CRITICAL" in assessment.improvements_needed[0]

    def test_custom_config(self):
        """Test using custom quality config."""
        evidence = EvidenceCollector()
        evidence.record_file_write("test.py", lines_changed=50)

        config = QualityConfig(
            quality_threshold=50.0,  # Lower threshold
            weight_code_changes=0.50,  # Higher weight for code changes
            weight_tests_run=0.20,
            weight_tests_pass=0.20,
            weight_coverage=0.05,
            weight_no_errors=0.05,
        )

        assessment = assess_quality(evidence, config)

        # With 50% weight on code_changes, should score higher
        assert assessment.score > 30.0

    def test_improvements_limited_to_five(self):
        """Test that improvements are limited to 5."""
        evidence = EvidenceCollector()
        # Empty evidence should have multiple improvements

        assessment = assess_quality(evidence)

        assert len(assessment.improvements_needed) <= 5


class TestCompareAssessments:
    """Tests for compare_assessments function."""

    def test_improvement_detected(self):
        """Test detecting score improvement."""
        prev = QualityAssessment.from_score(50.0)
        curr = QualityAssessment.from_score(70.0)

        comparison = compare_assessments(curr, prev)

        assert comparison["improved"] is True
        assert comparison["regressed"] is False
        assert comparison["score_delta"] == 20.0

    def test_regression_detected(self):
        """Test detecting score regression."""
        prev = QualityAssessment.from_score(80.0)
        curr = QualityAssessment.from_score(60.0)

        comparison = compare_assessments(curr, prev)

        assert comparison["improved"] is False
        assert comparison["regressed"] is True
        assert comparison["score_delta"] == -20.0

    def test_stagnation_detected(self):
        """Test detecting score stagnation."""
        prev = QualityAssessment.from_score(70.0)
        curr = QualityAssessment.from_score(71.0)

        comparison = compare_assessments(curr, prev)

        assert comparison["stagnant"] is True
        assert abs(comparison["score_delta"]) < 2.0

    def test_band_change_detected(self):
        """Test detecting quality band change."""
        prev = QualityAssessment.from_score(60.0)  # ACCEPTABLE
        curr = QualityAssessment.from_score(75.0)  # GOOD

        comparison = compare_assessments(curr, prev)

        assert comparison["band_changed"] is True
        assert comparison["previous_band"] == "acceptable"
        assert comparison["current_band"] == "good"

    def test_band_no_change(self):
        """Test when quality band doesn't change."""
        prev = QualityAssessment.from_score(72.0)  # GOOD
        curr = QualityAssessment.from_score(78.0)  # GOOD

        comparison = compare_assessments(curr, prev)

        assert comparison["band_changed"] is False


class TestCodeChangeScoring:
    """Tests for code change scoring dimension."""

    def test_no_changes_zero_score(self, empty_evidence):
        """Test that no changes gives zero for dimension."""
        assessment = assess_quality(empty_evidence)

        assert assessment.dimension_scores["code_changes"] == 0.0

    def test_single_file_partial_score(self):
        """Test single file gives partial score."""
        evidence = EvidenceCollector()
        evidence.record_file_write("test.py")

        assessment = assess_quality(evidence)

        assert assessment.dimension_scores["code_changes"] == 80.0

    def test_multiple_files_full_score(self):
        """Test multiple files give full score."""
        evidence = EvidenceCollector()
        evidence.record_file_write("a.py")
        evidence.record_file_write("b.py")
        evidence.record_file_edit("c.py")

        assessment = assess_quality(evidence)

        assert assessment.dimension_scores["code_changes"] == 100.0


class TestTestScoring:
    """Tests for test-related scoring dimensions."""

    def test_no_tests_neutral_score(self, empty_evidence):
        """Test that no tests gives neutral (50) for pass rate."""
        empty_evidence.record_file_write("test.py")  # Need some code change

        assessment = assess_quality(empty_evidence)

        assert assessment.dimension_scores["tests_run"] == 0.0
        assert assessment.dimension_scores["tests_pass"] == 50.0  # Neutral

    def test_tests_run_full_score(self, evidence_with_passing_tests):
        """Test that running tests gives full score for tests_run."""
        assessment = assess_quality(evidence_with_passing_tests)

        assert assessment.dimension_scores["tests_run"] == 100.0

    def test_all_tests_pass_full_score(self, evidence_with_passing_tests):
        """Test that all passing gives full score for tests_pass."""
        assessment = assess_quality(evidence_with_passing_tests)

        assert assessment.dimension_scores["tests_pass"] == 100.0

    def test_partial_pass_rate(self):
        """Test partial pass rate calculation."""
        evidence = EvidenceCollector()
        evidence.record_file_write("test.py")
        evidence.record_command("pytest", "5 passed, 5 failed")  # 50% pass rate

        assessment = assess_quality(evidence)

        assert assessment.dimension_scores["tests_pass"] == 50.0


class TestCoverageScoring:
    """Tests for coverage scoring dimension."""

    def test_no_coverage_neutral(self, evidence_with_passing_tests):
        """Test no coverage data gives neutral score."""
        assessment = assess_quality(evidence_with_passing_tests)

        # Tests run but no coverage reported
        assert assessment.dimension_scores["coverage"] == 50.0

    def test_high_coverage_full_score(self, evidence_complete):
        """Test high coverage gives full score."""
        assessment = assess_quality(evidence_complete)

        # evidence_complete has 85% coverage
        assert assessment.dimension_scores["coverage"] == 100.0

    def test_low_coverage_partial_score(self):
        """Test low coverage gives partial score."""
        evidence = EvidenceCollector()
        evidence.record_file_write("test.py")
        evidence.record_command("pytest --cov", "5 passed\nCoverage: 40%")

        config = QualityConfig(min_coverage=80.0)
        assessment = assess_quality(evidence, config)

        # 40/80 = 50% of full score
        assert assessment.dimension_scores["coverage"] == 50.0


class TestErrorScoring:
    """Tests for no_errors scoring dimension."""

    def test_clean_output_full_score(self, evidence_with_passing_tests):
        """Test clean output gives full error score."""
        assessment = assess_quality(evidence_with_passing_tests)

        assert assessment.dimension_scores["no_errors"] == 100.0

    def test_error_in_output_reduces_score(self):
        """Test error patterns in output reduce score."""
        evidence = EvidenceCollector()
        evidence.record_file_write("test.py")
        evidence.record_command(
            "python test.py",
            "Error: something went wrong\nTraceback: ...",
        )

        assessment = assess_quality(evidence)

        assert assessment.dimension_scores["no_errors"] < 100.0
