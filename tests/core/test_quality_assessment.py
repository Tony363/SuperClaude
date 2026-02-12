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
        result = assessor._inline_score({"tests": {"ran": True, "passed": 10, "failed": 0}})
        # 25 (ran) + 20 (passing) = 45
        assert result["score"] == 45.0

    def test_tests_mostly_passing_adds_15_points(self):
        """90%+ tests passing should add 15 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"tests": {"ran": True, "passed": 9, "failed": 1}})
        # 25 (ran) + 15 (90% passing) = 40
        assert result["score"] == 40.0
        assert "1 test(s) failing" in result["missing"]

    def test_lint_clean_adds_15_points(self):
        """Clean lint should add 15 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"lint": {"ran": True, "errors": 0}})
        assert result["score"] == 15.0

    def test_lint_errors_tracked(self):
        """Lint errors should be tracked in missing."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"lint": {"ran": True, "errors": 5}})
        assert result["score"] == 0.0
        assert "5 lint error(s)" in result["missing"]

    def test_coverage_high_adds_10_points(self):
        """Coverage >= 80% should add 10 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"tests": {"ran": True, "coverage": 85}})
        # 25 (ran) + 10 (coverage) = 35
        assert result["score"] == 35.0

    def test_coverage_medium_adds_7_points(self):
        """Coverage 60-79% should add 7 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"tests": {"ran": True, "coverage": 65}})
        # 25 (ran) + 7 (coverage) = 32
        assert result["score"] == 32.0

    def test_coverage_low_adds_3_points(self):
        """Coverage 1-59% should add 3 points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"tests": {"ran": True, "coverage": 30}})
        # 25 (ran) + 3 (coverage) = 28
        assert result["score"] == 28.0
        assert "Coverage 30% is low" in result["missing"]

    def test_full_score(self):
        """Full evidence should achieve high score."""
        assessor = QualityAssessor()
        result = assessor._inline_score(
            {
                "changes": ["file1.py", "file2.py"],
                "tests": {"ran": True, "passed": 10, "failed": 0, "coverage": 90},
                "lint": {"ran": True, "errors": 0},
            }
        )
        # 30 (changes) + 25 (ran) + 20 (passing) + 15 (lint) + 10 (coverage) = 100
        assert result["score"] == 100.0
        assert result["passed"] is True


class TestQualityBands:
    """Tests for quality band assignment."""

    def test_production_ready_band(self):
        """Score >= 90 should be production_ready."""
        assessor = QualityAssessor()
        result = assessor._inline_score(
            {
                "changes": ["file.py"],
                "tests": {"ran": True, "passed": 10, "failed": 0, "coverage": 85},
                "lint": {"ran": True, "errors": 0},
            }
        )
        assert result["status"] == "production_ready"

    def test_acceptable_band(self):
        """Score 70-89 should be acceptable."""
        assessor = QualityAssessor()
        # 30 + 25 + 20 = 75 (no lint, so no additional points)
        result = assessor._inline_score(
            {
                "changes": ["file.py"],
                "tests": {"ran": True, "passed": 10, "failed": 0},
            }
        )
        assert result["status"] == "acceptable"

    def test_needs_review_band(self):
        """Score 50-69 should be needs_review."""
        assessor = QualityAssessor()
        result = assessor._inline_score(
            {
                "changes": ["file.py"],
                "tests": {"ran": True},
            }
        )
        # 30 + 25 = 55
        assert result["status"] == "needs_review"

    def test_insufficient_band(self):
        """Score < 50 should be insufficient."""
        assessor = QualityAssessor()
        result = assessor._inline_score(
            {
                "changes": ["file.py"],
            }
        )
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
        result = assessor.assess(
            {
                "changes": ["file.py"],
                "tests": {"ran": True},
            }
        )
        # 30 + 25 = 55 > 50
        assert result.passed is True
        assert result.overall_score == 55.0

    def test_assess_below_threshold(self):
        """assess() should fail below threshold."""
        assessor = QualityAssessor(threshold=70.0)
        result = assessor.assess(
            {
                "changes": ["file.py"],
            }
        )
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


