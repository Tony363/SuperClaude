"""
Quality Assessment - Score output based on evidence from SDK hooks.

Quality is assessed using deterministic signals (evidence) rather than
LLM self-evaluation. This ensures consistent, reproducible scoring.

Scoring Dimensions:
- Code Changes: Were files actually modified?
- Test Execution: Were tests run?
- Test Results: Did tests pass?
- Code Coverage: Is coverage sufficient?
- Build Status: Does the build pass?
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .evidence import EvidenceCollector


class QualityBand(Enum):
    """Quality score bands for categorization."""

    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 70-89
    ACCEPTABLE = "acceptable"  # 50-69
    NEEDS_WORK = "needs_work"  # 30-49
    POOR = "poor"  # 0-29


@dataclass
class QualityAssessment:
    """
    Quality assessment result.

    Attributes:
        score: Overall quality score (0-100)
        passed: Whether score meets threshold
        band: Quality band categorization
        improvements_needed: List of suggested improvements
        dimension_scores: Breakdown by dimension
    """

    score: float
    passed: bool
    band: QualityBand
    improvements_needed: list[str] = field(default_factory=list)
    dimension_scores: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_score(cls, score: float, threshold: float = 70.0) -> "QualityAssessment":
        """Create assessment from a score."""
        band = cls._score_to_band(score)
        return cls(
            score=score,
            passed=score >= threshold,
            band=band,
            improvements_needed=[],
            dimension_scores={},
        )

    @staticmethod
    def _score_to_band(score: float) -> QualityBand:
        """Convert score to quality band."""
        if score >= 90:
            return QualityBand.EXCELLENT
        elif score >= 70:
            return QualityBand.GOOD
        elif score >= 50:
            return QualityBand.ACCEPTABLE
        elif score >= 30:
            return QualityBand.NEEDS_WORK
        else:
            return QualityBand.POOR


@dataclass
class QualityConfig:
    """Configuration for quality assessment."""

    # Dimension weights (must sum to 1.0)
    weight_code_changes: float = 0.30
    weight_tests_run: float = 0.25
    weight_tests_pass: float = 0.25
    weight_coverage: float = 0.10
    weight_no_errors: float = 0.10

    # Thresholds
    min_coverage: float = 80.0  # Minimum coverage percentage
    quality_threshold: float = 70.0  # Score to pass

    # Scoring
    max_score: float = 100.0


def assess_quality(
    evidence: EvidenceCollector,
    config: QualityConfig | None = None,
) -> QualityAssessment:
    """
    Assess quality based on collected evidence.

    Uses deterministic signals from tool outputs rather than
    LLM self-evaluation. This ensures consistent scoring.

    Args:
        evidence: Evidence collected via SDK hooks
        config: Quality assessment configuration

    Returns:
        QualityAssessment with score and improvement suggestions
    """
    if config is None:
        config = QualityConfig()

    score = 0.0
    improvements: list[str] = []
    dimension_scores: dict[str, float] = {}

    # Dimension 1: Code Changes (30%)
    code_change_score = _score_code_changes(evidence)
    dimension_scores["code_changes"] = code_change_score
    score += code_change_score * config.weight_code_changes

    if code_change_score < 100:
        if not evidence.files_written and not evidence.files_edited:
            improvements.append("No code changes detected - verify implementation")

    # Dimension 2: Tests Run (25%)
    tests_run_score = _score_tests_run(evidence)
    dimension_scores["tests_run"] = tests_run_score
    score += tests_run_score * config.weight_tests_run

    if tests_run_score < 100:
        improvements.append("Run tests to verify changes work correctly")

    # Dimension 3: Tests Pass (25%)
    tests_pass_score = _score_tests_pass(evidence)
    dimension_scores["tests_pass"] = tests_pass_score
    score += tests_pass_score * config.weight_tests_pass

    if evidence.tests_run and evidence.total_tests_failed > 0:
        improvements.append(f"Fix {evidence.total_tests_failed} failing test(s)")

    # Dimension 4: Coverage (10%)
    coverage_score = _score_coverage(evidence, config.min_coverage)
    dimension_scores["coverage"] = coverage_score
    score += coverage_score * config.weight_coverage

    if coverage_score < 100 and evidence.tests_run:
        avg_coverage = _get_average_coverage(evidence)
        if avg_coverage > 0:
            improvements.append(
                f"Increase test coverage from {avg_coverage:.1f}% to {config.min_coverage}%"
            )

    # Dimension 5: No Errors (10%)
    no_errors_score = _score_no_errors(evidence)
    dimension_scores["no_errors"] = no_errors_score
    score += no_errors_score * config.weight_no_errors

    if no_errors_score < 100:
        improvements.append("Fix errors in test or command output")

    # Apply caps for critical failures
    if evidence.tests_run and evidence.total_tests_failed > evidence.total_tests_passed:
        # More failing than passing = cap at 40
        score = min(score, 40.0)
        improvements.insert(0, "CRITICAL: Majority of tests failing")

    # Round score
    score = round(score, 1)

    return QualityAssessment(
        score=score,
        passed=score >= config.quality_threshold,
        band=QualityAssessment._score_to_band(score),
        improvements_needed=improvements[:5],  # Top 5 improvements
        dimension_scores=dimension_scores,
    )


def _score_code_changes(evidence: EvidenceCollector) -> float:
    """Score based on code changes made."""
    if evidence.files_written or evidence.files_edited:
        # Bonus for multiple files changed
        total = evidence.total_files_modified
        if total >= 3:
            return 100.0
        elif total >= 1:
            return 80.0
    return 0.0


def _score_tests_run(evidence: EvidenceCollector) -> float:
    """Score based on whether tests were run."""
    if evidence.tests_run:
        return 100.0
    return 0.0


def _score_tests_pass(evidence: EvidenceCollector) -> float:
    """Score based on test pass rate."""
    if not evidence.tests_run:
        return 50.0  # Neutral if no tests

    total = evidence.total_tests_passed + evidence.total_tests_failed
    if total == 0:
        return 50.0

    pass_rate = evidence.total_tests_passed / total
    return pass_rate * 100.0


def _score_coverage(evidence: EvidenceCollector, min_coverage: float) -> float:
    """Score based on code coverage."""
    if not evidence.tests_run:
        return 50.0  # Neutral if no tests

    avg_coverage = _get_average_coverage(evidence)
    if avg_coverage <= 0:
        return 50.0  # No coverage data

    if avg_coverage >= min_coverage:
        return 100.0
    else:
        # Partial credit
        return (avg_coverage / min_coverage) * 100.0


def _get_average_coverage(evidence: EvidenceCollector) -> float:
    """Get average coverage across test results."""
    coverages = [r.coverage for r in evidence.test_results if r.coverage > 0]
    if not coverages:
        return 0.0
    return sum(coverages) / len(coverages)


def _score_no_errors(evidence: EvidenceCollector) -> float:
    """Score based on absence of errors."""
    # Check for errors in test results
    total_errors = sum(r.errors for r in evidence.test_results)
    if total_errors > 0:
        return 0.0

    # Check for error patterns in command output
    error_patterns = ["error:", "exception:", "traceback:", "failed:"]
    for cmd in evidence.commands_run:
        output_lower = cmd.output.lower()
        for pattern in error_patterns:
            if pattern in output_lower:
                return 50.0  # Partial credit

    return 100.0


def compare_assessments(
    current: QualityAssessment,
    previous: QualityAssessment,
) -> dict[str, Any]:
    """
    Compare two assessments to track progress.

    Args:
        current: Current iteration's assessment
        previous: Previous iteration's assessment

    Returns:
        Comparison metrics
    """
    delta = current.score - previous.score

    return {
        "score_delta": round(delta, 1),
        "improved": delta > 0,
        "regressed": delta < 0,
        "stagnant": abs(delta) < 2.0,
        "current_band": current.band.value,
        "previous_band": previous.band.value,
        "band_changed": current.band != previous.band,
    }
