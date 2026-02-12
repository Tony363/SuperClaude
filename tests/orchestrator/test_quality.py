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

    def test_test_errors_zero_error_score(self):
        """Test that test errors result in zero error score."""
        evidence = EvidenceCollector()
        evidence.record_file_write("test.py")
        evidence.record_command(
            "pytest tests/",
            "3 passed, 1 error in 1.0s",
        )

        assessment = assess_quality(evidence)

        assert assessment.dimension_scores["no_errors"] == 0.0


class TestQualityBoundaryConditions:
    """Boundary condition tests for quality scoring."""

    def test_score_exactly_at_threshold(self):
        """Score exactly at threshold should pass."""
        assessment = QualityAssessment.from_score(70.0)
        assert assessment.passed is True

    def test_score_just_below_threshold(self):
        """Score just below threshold should not pass."""
        assessment = QualityAssessment.from_score(69.9)
        assert assessment.passed is False

    def test_band_boundary_90(self):
        """Score of exactly 90 should be excellent."""
        assessment = QualityAssessment.from_score(90.0)
        assert assessment.band == QualityBand.EXCELLENT

    def test_band_boundary_89(self):
        """Score of 89.9 should be good."""
        assessment = QualityAssessment.from_score(89.9)
        assert assessment.band == QualityBand.GOOD

    def test_band_boundary_70(self):
        """Score of exactly 70 should be good."""
        assessment = QualityAssessment.from_score(70.0)
        assert assessment.band == QualityBand.GOOD

    def test_band_boundary_69(self):
        """Score of 69.9 should be acceptable."""
        assessment = QualityAssessment.from_score(69.9)
        assert assessment.band == QualityBand.ACCEPTABLE

    def test_band_boundary_50(self):
        """Score of exactly 50 should be acceptable."""
        assessment = QualityAssessment.from_score(50.0)
        assert assessment.band == QualityBand.ACCEPTABLE

    def test_band_boundary_49(self):
        """Score of 49.9 should be needs_work."""
        assessment = QualityAssessment.from_score(49.9)
        assert assessment.band == QualityBand.NEEDS_WORK

    def test_band_boundary_30(self):
        """Score of exactly 30 should be needs_work."""
        assessment = QualityAssessment.from_score(30.0)
        assert assessment.band == QualityBand.NEEDS_WORK

    def test_band_boundary_29(self):
        """Score of 29.9 should be poor."""
        assessment = QualityAssessment.from_score(29.9)
        assert assessment.band == QualityBand.POOR

    def test_score_zero(self):
        """Score of 0 should be poor."""
        assessment = QualityAssessment.from_score(0.0)
        assert assessment.band == QualityBand.POOR
        assert assessment.passed is False

    def test_score_100(self):
        """Score of 100 should be excellent."""
        assessment = QualityAssessment.from_score(100.0)
        assert assessment.band == QualityBand.EXCELLENT
        assert assessment.passed is True


class TestCompareAssessmentsEdgeCases:
    """Edge case tests for compare_assessments."""

    def test_same_score(self):
        """Same score should be stagnant, not improved or regressed."""
        prev = QualityAssessment.from_score(70.0)
        curr = QualityAssessment.from_score(70.0)

        comparison = compare_assessments(curr, prev)

        assert comparison["improved"] is False
        assert comparison["regressed"] is False
        assert comparison["stagnant"] is True
        assert comparison["score_delta"] == 0.0

    def test_tiny_improvement_still_stagnant(self):
        """Improvement of less than 2.0 should still count as stagnant."""
        prev = QualityAssessment.from_score(70.0)
        curr = QualityAssessment.from_score(71.5)

        comparison = compare_assessments(curr, prev)

        assert comparison["improved"] is True  # Delta > 0
        assert comparison["stagnant"] is True  # Delta < 2.0

    def test_improvement_of_exactly_2(self):
        """Delta of exactly 2.0 should not be stagnant."""
        prev = QualityAssessment.from_score(70.0)
        curr = QualityAssessment.from_score(72.0)

        comparison = compare_assessments(curr, prev)

        assert comparison["stagnant"] is False

    def test_large_regression(self):
        """Large score drop should be regression."""
        prev = QualityAssessment.from_score(90.0)
        curr = QualityAssessment.from_score(30.0)

        comparison = compare_assessments(curr, prev)

        assert comparison["regressed"] is True
        assert comparison["score_delta"] == -60.0
        assert comparison["band_changed"] is True


class TestQualityDimensionInteractions:
    """Tests for how quality dimensions interact."""

    def test_read_only_no_code_change_points(self, empty_evidence):
        """Only reading files should not give code change points."""
        empty_evidence.record_file_read("a.py")
        empty_evidence.record_file_read("b.py")

        assessment = assess_quality(empty_evidence)

        assert assessment.dimension_scores["code_changes"] == 0.0

    def test_tests_pass_neutral_when_no_tests(self, empty_evidence):
        """Tests pass dimension should be neutral (50) when no tests run."""
        assessment = assess_quality(empty_evidence)
        assert assessment.dimension_scores["tests_pass"] == 50.0

    def test_coverage_neutral_when_no_tests(self, empty_evidence):
        """Coverage dimension should be neutral (50) when no tests run."""
        assessment = assess_quality(empty_evidence)
        assert assessment.dimension_scores["coverage"] == 50.0

    def test_full_score_all_dimensions(self):
        """All dimensions at max should produce score near 100."""
        evidence = EvidenceCollector()
        # 3+ files for code_changes=100
        evidence.record_file_write("a.py", lines_changed=50)
        evidence.record_file_write("b.py", lines_changed=50)
        evidence.record_file_edit("c.py", lines_changed=10)
        # All tests pass
        evidence.record_command(
            "pytest --cov=src",
            "50 passed\nCoverage: 95%",
        )

        assessment = assess_quality(evidence)

        assert assessment.score >= 95.0
        assert assessment.passed is True
        assert assessment.band == QualityBand.EXCELLENT
