"""Tests for loop invariants - deterministic validation of loop mechanics.

Tests the core loop behavior without requiring actual Claude execution:
- Termination conditions (quality_met, oscillation, stagnation, max_iterations)
- Safety caps (hard max 5 iterations)
- Score history tracking
- Changed files accumulation
"""

import time
from unittest.mock import patch

from core.loop_orchestrator import LoopOrchestrator
from core.types import LoopConfig, TerminationReason
from tests.loop.conftest import FixtureAssessor


class TestLoopTerminationQualityMet:
    """Tests for termination when quality threshold is met."""

    def test_terminates_on_first_iteration_quality_met(
        self, fixture_assessor_quality_met, fixture_skill_invoker
    ):
        """Loop should terminate when quality is met on first iteration."""
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", fixture_assessor_quality_met):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.QUALITY_MET
        assert result.total_iterations == 1
        assert result.final_assessment.passed is True

    def test_terminates_on_later_iteration_quality_met(self, fixture_skill_invoker):
        """Loop should terminate when quality is met after several iterations."""
        assessor = FixtureAssessor(scores=[50.0, 60.0, 75.0])  # Pass on 3rd
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.QUALITY_MET
        assert result.total_iterations == 3
        assert result.final_assessment.overall_score == 75.0


class TestLoopTerminationMaxIterations:
    """Tests for termination when max iterations reached."""

    def test_terminates_at_max_iterations(self, fixture_skill_invoker):
        """Loop should terminate at max iterations if quality never met."""
        # Scores that improve but never reach threshold
        assessor = FixtureAssessor(scores=[50.0, 60.0, 65.0, 68.0, 69.0])
        config = LoopConfig(max_iterations=3, quality_threshold=95.0, min_improvement=1.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        assert result.total_iterations == 3

    def test_hard_max_5_cannot_be_exceeded(self, fixture_skill_invoker):
        """Even if config specifies more, hard max of 5 is enforced."""
        assessor = FixtureAssessor(scores=[50.0, 55.0, 60.0, 65.0, 68.0, 70.0, 72.0])
        config = LoopConfig(max_iterations=10, quality_threshold=95.0, min_improvement=1.0)
        orchestrator = LoopOrchestrator(config)

        # Verify config was capped
        assert orchestrator.config.max_iterations == 5

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.total_iterations <= 5


class TestLoopTerminationOscillation:
    """Tests for termination when oscillation is detected."""

    def test_terminates_on_oscillation(self, fixture_assessor_oscillating, fixture_skill_invoker):
        """Loop should terminate when scores oscillate."""
        config = LoopConfig(max_iterations=5, quality_threshold=90.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", fixture_assessor_oscillating):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.OSCILLATION

    def test_oscillation_pattern_detected(self, fixture_skill_invoker):
        """Alternating up/down pattern should trigger oscillation."""
        # Clear oscillation: up, down, up, down
        assessor = FixtureAssessor(scores=[50.0, 60.0, 52.0, 63.0])
        config = LoopConfig(max_iterations=5, quality_threshold=90.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.OSCILLATION


class TestLoopTerminationStagnation:
    """Tests for termination when stagnation is detected."""

    def test_terminates_on_stagnation(self, fixture_assessor_stagnating, fixture_skill_invoker):
        """Loop should terminate when scores stagnate."""
        config = LoopConfig(
            max_iterations=5,
            quality_threshold=90.0,
            min_improvement=0.1,  # Low to let stagnation detection trigger
        )
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", fixture_assessor_stagnating):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.STAGNATION

    def test_stagnation_pattern_detected(self, fixture_skill_invoker):
        """Flat scores with low variance should trigger stagnation."""
        # Plateau with variance < 2.0
        assessor = FixtureAssessor(scores=[65.0, 65.5, 65.2, 65.3])
        config = LoopConfig(max_iterations=5, quality_threshold=90.0, min_improvement=0.1)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.STAGNATION


class TestLoopTerminationInsufficientImprovement:
    """Tests for termination when improvement is insufficient."""

    def test_terminates_on_insufficient_improvement(
        self, fixture_assessor_insufficient_improvement, fixture_skill_invoker
    ):
        """Loop should terminate when improvement is below threshold."""
        config = LoopConfig(
            max_iterations=5,
            quality_threshold=90.0,
            min_improvement=10.0,  # Require 10+ points per iteration
        )
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", fixture_assessor_insufficient_improvement):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.INSUFFICIENT_IMPROVEMENT

    def test_small_improvement_triggers_termination(self, fixture_skill_invoker):
        """Improvement of only +2 should trigger termination with min_improvement=10."""
        assessor = FixtureAssessor(scores=[50.0, 52.0])  # Only +2
        config = LoopConfig(max_iterations=5, quality_threshold=90.0, min_improvement=10.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason == TerminationReason.INSUFFICIENT_IMPROVEMENT
        assert result.total_iterations == 2


class TestLoopTerminationError:
    """Tests for termination when errors occur."""

    def test_terminates_on_skill_invoker_error(self, fixture_skill_invoker_with_errors):
        """Loop should terminate gracefully on skill invoker error."""
        config = LoopConfig(max_iterations=3)
        orchestrator = LoopOrchestrator(config)

        result = orchestrator.run({"task": "implement"}, fixture_skill_invoker_with_errors)

        assert result.termination_reason == TerminationReason.ERROR
        assert result.total_iterations == 1


class TestLoopTerminationTimeout:
    """Tests for termination on timeout."""

    def test_terminates_on_timeout(self, loop_config_with_timeout):
        """Loop should terminate when timeout is reached."""
        orchestrator = LoopOrchestrator(loop_config_with_timeout)

        call_count = [0]

        def slow_invoker(ctx):
            call_count[0] += 1
            time.sleep(0.05)  # Slow enough to trigger timeout
            return {"changes": ["main.py"], "changed_files": ["main.py"]}

        assessor = FixtureAssessor(scores=[50.0, 55.0, 60.0, 65.0, 70.0])

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, slow_invoker)

        assert result.termination_reason == TerminationReason.TIMEOUT


class TestLoopScoreHistoryTracking:
    """Tests for score history tracking across iterations."""

    def test_score_history_recorded(self, fixture_skill_invoker):
        """Score history should be recorded for each iteration."""
        assessor = FixtureAssessor(scores=[50.0, 60.0, 70.0])
        config = LoopConfig(quality_threshold=65.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        # Should have scores for all iterations until quality met
        assert len(orchestrator.score_history) >= 2
        assert orchestrator.score_history[0] == 50.0
        assert orchestrator.score_history[1] == 60.0

    def test_iteration_history_recorded(self, fixture_skill_invoker):
        """Iteration history should be recorded."""
        assessor = FixtureAssessor(scores=[50.0, 60.0])
        config = LoopConfig(max_iterations=2, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert len(result.iteration_history) == 2
        assert result.iteration_history[0].iteration == 0
        assert result.iteration_history[1].iteration == 1


class TestLoopChangedFilesTracking:
    """Tests for tracking changed files across iterations."""

    def test_changed_files_accumulated(self):
        """Changed files should accumulate across iterations."""
        iteration = [0]
        files_per_iteration = [["file1.py"], ["file2.py"], ["file3.py"]]

        def changing_invoker(ctx):
            files = files_per_iteration[min(iteration[0], 2)]
            iteration[0] += 1
            return {"changes": files, "changed_files": files}

        assessor = FixtureAssessor(scores=[50.0, 60.0, 70.0])
        config = LoopConfig(quality_threshold=65.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "implement"}, changing_invoker)

        # Should have files from all iterations
        assert "file1.py" in orchestrator.all_changed_files
        assert "file2.py" in orchestrator.all_changed_files

    def test_duplicate_files_not_duplicated(self):
        """Same file changed multiple times should appear once."""

        def same_file_invoker(ctx):
            return {"changes": ["main.py"], "changed_files": ["main.py"]}

        assessor = FixtureAssessor(scores=[50.0, 60.0, 70.0])
        config = LoopConfig(quality_threshold=65.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "implement"}, same_file_invoker)

        # main.py should appear only once
        assert orchestrator.all_changed_files.count("main.py") == 1


class TestLoopResultSerialization:
    """Tests for loop result serialization."""

    def test_to_dict_includes_all_fields(self, fixture_skill_invoker):
        """to_dict should include all important fields."""
        assessor = FixtureAssessor(scores=[75.0])
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        d = result.to_dict()

        assert "loop_completed" in d
        assert "iterations" in d
        assert "termination_reason" in d
        assert "final_score" in d
        assert "passed" in d
        assert "history" in d

    def test_termination_reason_serialized(self, fixture_skill_invoker):
        """Termination reason should be serialized as string."""
        assessor = FixtureAssessor(scores=[75.0])
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        d = result.to_dict()
        assert d["termination_reason"] == "quality_threshold_met"


class TestLoopSafetyInvariants:
    """Tests for safety invariants that must always hold."""

    def test_max_iterations_never_exceeds_5(self):
        """Hard max of 5 iterations should never be exceeded."""
        config = LoopConfig(max_iterations=100)  # Try to set high
        assert config.max_iterations == 5  # Should be capped

    def test_loop_always_terminates(self, fixture_skill_invoker):
        """Loop should always terminate (no infinite loops)."""
        # Even with improving scores, should hit max iterations
        assessor = FixtureAssessor(
            scores=[50.0, 55.0, 60.0, 65.0, 68.0, 70.0, 72.0, 74.0, 76.0, 78.0]
        )
        config = LoopConfig(max_iterations=5, quality_threshold=95.0, min_improvement=1.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        # Must terminate
        assert result.termination_reason is not None
        assert result.total_iterations <= 5

    def test_termination_reason_always_set(self, fixture_skill_invoker):
        """Termination reason should always be set on completion."""
        assessor = FixtureAssessor(scores=[75.0])
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LoopOrchestrator(config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "implement"}, fixture_skill_invoker)

        assert result.termination_reason in [
            TerminationReason.QUALITY_MET,
            TerminationReason.MAX_ITERATIONS,
            TerminationReason.OSCILLATION,
            TerminationReason.STAGNATION,
            TerminationReason.INSUFFICIENT_IMPROVEMENT,
            TerminationReason.ERROR,
            TerminationReason.TIMEOUT,
            TerminationReason.HUMAN_ESCALATION,
        ]
