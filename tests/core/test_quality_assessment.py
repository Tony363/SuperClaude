"""Tests for core/quality_assessment.py - Quality scoring."""


from core.quality_assessment import QualityAssessor, assess_quality


class TestQualityAssessorInit:
    """Tests for QualityAssessor initialization."""

    def test_default_threshold(self):
        """Default threshold should be 70.0."""
        assessor = QualityAssessor()
        assert assessor.threshold == 70.0

    def test_custom_threshold(self):
        """Custom threshold should be preserved."""
        assessor = QualityAssessor(threshold=85.0)
        assert assessor.threshold == 85.0


class TestInlineScoring:
    """Tests for QualityAssessor._inline_score() method."""

    def test_no_evidence_zero_score(self):
        """No evidence should result in zero score."""
        assessor = QualityAssessor()
        result = assessor._inline_score({})
        assert result["score"] == 0.0
        assert result["passed"] is False

    def test_changes_add_30_points(self):
        """File changes should add 30 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"changes": ["file1.py"]})
        assert result["score"] == 30.0

    def test_tests_ran_adds_25_points(self):
        """Running tests should add 25 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"tests": {"ran": True}})
        assert result["score"] == 25.0

    def test_tests_passing_adds_20_points(self):
        """All tests passing should add 20 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "tests": {"ran": True, "passed": 10, "failed": 0}
        })
        # 25 (ran) + 20 (passing) = 45
        assert result["score"] == 45.0

    def test_tests_mostly_passing_adds_15_points(self):
        """90%+ tests passing should add 15 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "tests": {"ran": True, "passed": 9, "failed": 1}
        })
        # 25 (ran) + 15 (90% passing) = 40
        assert result["score"] == 40.0
        assert "1 test(s) failing" in result["missing"]

    def test_lint_clean_adds_15_points(self):
        """Clean lint should add 15 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "lint": {"ran": True, "errors": 0}
        })
        assert result["score"] == 15.0

    def test_lint_errors_tracked(self):
        """Lint errors should be tracked in missing."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "lint": {"ran": True, "errors": 5}
        })
        assert result["score"] == 0.0
        assert "5 lint error(s)" in result["missing"]

    def test_coverage_high_adds_10_points(self):
        """Coverage >= 80% should add 10 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "tests": {"ran": True, "coverage": 85}
        })
        # 25 (ran) + 10 (coverage) = 35
        assert result["score"] == 35.0

    def test_coverage_medium_adds_7_points(self):
        """Coverage 60-79% should add 7 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "tests": {"ran": True, "coverage": 65}
        })
        # 25 (ran) + 7 (coverage) = 32
        assert result["score"] == 32.0

    def test_coverage_low_adds_3_points(self):
        """Coverage 1-59% should add 3 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "tests": {"ran": True, "coverage": 30}
        })
        # 25 (ran) + 3 (coverage) = 28
        assert result["score"] == 28.0
        assert "Coverage 30% is low" in result["missing"]

    def test_full_score(self):
        """Full evidence should achieve high score."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "changes": ["file1.py", "file2.py"],
            "tests": {"ran": True, "passed": 10, "failed": 0, "coverage": 90},
            "lint": {"ran": True, "errors": 0},
        })
        # 30 (changes) + 25 (ran) + 20 (passing) + 15 (lint) + 10 (coverage) = 100
        assert result["score"] == 100.0
        assert result["passed"] is True


class TestQualityBands:
    """Tests for quality band assignment."""

    def test_production_ready_band(self):
        """Score >= 90 should be production_ready."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "changes": ["file.py"],
            "tests": {"ran": True, "passed": 10, "failed": 0, "coverage": 85},
            "lint": {"ran": True, "errors": 0},
        })
        assert result["status"] == "production_ready"

    def test_acceptable_band(self):
        """Score 70-89 should be acceptable."""
        assessor = QualityAssessor()
        # 30 + 25 + 20 = 75 (no lint, so no additional points)
        result = assessor._inline_score({
            "changes": ["file.py"],
            "tests": {"ran": True, "passed": 10, "failed": 0},
        })
        assert result["status"] == "acceptable"

    def test_needs_review_band(self):
        """Score 50-69 should be needs_review."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "changes": ["file.py"],
            "tests": {"ran": True},
        })
        # 30 + 25 = 55
        assert result["status"] == "needs_review"

    def test_insufficient_band(self):
        """Score < 50 should be insufficient."""
        assessor = QualityAssessor()
        result = assessor._inline_score({
            "changes": ["file.py"],
        })
        # 30 only
        assert result["status"] == "insufficient"


class TestQualityAssessorAssess:
    """Tests for QualityAssessor.assess() method."""

    def test_assess_returns_quality_assessment(self):
        """assess() should return QualityAssessment object."""
        assessor = QualityAssessor()
        result = assessor.assess({"changes": ["file.py"]})
        # Verify it's a QualityAssessment
        assert hasattr(result, "overall_score")
        assert hasattr(result, "passed")
        assert hasattr(result, "improvements_needed")

    def test_assess_with_threshold_check(self):
        """assess() should check against threshold (using inline scorer)."""
        assessor = QualityAssessor(threshold=50.0)
        # Force inline scoring by disabling evidence_gate path
        assessor.evidence_gate_path = None
        result = assessor.assess({
            "changes": ["file.py"],
            "tests": {"ran": True},
        })
        # 30 + 25 = 55 > 50
        assert result.passed is True
        assert result.overall_score == 55.0

    def test_assess_below_threshold(self):
        """assess() should fail below threshold."""
        assessor = QualityAssessor(threshold=70.0)
        result = assessor.assess({
            "changes": ["file.py"],
        })
        # 30 < 70
        assert result.passed is False


class TestAssessQualityFunction:
    """Tests for assess_quality convenience function."""

    def test_assess_quality_with_default_threshold(self):
        """assess_quality should use default threshold."""
        result = assess_quality({"changes": ["file.py"]})
        assert result.threshold == 70.0

    def test_assess_quality_with_custom_threshold(self):
        """assess_quality should accept custom threshold."""
        result = assess_quality({"changes": ["file.py"]}, threshold=50.0)
        assert result.threshold == 50.0
