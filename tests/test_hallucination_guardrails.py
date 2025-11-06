import os
from pathlib import Path

import pytest

os.environ.setdefault("SUPERCLAUDE_OFFLINE_MODE", "1")

from SuperClaude.Commands.executor import CommandExecutor
from SuperClaude.Commands.parser import CommandParser
from SuperClaude.Commands.registry import CommandRegistry
from SuperClaude.ModelRouter.consensus import ConsensusBuilder, ModelVote, VoteType
from SuperClaude.Monitoring.performance_monitor import PerformanceMonitor
from SuperClaude.Monitoring.sink import MetricsSink
from SuperClaude.Retrieval import RepoRetriever


class MemorySink(MetricsSink):
    def __init__(self) -> None:
        self.events = []

    def write_event(self, event):  # noqa: D401
        self.events.append(event)


def build_executor(tmp_path: Path) -> tuple[CommandExecutor, MemorySink]:
    registry = CommandRegistry()
    parser = CommandParser(registry)
    executor = CommandExecutor(registry, parser)
    executor.repo_root = tmp_path
    sink = MemorySink()
    executor.monitor = PerformanceMonitor(config={"persist_metrics": False}, sinks=[sink])
    executor.retriever = RepoRetriever(tmp_path)
    return executor, sink


def test_consensus_policy_overrides(tmp_path):
    executor, _ = build_executor(tmp_path)
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
    executor, _ = build_executor(tmp_path)
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
    executor, sink = build_executor(tmp_path)
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

    metric_names = [metric.name for metrics in monitor.metrics.values() for metric in metrics]
    assert any(name.endswith('missing_evidence') for name in metric_names)
    assert any(event.get('event_type') == 'hallucination.guardrail' for event in sink.events)
