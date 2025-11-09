"""Tests for the validation pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from SuperClaude.MCP.coderabbit import CodeRabbitIssue, CodeRabbitReview
from SuperClaude.Quality.validation_pipeline import ValidationPipeline


def _make_review(severity: str = "critical") -> CodeRabbitReview:
    return CodeRabbitReview(
        repo="org/repo",
        pr_number=42,
        score=85,
        status="ok",
        summary="",
        issues=[CodeRabbitIssue(title="security", body="details", severity=severity)],
        raw={},
        received_at=datetime.now(timezone.utc),
    )


def test_pipeline_short_circuits_on_fatal_security(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path / "metrics"))
    pipeline = ValidationPipeline()
    context = {
        "syntax_report": {"errors": []},
        "coderabbit_review": _make_review("critical"),
        "security_scan": {"issues": []},
        "test_results": {"failed": 0},
    }

    results = pipeline.run(context)
    status_map = {result.name: result for result in results}
    assert status_map["security"].status == "failed"
    assert status_map["security"].fatal is True
    for stage in ("style", "tests", "performance"):
        assert status_map[stage].status == "skipped"
    evidence_path = status_map["security"].evidence_path
    assert evidence_path and evidence_path.exists()


def test_security_stage_degraded_without_coderabbit(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path / "metrics"))
    pipeline = ValidationPipeline()
    context = {
        "syntax_report": {"errors": []},
        "security_scan": {"issues": []},
        "test_results": {"failed": 0},
    }

    results = pipeline.run(context)
    security_result = next(r for r in results if r.name == "security")
    assert security_result.status == "passed"
    assert security_result.degraded is True
    assert security_result.metadata["coderabbit_status"] == "missing"
    assert security_result.evidence_path and security_result.evidence_path.exists()


def test_pipeline_marks_test_stage_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path / "metrics"))
    pipeline = ValidationPipeline()
    context = {
        "syntax_report": {"errors": []},
        "coderabbit_review": _make_review("info"),
        "security_scan": {"issues": []},
        "test_results": {"failed": 2},
    }

    results = pipeline.run(context)
    tests_result = next(r for r in results if r.name == "tests")
    assert tests_result.status == "failed"
    assert tests_result.fatal is True
    assert tests_result.evidence_path and tests_result.evidence_path.exists()
