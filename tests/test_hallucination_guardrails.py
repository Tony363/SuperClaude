import os
from pathlib import Path

import pytest

os.environ.setdefault("SUPERCLAUDE_OFFLINE_MODE", "1")

from SuperClaude.Commands.executor import CommandExecutor
from SuperClaude.Commands.parser import CommandParser
from SuperClaude.Commands.registry import CommandRegistry
from SuperClaude.ModelRouter.consensus import ConsensusBuilder, ModelVote, VoteType
from SuperClaude.Retrieval import RepoRetriever


class DummyMonitor:
    def __init__(self) -> None:
        self.metrics = []
        self.events = []

    def record_metric(self, name, value, metric_type, tags=None):  # noqa: D401
        self.metrics.append((name, value, metric_type, tags))

    def record_event(self, event_type, data):  # noqa: D401
        self.events.append((event_type, data))


def build_executor(tmp_path: Path) -> CommandExecutor:
    registry = CommandRegistry()
    parser = CommandParser(registry)
    executor = CommandExecutor(registry, parser)
    executor.repo_root = tmp_path
    executor.monitor = DummyMonitor()
    executor.retriever = RepoRetriever(tmp_path)
    return executor


def test_consensus_policy_overrides(tmp_path):
    executor = build_executor(tmp_path)
    policy = executor._resolve_consensus_policy('implement')
    assert policy['vote_type'] == VoteType.QUORUM
    assert policy['quorum_size'] == 3

    default_policy = executor._resolve_consensus_policy('unknown-command')
    assert default_policy['vote_type'] == VoteType.MAJORITY
    assert default_policy['quorum_size'] == 2


def test_consensus_majority_detects_agreement():
    builder = ConsensusBuilder()
    votes = [
        ModelVote(model_name='m1', response={'decision': 'approve'}, confidence=0.8, reasoning=''),
        ModelVote(model_name='m2', response={'decision': 'approve'}, confidence=0.7, reasoning=''),
        ModelVote(model_name='m3', response={'decision': 'revise'}, confidence=0.6, reasoning=''),
    ]
    reached, decision = builder._analyze_votes(votes, VoteType.MAJORITY, quorum_size=2)
    assert reached is True
    assert isinstance(decision, dict)
    assert decision.get('decision') == 'approve'


def test_static_validation_detects_import_error(tmp_path):
    executor = build_executor(tmp_path)
    file_path = tmp_path / 'module.py'
    file_path.write_text('import nonexistent_module\n\nprint(value)', encoding='utf-8')

    issues = executor._python_semantic_issues(file_path, 'module.py')
    joined = '\n'.join(issues)
    assert "missing import 'nonexistent_module'" in joined
    assert "unresolved symbol 'value'" in joined


def test_retriever_returns_hits(tmp_path):
    sample = tmp_path / 'src'
    sample.mkdir()
    target = sample / 'example.py'
    target.write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')

    retriever = RepoRetriever(tmp_path)
    hits = retriever.retrieve('add', limit=1)
    assert hits
    hit = hits[0]
    assert 'example.py' in hit.file
    assert hit.line >= 1


def test_record_requires_evidence_event_records_payload(tmp_path):
    executor = build_executor(tmp_path)
    monitor = executor.monitor

    executor._record_requires_evidence_metrics(
        'implement',
        True,
        'plan-only',
        False,
        None,
        ['module.py: python syntax error'],
        {'consensus_reached': False},
        {'consensus_vote_type': 'majority', 'consensus_quorum_size': 2},
    )

    assert any(name.endswith('missing_evidence') for name, *_ in monitor.metrics)
    assert any(event[0] == 'hallucination.guardrail' for event in monitor.events)
