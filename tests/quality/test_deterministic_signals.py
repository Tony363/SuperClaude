"""
P1 Tests: Deterministic Signals for Quality Scoring

Tests the grounding of quality scores in verifiable facts from
actual tool execution (tests, linters, builds, security scans).
"""

from __future__ import annotations

import pytest

from SuperClaude.Quality.quality_scorer import (
    DeterministicSignals,
    QualityScorer,
)


class TestDeterministicSignals:
    """Test the DeterministicSignals dataclass."""

    def test_default_values(self):
        """Test that defaults are safe (assume nothing passed)."""
        signals = DeterministicSignals()

        assert signals.tests_passed is False
        assert signals.tests_total == 0
        assert signals.lint_passed is False
        assert signals.build_passed is False
        assert signals.security_passed is False

    def test_has_hard_failures_with_failing_tests(self):
        """Test detection of failing tests as hard failure."""
        signals = DeterministicSignals(
            tests_passed=False,
            tests_total=10,
            tests_failed=3,
        )

        assert signals.has_hard_failures() is True

    def test_has_hard_failures_with_security_critical(self):
        """Test detection of critical security issues as hard failure."""
        signals = DeterministicSignals(
            security_passed=False,
            security_critical=1,
        )

        assert signals.has_hard_failures() is True

    def test_has_hard_failures_with_build_failure(self):
        """Test detection of build failure as hard failure."""
        signals = DeterministicSignals(
            build_passed=False,
            build_errors=5,
        )

        assert signals.has_hard_failures() is True

    def test_no_hard_failures_when_all_pass(self):
        """Test no hard failures when everything passes."""
        signals = DeterministicSignals(
            tests_passed=True,
            tests_total=50,
            tests_failed=0,
            build_passed=True,
            security_passed=True,
        )

        assert signals.has_hard_failures() is False


class TestHardFailureCap:
    """Test the score capping based on hard failures."""

    def test_critical_security_caps_at_30(self):
        """Critical security issues cap score at 30."""
        signals = DeterministicSignals(security_critical=2)
        cap = signals.get_hard_failure_cap()
        assert cap == 30.0

    def test_high_test_failure_rate_caps_at_40(self):
        """Over 50% test failure caps score at 40."""
        signals = DeterministicSignals(
            tests_total=10,
            tests_failed=6,  # 60% failure
        )
        cap = signals.get_hard_failure_cap()
        assert cap == 40.0

    def test_medium_test_failure_rate_caps_at_50(self):
        """20-50% test failure caps score at 50."""
        signals = DeterministicSignals(
            tests_total=10,
            tests_failed=3,  # 30% failure
        )
        cap = signals.get_hard_failure_cap()
        assert cap == 50.0

    def test_low_test_failure_rate_caps_at_60(self):
        """Under 20% test failure caps score at 60."""
        signals = DeterministicSignals(
            tests_total=10,
            tests_failed=1,  # 10% failure
        )
        cap = signals.get_hard_failure_cap()
        assert cap == 60.0

    def test_build_failure_caps_at_45(self):
        """Build failure caps score at 45."""
        signals = DeterministicSignals(
            build_passed=False,
            build_errors=3,
        )
        cap = signals.get_hard_failure_cap()
        assert cap == 45.0

    def test_high_security_issues_caps_at_65(self):
        """High severity security issues cap score at 65."""
        signals = DeterministicSignals(
            security_high=2,
        )
        cap = signals.get_hard_failure_cap()
        assert cap == 65.0

    def test_no_failures_no_cap(self):
        """No failures means no cap (returns 100)."""
        signals = DeterministicSignals(
            tests_passed=True,
            tests_total=10,
            tests_failed=0,
            build_passed=True,
            security_passed=True,
        )
        cap = signals.get_hard_failure_cap()
        assert cap == 100.0


class TestBonusCalculation:
    """Test bonus points for positive signals."""

    def test_high_coverage_bonus(self):
        """Test bonus for high test coverage (80%+)."""
        signals = DeterministicSignals(test_coverage=85.0)
        bonus = signals.calculate_bonus()
        assert bonus >= 10.0

    def test_medium_coverage_bonus(self):
        """Test bonus for medium test coverage (60-80%)."""
        signals = DeterministicSignals(test_coverage=70.0)
        bonus = signals.calculate_bonus()
        assert 5.0 <= bonus < 10.0

    def test_clean_lint_bonus(self):
        """Test bonus for clean lint."""
        signals = DeterministicSignals(
            lint_passed=True,
            lint_errors=0,
        )
        bonus = signals.calculate_bonus()
        assert bonus >= 5.0

    def test_clean_type_check_bonus(self):
        """Test bonus for clean type check."""
        signals = DeterministicSignals(
            type_check_passed=True,
            type_errors=0,
        )
        bonus = signals.calculate_bonus()
        assert bonus >= 5.0

    def test_all_tests_passing_bonus(self):
        """Test bonus for all tests passing."""
        signals = DeterministicSignals(
            tests_passed=True,
            tests_total=50,
            tests_failed=0,
        )
        bonus = signals.calculate_bonus()
        assert bonus >= 5.0

    def test_security_passed_bonus(self):
        """Test bonus for clean security scan."""
        signals = DeterministicSignals(security_passed=True)
        bonus = signals.calculate_bonus()
        assert bonus >= 5.0

    def test_bonus_is_capped(self):
        """Test that total bonus is capped at 25."""
        signals = DeterministicSignals(
            test_coverage=95.0,
            lint_passed=True,
            lint_errors=0,
            type_check_passed=True,
            type_errors=0,
            tests_passed=True,
            tests_total=100,
            tests_failed=0,
            security_passed=True,
        )
        bonus = signals.calculate_bonus()
        assert bonus <= 25.0


