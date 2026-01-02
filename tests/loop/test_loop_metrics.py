"""Tests for metrics emission from LoopOrchestrator.

These tests verify that operational metrics are emitted at key lifecycle events.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from core.loop_orchestrator import LoopOrchestrator
from core.metrics import InMemoryMetricsCollector
from core.types import LoopConfig, QualityAssessment, TerminationReason


class FixtureAssessor:
    """Quality assessor that returns predetermined scores."""

    def __init__(self, scores: list[float], threshold: float = 70.0):
        self.scores = scores
        self.threshold = threshold
        self.call_count = 0

    def assess(self, output: Dict[str, Any]) -> QualityAssessment:
        """Return predetermined quality assessment."""
        if self.call_count < len(self.scores):
            score = self.scores[self.call_count]
        else:
            score = self.scores[-1] if self.scores else 50.0

        self.call_count += 1
        return QualityAssessment(
            overall_score=score,
            passed=score >= self.threshold,
            improvements_needed=[] if score >= self.threshold else ["improve"],
        )


class TestLoopMetricsEmission:
    """Tests for metrics emitted during loop execution."""

    def test_loop_started_metric(self):
        """Should emit loop.started.count when loop begins."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([85.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        assert collector.get("loop.started.count") == 1

    def test_loop_completed_metric(self):
        """Should emit loop.completed.count when loop ends."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([85.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        assert collector.get("loop.completed.count") == 1

    def test_loop_completed_has_termination_reason_tag(self):
        """Completed metric should include termination_reason tag."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([85.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        # TerminationReason.QUALITY_MET.value is "quality_threshold_met"
        metrics = collector.filter_by_tags(
            "loop.completed.count", {"termination_reason": "quality_threshold_met"}
        )
        assert len(metrics) == 1

    def test_loop_duration_metric(self):
        """Should emit loop.duration.seconds with positive value."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([85.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        duration = collector.get("loop.duration.seconds")
        assert duration is not None
        assert duration >= 0

    def test_loop_iterations_total_metric(self):
        """Should emit loop.iterations.total.gauge with correct count."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=3)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        # Scores below threshold, then above
        orchestrator.assessor = FixtureAssessor([50.0, 60.0, 85.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        assert collector.get("loop.iterations.total.gauge") == 3

    def test_loop_quality_score_final_metric(self):
        """Should emit loop.quality_score.final.gauge."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([75.5])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        assert collector.get("loop.quality_score.final.gauge") == 75.5

    def test_error_metric_on_skill_invocation_failure(self):
        """Should emit loop.errors.count when skill invoker raises."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)

        def failing_invoker(ctx):
            raise RuntimeError("Intentional failure")

        orchestrator.run({}, failing_invoker)

        error_metrics = collector.filter_by_tags(
            "loop.errors.count", {"reason": "skill_invocation"}
        )
        assert len(error_metrics) == 1


class TestIterationMetrics:
    """Tests for per-iteration metrics."""

    def test_iteration_duration_metric(self):
        """Should emit loop.iteration.duration.seconds per iteration."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=3)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([50.0, 60.0, 85.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        durations = collector.get_all("loop.iteration.duration.seconds")
        assert len(durations) == 3
        assert all(d >= 0 for d in durations)

    def test_iteration_quality_score_metric(self):
        """Should emit loop.iteration.quality_score.gauge per iteration."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=3)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([50.0, 65.0, 80.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        scores = collector.get_all("loop.iteration.quality_score.gauge")
        assert scores == [50.0, 65.0, 80.0]

    def test_iteration_quality_delta_metric(self):
        """Should emit loop.iteration.quality_delta.gauge per iteration."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=3)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([50.0, 65.0, 80.0])

        orchestrator.run({}, lambda ctx: {"changed_files": []})

        deltas = collector.get_all("loop.iteration.quality_delta.gauge")
        # First iteration: 50 - 0 = 50
        # Second iteration: 65 - 50 = 15
        # Third iteration: 80 - 65 = 15
        assert len(deltas) == 3
        assert deltas[0] == 50.0  # From initial 0 to 50
        assert deltas[1] == 15.0  # From 50 to 65
        assert deltas[2] == 15.0  # From 65 to 80


class TestTerminationReasonTags:
    """Tests for termination reason tags in metrics."""

    def test_quality_met_tag(self):
        """Quality met termination should have correct tag."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([85.0])

        result = orchestrator.run({}, lambda ctx: {"changed_files": []})

        assert result.termination_reason == TerminationReason.QUALITY_MET
        # TerminationReason.QUALITY_MET.value is "quality_threshold_met"
        metrics = collector.filter_by_tags(
            "loop.completed.count", {"termination_reason": "quality_threshold_met"}
        )
        assert len(metrics) == 1

    def test_max_iterations_tag(self):
        """Max iterations termination should have correct tag."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=2)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        orchestrator.assessor = FixtureAssessor([50.0, 55.0])

        result = orchestrator.run({}, lambda ctx: {"changed_files": []})

        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        # TerminationReason.MAX_ITERATIONS.value is "max_iterations_reached"
        metrics = collector.filter_by_tags(
            "loop.completed.count", {"termination_reason": "max_iterations_reached"}
        )
        assert len(metrics) == 1


class TestNoopEmitterDoesNotBreak:
    """Tests that orchestrator works without a metrics emitter."""

    def test_runs_without_emitter(self):
        """Orchestrator should run fine without explicit emitter."""
        config = LoopConfig(max_iterations=1)
        orchestrator = LoopOrchestrator(config)  # No metrics_emitter
        orchestrator.assessor = FixtureAssessor([85.0])

        result = orchestrator.run({}, lambda ctx: {"changed_files": []})

        assert result.termination_reason == TerminationReason.QUALITY_MET
