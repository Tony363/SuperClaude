"""Tests for the CodeRabbit gate CLI helper."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from SuperClaude.MCP.coderabbit import CodeRabbitError, CodeRabbitIssue, CodeRabbitReview
from SuperClaude.Quality import coderabbit_gate


def _review(score: float, *, degraded: bool = False) -> CodeRabbitReview:
    return CodeRabbitReview(
        repo="org/repo",
        pr_number=7,
        score=score,
        status="ok",
        summary="",
        issues=[CodeRabbitIssue(title="nit", body="fix", severity="info")],
        raw={"score": score},
        received_at=datetime.now(timezone.utc),
        degraded=degraded,
        degraded_reason="cache" if degraded else None,
    )


class StubClient:
    def __init__(self, review: CodeRabbitReview | None = None, error: Exception | None = None):
        self.review = review
        self.error = error

    def review_pull_request(self, **_: object) -> CodeRabbitReview:
        if self.error:
            raise self.error
        assert self.review is not None
        return self.review


def _metrics_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".superclaude_metrics"
    path.mkdir()
    return path


def test_gate_passes_when_score_above_threshold(tmp_path):
    client = StubClient(review=_review(94))
    result = coderabbit_gate.run_gate(
        repo="org/repo",
        pr_number=7,
        threshold=90.0,
        allow_degraded=False,
        client=client,
        config={},
        metrics_dir=_metrics_dir(tmp_path),
    )
    assert result.status == "passed"
    assert result.score == pytest.approx(94)


def test_gate_blocks_when_score_below_threshold(tmp_path):
    client = StubClient(review=_review(70))
    result = coderabbit_gate.run_gate(
        repo="org/repo",
        pr_number=7,
        threshold=80.0,
        allow_degraded=False,
        client=client,
        config={},
        metrics_dir=_metrics_dir(tmp_path),
    )
    assert result.status == "failed"
    assert "gate failed" in result.message


def test_gate_degrades_when_client_errors_and_allowed(tmp_path):
    client = StubClient(error=CodeRabbitError("network"))
    result = coderabbit_gate.run_gate(
        repo="org/repo",
        pr_number=9,
        threshold=80.0,
        allow_degraded=True,
        client=client,
        config={},
        metrics_dir=_metrics_dir(tmp_path),
    )
    assert result.status == "degraded"
    assert result.degraded is True


def test_gate_errors_when_review_degraded_and_not_allowed(tmp_path):
    client = StubClient(review=_review(88, degraded=True))
    result = coderabbit_gate.run_gate(
        repo="org/repo",
        pr_number=9,
        threshold=80.0,
        allow_degraded=False,
        client=client,
        config={},
        metrics_dir=_metrics_dir(tmp_path),
    )
    assert result.status == "error"
    assert result.degraded is True