class TestApplyDeterministicSignals:
    """Test applying signals to adjust quality score."""

    @pytest.fixture
    def scorer(self):
        return QualityScorer()

    def test_failing_tests_cap_score(self, scorer):
        """Test that failing tests cap the score."""
        signals = DeterministicSignals(
            tests_total=10,
            tests_failed=5,  # 50% failure
        )

        adjusted, details = scorer.apply_deterministic_signals(95.0, signals)

        # Should be capped (50% failure = cap at 40 or 50)
        assert adjusted <= 50.0
        assert details["signals_applied"] is True
        assert len(details["hard_failures"]) > 0

    def test_critical_security_caps_score(self, scorer):
        """Test that critical security issues cap the score."""
        signals = DeterministicSignals(security_critical=1)

        adjusted, details = scorer.apply_deterministic_signals(90.0, signals)

        assert adjusted == 30.0  # Critical = 30 cap
        assert "Critical security" in details["hard_failures"][0]

    def test_bonus_applied_without_failures(self, scorer):
        """Test that bonuses are applied when no failures."""
        signals = DeterministicSignals(
            tests_passed=True,
            tests_total=50,
            tests_failed=0,
            test_coverage=85.0,
            lint_passed=True,
            lint_errors=0,
        )

        adjusted, details = scorer.apply_deterministic_signals(70.0, signals)

        # Should be higher than base due to bonuses
        assert adjusted > 70.0
        assert len(details["bonuses"]) > 0

    def test_bonus_not_applied_with_failures(self, scorer):
        """Test that bonuses are NOT applied when hard failures exist."""
        signals = DeterministicSignals(
            tests_passed=False,
            tests_total=10,
            tests_failed=2,
            test_coverage=85.0,  # Good coverage, but tests failing
            lint_passed=True,
            lint_errors=0,
        )

        adjusted, details = scorer.apply_deterministic_signals(80.0, signals)

        # Should be capped due to failures, bonus ignored
        assert adjusted <= 60.0  # Low failure cap


class TestEvaluateWithSignals:
    """Test the combined evaluation with signals."""

    @pytest.fixture
    def scorer(self):
        return QualityScorer()

    def test_signals_grounded_in_metadata(self, scorer):
        """Test that signals are recorded in metadata."""
        signals = DeterministicSignals(
            tests_passed=True,
            tests_total=10,
            tests_failed=0,
        )

        assessment = scorer.evaluate_with_signals(
            output={"success": True},
            context={},
            signals=signals,
        )

        assert assessment.metadata.get("signals_grounded") is True
        assert "deterministic_signals" in assessment.metadata

    def test_hard_failures_added_to_improvements(self, scorer):
        """Test that hard failures are added to improvements list."""
        signals = DeterministicSignals(
            tests_total=10,
            tests_failed=3,
        )

        assessment = scorer.evaluate_with_signals(
            output={"success": True},
            context={},
            signals=signals,
        )

        # Should have FIX: prefix for hard failures
        fix_items = [i for i in assessment.improvements_needed if i.startswith("FIX:")]
        assert len(fix_items) > 0


class TestSignalsFromContext:
    """Test extracting signals from context dictionary."""

    def test_extracts_test_results(self):
        """Test extracting test results from context."""
        context = {
            "test_results": {
                "total": 100,
                "failed": 5,
                "passed": True,
                "coverage": 0.85,  # 85% as decimal
            }
        }

        signals = QualityScorer.signals_from_context(context)

        assert signals.tests_total == 100
        assert signals.tests_failed == 5
        assert signals.test_coverage == 85.0

    def test_extracts_lint_results(self):
        """Test extracting lint results from context."""
        context = {
            "lint_results": {
                "passed": True,
                "errors": 0,
                "warnings": 3,
            }
        }

        signals = QualityScorer.signals_from_context(context)

        assert signals.lint_passed is True
        assert signals.lint_errors == 0
        assert signals.lint_warnings == 3

    def test_extracts_security_scan(self):
        """Test extracting security scan results from context."""
        context = {
            "security_scan": {
                "passed": False,
                "critical": 2,
                "high": 5,
            }
        }

        signals = QualityScorer.signals_from_context(context)

        assert signals.security_passed is False
        assert signals.security_critical == 2
        assert signals.security_high == 5

    def test_handles_missing_context(self):
        """Test graceful handling of missing context keys."""
        context = {}

        signals = QualityScorer.signals_from_context(context)

        # Should return defaults, not crash
        assert signals.tests_passed is False
        assert signals.lint_passed is False

    def test_coverage_as_percentage(self):
        """Test that coverage percentage (>1) is handled correctly."""
        context = {
            "test_results": {
                "coverage": 75,  # Already a percentage
            }
        }

        signals = QualityScorer.signals_from_context(context)

        assert signals.test_coverage == 75.0
