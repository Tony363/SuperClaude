"""Unit tests for the blended quality scorer."""

from __future__ import annotations

import pytest

from SuperClaude.Quality.quality_scorer import (
    QualityDimension,
    QualityMetric,
    QualityScorer,
)


def _sample_metrics(include_tests: bool = True) -> list:
    metrics = [
        QualityMetric(QualityDimension.CORRECTNESS, 80, 0.25, "correctness"),
        QualityMetric(QualityDimension.COMPLETENESS, 70, 0.20, "completeness"),
    ]
    if include_tests:
        metrics.append(QualityMetric(QualityDimension.TESTABILITY, 60, 0.10, "tests"))
    return metrics


def test_weighted_formula_without_external_signal():
    scorer = QualityScorer()
    metrics = _sample_metrics()

    score, meta = scorer._calculate_overall_score(metrics, {})
    expected = (80 * 0.6) + (70 * 0.25) + (60 * 0.15)
    assert pytest.approx(score, rel=1e-6) == expected
    assert set(meta["weights"].keys()) == {
        "superclaude",
        "completeness",
        "test_coverage",
    }


def test_renormalizes_weights_when_component_missing():
    scorer = QualityScorer()
    metrics = _sample_metrics(include_tests=False)

    score, meta = scorer._calculate_overall_score(metrics, {})
    total_weight = 0.6 + 0.25
    expected = (80 * 0.6 + 70 * 0.25) / total_weight
    assert pytest.approx(score, rel=1e-6) == expected
    assert "test_coverage" not in meta["weights"]


def test_calculate_score_exposes_band():
    scorer = QualityScorer()
    score = scorer.calculate_score(
        {
            "correctness": 95,
            "completeness": 93,
            "test_coverage": 97,
        }
    )
    assert score["band"] == "production_ready"
    assert score["grade"] == "Excellent"


def test_threshold_classification():
    scorer = QualityScorer()
    thresholds = scorer.thresholds
    assert thresholds.classify(thresholds.production_ready + 1) == "production_ready"
    assert thresholds.classify(thresholds.needs_attention + 0.1) == "needs_attention"
    assert thresholds.classify(thresholds.iterate - 1) == "iterate"


def test_primary_evaluator_short_circuits_default_metrics():
    scorer = QualityScorer()

    def _primary(_, __, iteration):
        assert iteration == 0
        metric = QualityMetric(QualityDimension.PAL_REVIEW, 97, 1.0, "pal review")
        return {
            "metrics": [metric],
            "improvements": ["tighten tests"],
            "metadata": {"pal": True},
        }

    scorer.set_primary_evaluator(_primary)
    assessment = scorer.evaluate({}, {}, iteration=0)
    assert assessment.metrics[0].dimension == QualityDimension.PAL_REVIEW
    assert assessment.improvements_needed == ["tighten tests"]
    assert assessment.metadata.get("pal") is True
    scorer.clear_primary_evaluator()
