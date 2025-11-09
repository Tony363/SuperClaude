from __future__ import annotations

from datetime import datetime, timezone

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands.executor import CommandContext
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata
from SuperClaude.MCP.coderabbit import CodeRabbitIssue, CodeRabbitReview
from SuperClaude.Quality.quality_scorer import QualityAssessment


class DummyCoderabbitClient:
    def __init__(self, score: float = 91.0):
        self.score = score
        self.calls = []

    def review_pull_request(self, repo: str, pr_number: int, **_: object) -> CodeRabbitReview:
        self.calls.append((repo, pr_number))
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
