"""Unit tests for the blended quality scorer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from SuperClaude.MCP.coderabbit import CodeRabbitIssue, CodeRabbitReview
from SuperClaude.Quality.quality_scorer import (
    QualityDimension,
    QualityMetric,
    QualityScorer,
)


def _sample_metrics() -> list:
    return [
        QualityMetric(QualityDimension.CORRECTNESS, 80, 0.25, "correctness"),
        QualityMetric(QualityDimension.COMPLETENESS, 70, 0.20, "completeness"),
        QualityMetric(QualityDimension.TESTABILITY, 60, 0.10, "tests"),
    ]


def _review(score: float = 88.0, degraded: bool = False) -> CodeRabbitReview:
    return CodeRabbitReview(
        repo="org/repo",
        pr_number=1,
        score=score,
        status="ok",
        summary="",
        issues=[
            CodeRabbitIssue(title="security", body="xss", severity="high")
        ],
        raw={"score": score},
        received_at=datetime.now(timezone.utc),
        degraded=degraded,
        degraded_reason="cache" if degraded else None,
    )


def test_weighted_formula_with_coderabbit():
    scorer = QualityScorer()
    metrics = _sample_metrics()
    review = _review()

    score, meta = scorer._calculate_overall_score(metrics, {"coderabbit_review": review})
    expected = (80 * 0.35) + (88 * 0.35) + (70 * 0.15) + (60 * 0.15)
    assert pytest.approx(score, rel=1e-6) == expected
    assert meta["coderabbit_status"] == "available"
    assert pytest.approx(meta["weights"]["coderabbit"], rel=1e-6) == 0.35


def test_renormalizes_weights_when_coderabbit_missing():
    scorer = QualityScorer()
    metrics = _sample_metrics()

    score, meta = scorer._calculate_overall_score(metrics, {})
    total_weight = 0.35 + 0.15 + 0.15
    expected = (80 * 0.35 + 70 * 0.15 + 60 * 0.15) / total_weight
    assert pytest.approx(score, rel=1e-6) == expected
    assert meta["coderabbit_status"] == "missing"
    assert "coderabbit" not in meta["weights"]


def test_calculate_score_exposes_band():
    scorer = QualityScorer()
    score = scorer.calculate_score({
        "correctness": 92,
        "completeness": 88,
        "coderabbit": 91,
        "test_coverage": 95,
    })
    assert score["band"] == "production_ready"
    assert score["grade"] == "Excellent"


def test_threshold_classification():
    scorer = QualityScorer()
    thresholds = scorer.thresholds
    assert thresholds.classify(thresholds.production_ready + 1) == "production_ready"
    assert thresholds.classify(thresholds.needs_attention + 0.1) == "needs_attention"
    assert thresholds.classify(thresholds.iterate - 1) == "iterate"