class TestToQualityAssessment:
    """Tests for QualityAssessor._to_quality_assessment() conversion."""

    def test_maps_score(self):
        """Should map 'score' from result to overall_score."""
        assessor = QualityAssessor(threshold=70.0)
        qa = assessor._to_quality_assessment({"score": 82.5, "passed": True})
        assert qa.overall_score == 82.5

    def test_maps_passed(self):
        """Should map 'passed' from result."""
        assessor = QualityAssessor(threshold=70.0)
        qa = assessor._to_quality_assessment({"score": 50.0, "passed": False})
        assert qa.passed is False

    def test_maps_missing_to_improvements(self):
        """Should map 'missing' list to improvements_needed."""
        assessor = QualityAssessor()
        qa = assessor._to_quality_assessment(
            {
                "score": 50.0,
                "passed": False,
                "missing": ["No tests", "No lint"],
            }
        )
        assert qa.improvements_needed == ["No tests", "No lint"]

    def test_maps_evidence_summary_to_metrics(self):
        """Should map 'evidence_summary' to metrics."""
        assessor = QualityAssessor()
        qa = assessor._to_quality_assessment(
            {
                "score": 75.0,
                "passed": True,
                "evidence_summary": {"tests_ran": True, "lint_ran": True},
            }
        )
        assert qa.metrics == {"tests_ran": True, "lint_ran": True}

    def test_maps_status_to_band(self):
        """Should map 'status' to band."""
        assessor = QualityAssessor()
        qa = assessor._to_quality_assessment(
            {
                "score": 95.0,
                "passed": True,
                "status": "production_ready",
            }
        )
        assert qa.band == "production_ready"

    def test_stores_full_result_as_metadata(self):
        """Full result dict should be stored as metadata."""
        assessor = QualityAssessor()
        result = {"score": 80.0, "passed": True, "extra": "data"}
        qa = assessor._to_quality_assessment(result)
        assert qa.metadata == result

    def test_uses_configured_threshold(self):
        """Should use the assessor's threshold, not the result's."""
        assessor = QualityAssessor(threshold=85.0)
        qa = assessor._to_quality_assessment({"score": 80.0, "passed": False})
        assert qa.threshold == 85.0

    def test_defaults_for_missing_fields(self):
        """Should handle result dict with missing optional fields."""
        assessor = QualityAssessor()
        qa = assessor._to_quality_assessment({})
        assert qa.overall_score == 0.0
        assert qa.passed is False
        assert qa.improvements_needed == []
        assert qa.metrics == {}
        assert qa.band == "unknown"


class TestInlineScoringEdgeCases:
    """Edge case tests for inline scoring logic."""

    def test_zero_total_tests_no_passing_points(self):
        """Zero total tests should not award passing points."""
        assessor = QualityAssessor()
        result = assessor._inline_score(
            {
                "tests": {"ran": True, "passed": 0, "failed": 0},
            }
        )
        # 25 (ran) but no passing bonus
        assert result["score"] == 25.0

    def test_tests_below_90_percent_no_partial_points(self):
        """Below 90% passing should not award partial points."""
        assessor = QualityAssessor()
        result = assessor._inline_score(
            {
                "tests": {"ran": True, "passed": 5, "failed": 5},
            }
        )
        # 25 (ran) + 0 (50% pass rate < 90%)
        assert result["score"] == 25.0

    def test_missing_evidence_items(self):
        """Missing evidence should accumulate missing items."""
        assessor = QualityAssessor()
        result = assessor._inline_score({})
        assert "No file changes detected" in result["missing"]
        assert "Tests not executed" in result["missing"]

    def test_coverage_zero_no_points(self):
        """Zero coverage should not add points."""
        assessor = QualityAssessor()
        result = assessor._inline_score(
            {
                "tests": {"ran": True, "coverage": 0},
            }
        )
        # 25 (ran) + 0 (zero coverage)
        assert result["score"] == 25.0

    def test_threshold_50_passes(self):
        """Custom threshold of 50 should pass at 55."""
        assessor = QualityAssessor(threshold=50.0)
        result = assessor._inline_score(
            {
                "changes": ["f.py"],
                "tests": {"ran": True},
            }
        )
        # 30 + 25 = 55 >= 50
        assert result["passed"] is True

    def test_lint_not_ran_no_points(self):
        """Lint not ran should not add points."""
        assessor = QualityAssessor()
        result = assessor._inline_score({"lint": {"ran": False}})
        assert result["score"] == 0.0


class TestQualityAssessorEvidenceGate:
    """Tests for evidence_gate interaction."""

    def test_evidence_gate_path_none_uses_inline(self):
        """When evidence_gate not found, should use inline scoring."""
        assessor = QualityAssessor()
        assessor.evidence_gate_path = None
        result = assessor.assess({"changes": ["file.py"]})
        assert result.overall_score == 30.0  # Inline: 30 for changes

    def test_assess_with_full_context(self):
        """Assess with full evidence should use inline scorer."""
        assessor = QualityAssessor(threshold=50.0)
        assessor.evidence_gate_path = None
        result = assessor.assess(
            {
                "changes": ["f.py"],
                "tests": {"ran": True, "passed": 10, "failed": 0, "coverage": 85},
                "lint": {"ran": True, "errors": 0},
            }
        )
        # 30 + 25 + 20 + 15 + 10 = 100
        assert result.overall_score == 100.0
        assert result.passed is True
        assert result.band == "production_ready"


