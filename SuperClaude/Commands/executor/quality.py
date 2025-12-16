"""
Quality utilities for the SuperClaude Command Executor.

Provides helper functions for quality assessment serialization,
validation, and result formatting.
"""

import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def serialize_assessment(assessment: Any) -> Dict[str, Any]:
    """Convert a QualityAssessment dataclass into JSON-serializable dict.

    Args:
        assessment: QualityAssessment instance with metrics and timestamp.

    Returns:
        Dictionary suitable for JSON serialization.
    """
    data = asdict(assessment)

    timestamp = getattr(assessment, "timestamp", None)
    if isinstance(timestamp, datetime):
        data["timestamp"] = timestamp.isoformat()

    metrics = data.get("metrics", [])
    for metric in metrics:
        dimension = metric.get("dimension")
        if hasattr(dimension, "value"):
            metric["dimension"] = dimension.value

    return data


def format_quality_summary(
    overall_score: float,
    threshold: float,
    passed: bool,
    metrics: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Format a quality assessment into a human-readable summary.

    Args:
        overall_score: The overall quality score.
        threshold: The passing threshold.
        passed: Whether the assessment passed.
        metrics: Optional list of metric dictionaries.

    Returns:
        Formatted summary string.
    """
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"Quality Assessment: {status}",
        f"Score: {overall_score:.1f} / {threshold:.1f}",
    ]

    if metrics:
        lines.append("Dimensions:")
        for metric in metrics:
            dimension = metric.get("dimension", "unknown")
            score = metric.get("score", 0.0)
            lines.append(f"  - {dimension}: {score:.1f}")

    return "\n".join(lines)


def extract_quality_improvements(
    assessment: Any,
) -> List[str]:
    """Extract the improvements_needed list from an assessment.

    Args:
        assessment: QualityAssessment with improvements_needed attribute.

    Returns:
        List of improvement strings.
    """
    if not assessment:
        return []

    improvements = getattr(assessment, "improvements_needed", None)
    if isinstance(improvements, list):
        return [str(item) for item in improvements if item]

    return []


def calculate_pass_rate(passed: int, failed: int, errored: int = 0) -> float:
    """Calculate the pass rate from test counts.

    Args:
        passed: Number of passed tests.
        failed: Number of failed tests.
        errored: Number of errored tests.

    Returns:
        Pass rate as a float between 0.0 and 1.0.
    """
    total = passed + failed + errored
    if total == 0:
        return 1.0
    return passed / total


def derive_quality_status(
    has_changes: bool,
    assessment_passed: Optional[bool],
    consensus_reached: Optional[bool],
    static_issues: Optional[List[str]] = None,
) -> str:
    """Derive the overall quality status from multiple signals.

    Args:
        has_changes: Whether file changes were applied.
        assessment_passed: Whether the quality assessment passed.
        consensus_reached: Whether consensus was reached.
        static_issues: List of static analysis issues.

    Returns:
        Status string: 'complete', 'partial', or 'plan-only'.
    """
    if not has_changes:
        return "plan-only"

    if static_issues:
        return "partial"

    if assessment_passed is False:
        return "partial"

    if consensus_reached is False:
        return "partial"

    return "complete"


def validate_quality_threshold(
    score: float,
    threshold: float,
    strict: bool = False,
) -> Tuple[bool, str]:
    """Validate whether a score meets the threshold.

    Args:
        score: The quality score to validate.
        threshold: The minimum acceptable score.
        strict: If True, score must strictly exceed threshold.

    Returns:
        Tuple of (passed, message).
    """
    if strict:
        passed = score > threshold
        operator = ">"
    else:
        passed = score >= threshold
        operator = ">="

    if passed:
        message = f"Score {score:.1f} {operator} threshold {threshold:.1f}: PASSED"
    else:
        message = f"Score {score:.1f} < threshold {threshold:.1f}: FAILED"

    return passed, message


def aggregate_dimension_scores(
    metrics: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Aggregate dimension scores into an overall score.

    Args:
        metrics: List of metric dictionaries with 'dimension' and 'score'.
        weights: Optional weights per dimension. Defaults to equal weights.

    Returns:
        Weighted average score.
    """
    if not metrics:
        return 0.0

    if weights is None:
        weights = {}

    total_weight = 0.0
    weighted_sum = 0.0

    for metric in metrics:
        dimension = metric.get("dimension", "unknown")
        score = float(metric.get("score", 0.0))
        weight = weights.get(str(dimension), 1.0)
        weighted_sum += score * weight
        total_weight += weight

    if total_weight == 0.0:
        return 0.0

    return weighted_sum / total_weight


def build_quality_context(
    status: str,
    changed_files: List[str],
    results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build an evaluation context dictionary for quality scoring.

    Args:
        status: Current execution status.
        changed_files: List of changed file paths.
        results: Optional existing results to include.

    Returns:
        Context dictionary for the quality scorer.
    """
    context = dict(results or {})
    context["status"] = status
    context["changed_files"] = changed_files
    return context


__all__ = [
    "aggregate_dimension_scores",
    "build_quality_context",
    "calculate_pass_rate",
    "derive_quality_status",
    "extract_quality_improvements",
    "format_quality_summary",
    "serialize_assessment",
    "validate_quality_threshold",
]
