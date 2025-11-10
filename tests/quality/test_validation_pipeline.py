"""Tests for the validation pipeline."""

from __future__ import annotations

from SuperClaude.Quality.validation_pipeline import ValidationPipeline


def test_pipeline_short_circuits_on_fatal_security(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path / "metrics"))
    pipeline = ValidationPipeline()
    context = {
        "syntax_report": {"errors": []},
        "security_scan": {
            "issues": [
                {"message": "Critical vuln", "severity": "critical"},
            ]
        },
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


def test_security_stage_degraded_without_scan(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path / "metrics"))
    pipeline = ValidationPipeline()
    context = {
        "syntax_report": {"errors": []},
        "test_results": {"failed": 0},
    }

    results = pipeline.run(context)
    security_result = next(r for r in results if r.name == "security")
    assert security_result.status == "degraded"
    assert security_result.degraded is True
    assert "scanner" in security_result.metadata
    assert security_result.evidence_path and security_result.evidence_path.exists()


def test_pipeline_marks_test_stage_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path / "metrics"))
    pipeline = ValidationPipeline()
    context = {
        "syntax_report": {"errors": []},
        "security_scan": {"issues": []},
        "test_results": {"failed": 2},
    }

    results = pipeline.run(context)
    tests_result = next(r for r in results if r.name == "tests")
    assert tests_result.status == "failed"
    assert tests_result.fatal is True
    assert tests_result.evidence_path and tests_result.evidence_path.exists()