class TestInvokeEvidenceGate:
    """Tests for QualityAssessor._invoke_evidence_gate() error paths."""

    def test_successful_subprocess(self):
        """Should parse stdout JSON on success."""
        from unittest.mock import MagicMock, patch

        assessor = QualityAssessor()
        assessor.evidence_gate_path = "/fake/path.py"

        mock_result = MagicMock()
        mock_result.stdout = '{"score": 85.0, "passed": true, "status": "acceptable"}'
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = assessor._invoke_evidence_gate({"changes": ["f.py"]})

        assert result["score"] == 85.0
        assert result["passed"] is True

    def test_empty_stdout_returns_error(self):
        """Empty stdout should return error dict."""
        from unittest.mock import MagicMock, patch

        assessor = QualityAssessor()
        assessor.evidence_gate_path = "/fake/path.py"

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "something went wrong"

        with patch("subprocess.run", return_value=mock_result):
            result = assessor._invoke_evidence_gate({})

        assert result["passed"] is False
        assert result["score"] == 0.0
        assert result["status"] == "error"
        assert "evidence_gate error:" in result["missing"][0]

    def test_timeout_returns_timeout_dict(self):
        """Subprocess timeout should return timeout error."""
        import subprocess
        from unittest.mock import patch

        assessor = QualityAssessor()
        assessor.evidence_gate_path = "/fake/path.py"

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            result = assessor._invoke_evidence_gate({})

        assert result["passed"] is False
        assert result["status"] == "timeout"
        assert "timed out" in result["missing"][0]

    def test_generic_exception_returns_error(self):
        """Generic exception should return error dict."""
        from unittest.mock import patch

        assessor = QualityAssessor()
        assessor.evidence_gate_path = "/fake/path.py"

        with patch("subprocess.run", side_effect=OSError("Permission denied")):
            result = assessor._invoke_evidence_gate({})

        assert result["passed"] is False
        assert result["status"] == "error"
        assert "Permission denied" in result["missing"][0]

    def test_invalid_json_stdout_returns_error(self):
        """Invalid JSON in stdout should return error."""
        from unittest.mock import MagicMock, patch

        assessor = QualityAssessor()
        assessor.evidence_gate_path = "/fake/path.py"

        mock_result = MagicMock()
        mock_result.stdout = "not valid json"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = assessor._invoke_evidence_gate({})

        # json.loads will raise, caught by generic except
        assert result["passed"] is False
        assert result["status"] == "error"


class TestFindEvidenceGate:
    """Tests for QualityAssessor._find_evidence_gate() path discovery."""

    def test_returns_none_when_not_found(self):
        """Should return None when evidence_gate.py not found."""
        from pathlib import Path
        from unittest.mock import patch

        with patch.object(Path, "exists", return_value=False):
            assessor = QualityAssessor()

        # The assessor's path may or may not be None depending on filesystem
        # But if we mock exists to always return False, it should be None
        # Re-call the method directly for a clean test
        with patch.object(Path, "exists", return_value=False):
            result = assessor._find_evidence_gate()
        assert result is None

    def test_assess_uses_evidence_gate_when_available(self):
        """Should use evidence_gate when path exists."""
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        assessor = QualityAssessor()
        assessor.evidence_gate_path = Path("/fake/evidence_gate.py")

        mock_result = MagicMock()
        mock_result.stdout = '{"score": 90.0, "passed": true, "status": "production_ready"}'
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = assessor.assess({"changes": ["f.py"]})

        assert result.overall_score == 90.0


class TestAssessContextMapping:
    """Tests for how assess() maps context to evidence format."""

    def test_maps_command_key(self):
        """Should map 'command' from context."""
        assessor = QualityAssessor()
        assessor.evidence_gate_path = None
        # When using inline scoring, the command key doesn't affect score
        # but should not cause errors
        result = assessor.assess({"command": "test", "changes": ["f.py"]})
        assert result.overall_score == 30.0

    def test_handles_missing_keys(self):
        """Should handle context with no relevant keys."""
        assessor = QualityAssessor()
        assessor.evidence_gate_path = None
        result = assessor.assess({})
        assert result.overall_score == 0.0
        assert result.passed is False
