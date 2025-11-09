from __future__ import annotations

from datetime import datetime, timezone

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands.executor import CommandContext
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata
from SuperClaude.MCP.coderabbit import CodeRabbitError, CodeRabbitIssue, CodeRabbitReview
from SuperClaude.Quality.quality_scorer import QualityAssessment


class DummyCoderabbitClient:
    def __init__(self, score: float = 91.0):
        self.score = score
        self.calls = []
        self.raise_error: Exception | None = None
        self.degraded = False

    def review_pull_request(self, repo: str, pr_number: int, **_: object) -> CodeRabbitReview:
        self.calls.append((repo, pr_number))
        if self.raise_error:
            raise self.raise_error
        return CodeRabbitReview(
            repo=repo,
            pr_number=pr_number,
            score=self.score,
            status="ok",
            summary="",
            issues=[
                CodeRabbitIssue(title="Sanitize input", body="escape html", severity="high", tag="security"),
                CodeRabbitIssue(title="Rename var", body="improve clarity", severity="info", tag="style"),
            ],
            raw={"score": self.score},
            received_at=datetime.now(timezone.utc),
            degraded=self.degraded,
            degraded_reason="cache" if self.degraded else None,
        )


@pytest.fixture
def executor(monkeypatch, tmp_path) -> CommandExecutor:
    monkeypatch.chdir(tmp_path)
    registry = CommandRegistry()
    parser = CommandParser()
    return CommandExecutor(registry, parser)


def _make_context() -> CommandContext:
    parsed = ParsedCommand(name="implement", raw_string="/sc:implement")
    metadata = CommandMetadata(
        name="implement",
        description="",
        category="test",
        complexity="standard",
    )
    return CommandContext(command=parsed, metadata=metadata)


def test_attach_coderabbit_review_populates_context(executor, monkeypatch):
    monkeypatch.setenv("CODERABBIT_REPO", "org/repo")
    monkeypatch.setenv("CODERABBIT_PR_NUMBER", "77")
    executor.coderabbit_client = DummyCoderabbitClient()

    context = _make_context()
    evaluation_context = {}
    review = executor._attach_coderabbit_review(context, evaluation_context)

    assert executor.coderabbit_client.calls == [("org/repo", 77)]
    assert review is evaluation_context.get("coderabbit_review")
    assert evaluation_context.get("coderabbit_status") == "available"
    assert context.results['coderabbit_review_data']['score'] == pytest.approx(91.0)


def test_attach_coderabbit_review_handles_missing_env(executor, monkeypatch):
    monkeypatch.delenv("CODERABBIT_REPO", raising=False)
    monkeypatch.delenv("CODERABBIT_PR_NUMBER", raising=False)
    executor.coderabbit_client = DummyCoderabbitClient()

    context = _make_context()
    evaluation_context = {}
    review = executor._attach_coderabbit_review(context, evaluation_context)

    assert review is None
    assert evaluation_context.get("coderabbit_status") == "missing"
    assert "coderabbit_review_data" not in context.results


def test_attach_coderabbit_review_handles_client_error(executor, monkeypatch):
    monkeypatch.setenv("CODERABBIT_REPO", "org/repo")
    monkeypatch.setenv("CODERABBIT_PR_NUMBER", "77")
    failing = DummyCoderabbitClient()
    failing.raise_error = CodeRabbitError("network down")
    executor.coderabbit_client = failing

    context = _make_context()
    evaluation_context = {}
    review = executor._attach_coderabbit_review(context, evaluation_context)

    assert review is None
    assert evaluation_context.get("coderabbit_status") == "error"
    assert "network down" in evaluation_context.get("coderabbit_error", "")


def test_route_coderabbit_feedback_groups_taxonomy(executor):
    review = DummyCoderabbitClient().review_pull_request("org/repo", 5)
    context = _make_context()
    context.results['coderabbit_review_data'] = review.to_dict()
    assessment = QualityAssessment(
        overall_score=78.0,
        metrics=[],
        timestamp=datetime.now(),
        iteration=0,
        passed=False,
        threshold=90.0,
        context={},
        band="needs_attention",
    )

    executor._route_coderabbit_feedback(context, assessment)
    briefs = context.results.get('coderabbit_briefs') or []
    assert briefs, "Expected taxonomy briefs to be recorded"
    buckets = {brief['taxonomy'] for brief in briefs}
    assert 'security' in buckets
    assert 'style' in buckets


def test_route_coderabbit_feedback_skips_when_degraded(executor):
    client = DummyCoderabbitClient()
    client.degraded = True
    review = client.review_pull_request("org/repo", 5)
    context = _make_context()
    payload = review.to_dict()
    payload['issues'] = []
    context.results['coderabbit_review_data'] = payload
    assessment = QualityAssessment(
        overall_score=78.0,
        metrics=[],
        timestamp=datetime.now(),
        iteration=0,
        passed=False,
        threshold=90.0,
        context={},
        band="needs_attention",
    )

    executor._route_coderabbit_feedback(context, assessment)
    briefs = context.results.get('coderabbit_briefs') or []
    assert briefs == []
    assert context.results.get('coderabbit_review_data', {}).get('degraded') is True
