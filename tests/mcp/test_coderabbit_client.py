"""Tests for the CodeRabbit MCP client."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest

from SuperClaude.MCP.coderabbit import (
    CodeRabbitClient,
    NetworkError,
    RateLimitError,
    scrub_secrets,
)


def _base_config(tmp_path: Path) -> Dict[str, object]:
    return {
        "enabled": True,
        "endpoint": "https://example.invalid/api",
        "cache_filename": "coderabbit_cache.json",
        "telemetry": {"filename": "coderabbit_telemetry.jsonl"},
        "retry_policy": {
            "max_attempts": 3,
            "backoff_seconds": 0.0,
            "max_backoff_seconds": 0.0,
            "jitter_seconds": 0.0,
        },
        "requires_network": False,
    }


def test_review_pull_request_success_and_cache(tmp_path, monkeypatch):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(metrics_dir))

    payloads = []

    def fake_transport(payload):
        payloads.append(payload)
        return {
            "score": 91,
            "status": "ok",
            "summary": "Solid PR",
            "issues": [
                {
                    "title": "Nit",
                    "body": "Consider renaming variable",
                    "severity": "info",
                    "file_path": "app.py",
                    "line": 12,
                }
            ],
        }

    client = CodeRabbitClient(config=_base_config(tmp_path), transport=fake_transport)

    review = client.review_pull_request(repo="org/repo", pr_number=7)
    assert review.score == 91
    assert review.summary == "Solid PR"
    assert len(review.issues) == 1
    assert payloads[0]["repo"] == "org/repo"

    # Second call should hit cache and avoid the transport
    payloads.clear()
    cached_review = client.review_pull_request(repo="org/repo", pr_number=7)
    assert cached_review.score == 91
    assert not payloads

    telemetry_path = metrics_dir / "coderabbit_telemetry.jsonl"
    assert telemetry_path.exists()
    entries = [json.loads(line) for line in telemetry_path.read_text().splitlines() if line.strip()]
    assert any(entry["event"] == "review.success" for entry in entries)


def test_retry_logic_on_transient_errors(tmp_path, monkeypatch):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(metrics_dir))

    attempts = {"count": 0}

    def flaky_transport(payload):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise NetworkError("temporary network issue")
        return {"score": 80, "status": "ok"}

    client = CodeRabbitClient(config=_base_config(tmp_path), transport=flaky_transport)
    review = client.review_pull_request(repo="org/proj", pr_number=5)
    assert review.score == 80
    assert attempts["count"] == 3


def test_fallback_to_cached_review_on_failure(tmp_path, monkeypatch):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(metrics_dir))

    success_client = CodeRabbitClient(
        config=_base_config(tmp_path),
        transport=lambda payload: {"score": 70, "status": "ok"},
    )
    success_client.review_pull_request(repo="org/repo", pr_number=8)

    def failing_transport(_payload):
        raise RateLimitError("rate limited")

    failing_client = CodeRabbitClient(config=_base_config(tmp_path), transport=failing_transport)

    review = failing_client.review_pull_request(repo="org/repo", pr_number=8, force_refresh=True)
    assert review.score == 70
    assert review.degraded
    assert "rate limited" in (review.degraded_reason or "")


def test_scrub_secrets_redacts_sensitive_keys():
    payload = {
        "token": "secret",
        "Authorization": "Bearer abc",
        "nested": {"api_key": "xyz", "safe": "ok"},
    }
    scrubbed = scrub_secrets(payload)
    assert scrubbed["token"] == "<redacted>"
    assert scrubbed["Authorization"] == "<redacted>"
    assert scrubbed["nested"]["api_key"] == "<redacted>"
    assert scrubbed["nested"]["safe"] == "ok"
