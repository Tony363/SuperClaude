"""Tests for core/loop_orchestrator.py - Main loop controller."""

import time
from unittest.mock import patch

from core.loop_orchestrator import LoopOrchestrator, create_skill_invoker_signal
from core.types import LoopConfig, TerminationReason


class TestLoopOrchestratorInit:
    """Tests for LoopOrchestrator initialization."""

    def test_default_config(self):
        """Should use default config when none provided."""
        orchestrator = LoopOrchestrator()
        assert orchestrator.config.max_iterations == 3
        assert orchestrator.config.quality_threshold == 70.0

    def test_custom_config(self):
        """Should use provided config."""
        config = LoopConfig(max_iterations=2, quality_threshold=80.0)
        orchestrator = LoopOrchestrator(config)
        assert orchestrator.config.max_iterations == 2
        assert orchestrator.config.quality_threshold == 80.0

    def test_initial_state(self):
        """Should initialize with empty state."""
        orchestrator = LoopOrchestrator()
        assert orchestrator.iteration_history == []
        assert orchestrator.score_history == []
        assert orchestrator.all_changed_files == []


class TestLoopOrchestratorRun:
    """Tests for LoopOrchestrator.run() method."""

    def test_quality_met_first_iteration(self):
        """Should terminate when quality is met on first iteration."""
        config = LoopConfig(quality_threshold=50.0)
        orchestrator = LoopOrchestrator(config)

        def skill_invoker(ctx):
            return {
                "changes": ["main.py"],
                "tests": {"ran": True, "passed": 10, "failed": 0},
                "lint": {"ran": True, "errors": 0},
                "changed_files": ["main.py"],
            }

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                return QualityAssessment(
                    overall_score=75.0,
                    passed=True,
                    threshold=50.0,
                    improvements_needed=[],
                )

            mock_assessor.assess = mock_assess

            result = orchestrator.run({"task": "implement feature"}, skill_invoker)

        assert result.termination_reason == TerminationReason.QUALITY_MET
        assert result.total_iterations == 1
        assert result.final_assessment.passed is True

    def test_max_iterations_reached(self):
        """Should terminate when max iterations reached."""
        config = LoopConfig(max_iterations=2, quality_threshold=95.0, min_improvement=1.0)
        orchestrator = LoopOrchestrator(config)

        call_count = [0]
        # Scores that improve enough to avoid INSUFFICIENT_IMPROVEMENT
        scores = [50.0, 60.0, 70.0]

        def skill_invoker(ctx):
            call_count[0] += 1
            return {
                "changes": ["main.py"],
                "tests": {"ran": True, "passed": 5, "failed": 2},
                "lint": {"ran": True, "errors": 1},
                "changed_files": ["main.py"],
            }

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                score = scores[min(call_count[0], len(scores) - 1)]
                return QualityAssessment(
                    overall_score=score,
                    passed=False,
                    threshold=95.0,
                    improvements_needed=["More work needed"],
                )

            mock_assessor.assess = mock_assess

            result = orchestrator.run({"task": "implement feature"}, skill_invoker)

        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        assert result.total_iterations == 2
        assert call_count[0] == 2

    def test_oscillation_detection(self):
        """Should terminate on oscillation detection."""
        config = LoopConfig(max_iterations=5, quality_threshold=90.0)
        orchestrator = LoopOrchestrator(config)

        # Create a mock assessor that returns oscillating scores
        scores = [50.0, 60.0, 52.0, 63.0]
        score_index = [0]

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                score = scores[min(score_index[0], len(scores) - 1)]
                score_index[0] += 1
                return QualityAssessment(
                    overall_score=score,
                    passed=False,
                    improvements_needed=["Fix issues"],
                )

            mock_assessor.assess = mock_assess

            def skill_invoker(ctx):
                return {
                    "changes": ["main.py"],
                    "changed_files": ["main.py"],
                }

            result = orchestrator.run({"task": "implement"}, skill_invoker)

        assert result.termination_reason == TerminationReason.OSCILLATION

    def test_stagnation_detection(self):
        """Should terminate on stagnation detection."""
        # Set min_improvement very low so stagnation detection triggers first
        config = LoopConfig(max_iterations=5, quality_threshold=90.0, min_improvement=0.1)
        orchestrator = LoopOrchestrator(config)

        # Create stagnating scores
        scores = [65.0, 65.5, 65.2, 65.3]
        score_index = [0]

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                score = scores[min(score_index[0], len(scores) - 1)]
                score_index[0] += 1
                return QualityAssessment(
                    overall_score=score,
                    passed=False,
                    improvements_needed=["Fix issues"],
                )

            mock_assessor.assess = mock_assess

            def skill_invoker(ctx):
                return {
                    "changes": ["main.py"],
                    "changed_files": ["main.py"],
                }

            result = orchestrator.run({"task": "implement"}, skill_invoker)

        assert result.termination_reason == TerminationReason.STAGNATION

    def test_insufficient_improvement_detection(self):
        """Should terminate on insufficient improvement."""
        config = LoopConfig(
            max_iterations=5,
            quality_threshold=90.0,
            min_improvement=10.0,
        )
        orchestrator = LoopOrchestrator(config)

        # Create scores with small improvement
        scores = [50.0, 52.0]  # Only +2 improvement
        score_index = [0]

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                score = scores[min(score_index[0], len(scores) - 1)]
                score_index[0] += 1
                return QualityAssessment(
                    overall_score=score,
                    passed=False,
                    improvements_needed=["Fix issues"],
                )

            mock_assessor.assess = mock_assess

            def skill_invoker(ctx):
                return {
                    "changes": ["main.py"],
                    "changed_files": ["main.py"],
                }

            result = orchestrator.run({"task": "implement"}, skill_invoker)

        assert result.termination_reason == TerminationReason.INSUFFICIENT_IMPROVEMENT

    def test_error_handling(self):
        """Should handle skill invoker errors gracefully."""
        config = LoopConfig(max_iterations=3)
        orchestrator = LoopOrchestrator(config)

        def failing_invoker(ctx):
            raise ValueError("Skill execution failed")

        result = orchestrator.run({"task": "implement"}, failing_invoker)

        assert result.termination_reason == TerminationReason.ERROR
        assert result.total_iterations == 1

    def test_timeout_detection(self):
        """Should terminate on timeout."""
        config = LoopConfig(
            max_iterations=10,
            quality_threshold=95.0,
            timeout_seconds=0.1,  # Very short timeout
            min_improvement=1.0,  # Low min improvement to avoid early termination
        )
        orchestrator = LoopOrchestrator(config)

        call_count = [0]

        def slow_invoker(ctx):
            call_count[0] += 1
            time.sleep(0.05)  # Sleep to trigger timeout
            return {
                "changes": ["main.py"],
                "changed_files": ["main.py"],
            }

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                # Improving scores to avoid INSUFFICIENT_IMPROVEMENT
                score = 50.0 + (call_count[0] * 5.0)
                return QualityAssessment(
                    overall_score=score,
                    passed=False,
                    improvements_needed=["More work"],
                )

            mock_assessor.assess = mock_assess

            result = orchestrator.run({"task": "implement"}, slow_invoker)

        assert result.termination_reason == TerminationReason.TIMEOUT

    def test_changed_files_tracked(self):
        """Should track all changed files across iterations."""
        config = LoopConfig(max_iterations=2, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config)

        iteration = [0]

        def skill_invoker(ctx):
            iteration[0] += 1
            files = [f"file{iteration[0]}.py"]
            return {
                "changes": files,
                "changed_files": files,
            }

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                return QualityAssessment(
                    overall_score=50.0,
                    passed=False,
                    improvements_needed=["More work"],
                )

            mock_assessor.assess = mock_assess

            orchestrator.run({"task": "implement"}, skill_invoker)

        assert "file1.py" in orchestrator.all_changed_files
        assert "file2.py" in orchestrator.all_changed_files

    def test_iteration_history_recorded(self):
        """Should record iteration history."""
        config = LoopConfig(max_iterations=2, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config)

        def skill_invoker(ctx):
            return {
                "changes": ["main.py"],
                "changed_files": ["main.py"],
            }

        with patch.object(orchestrator, "assessor") as mock_assessor:

            def mock_assess(ctx):
                from core.types import QualityAssessment

                return QualityAssessment(
                    overall_score=50.0,
                    passed=False,
                    improvements_needed=["More work"],
                )

            mock_assessor.assess = mock_assess

            result = orchestrator.run({"task": "implement"}, skill_invoker)

        assert len(result.iteration_history) == 2
        assert result.iteration_history[0].iteration == 0
        assert result.iteration_history[1].iteration == 1


class TestLoopResultSerialization:
    """Tests for LoopResult.to_dict() method."""

    def test_to_dict_includes_all_fields(self):
        """to_dict should include all important fields."""
        config = LoopConfig(quality_threshold=50.0)
        orchestrator = LoopOrchestrator(config)

        def skill_invoker(ctx):
            return {
                "changes": ["main.py"],
                "tests": {"ran": True, "passed": 10, "failed": 0},
                "lint": {"ran": True, "errors": 0},
                "changed_files": ["main.py"],
            }

        result = orchestrator.run({"task": "implement"}, skill_invoker)
        d = result.to_dict()

        assert "loop_completed" in d
        assert "iterations" in d
        assert "termination_reason" in d
        assert "final_score" in d
        assert "passed" in d
        assert "history" in d


class TestCreateSkillInvokerSignal:
    """Tests for create_skill_invoker_signal helper function."""

    def test_basic_signal_structure(self):
        """Signal should have required structure."""
        signal = create_skill_invoker_signal({"task": "implement feature"})
        assert signal["action"] == "execute_skill"
        assert signal["skill"] == "sc-implement"
        assert "parameters" in signal
        assert "collect" in signal

    def test_task_included(self):
        """Task should be included in parameters."""
        signal = create_skill_invoker_signal({"task": "add authentication"})
        assert signal["parameters"]["task"] == "add authentication"

    def test_improvements_included(self):
        """Improvements should be included in parameters."""
        context = {
            "task": "fix bug",
            "improvements_needed": ["Add tests", "Fix lint"],
        }
        signal = create_skill_invoker_signal(context)
        assert signal["parameters"]["improvements_needed"] == ["Add tests", "Fix lint"]

    def test_iteration_included(self):
        """Iteration should be included in parameters."""
        context = {"task": "implement", "iteration": 2}
        signal = create_skill_invoker_signal(context)
        assert signal["parameters"]["iteration"] == 2

    def test_focus_initial(self):
        """Focus should be 'implementation' for iteration 0."""
        context = {"task": "implement", "iteration": 0}
        signal = create_skill_invoker_signal(context)
        assert signal["parameters"]["focus"] == "implementation"

    def test_focus_remediation(self):
        """Focus should be 'remediation' for later iterations."""
        context = {"task": "implement", "iteration": 2}
        signal = create_skill_invoker_signal(context)
        assert signal["parameters"]["focus"] == "remediation"

    def test_collect_fields(self):
        """Collect should specify required evidence fields."""
        signal = create_skill_invoker_signal({"task": "implement"})
        assert "changes" in signal["collect"]
        assert "tests" in signal["collect"]
        assert "lint" in signal["collect"]
        assert "changed_files" in signal["collect"]

    def test_context_preserved(self):
        """Full context should be preserved in signal."""
        context = {"task": "implement", "custom_field": "value"}
        signal = create_skill_invoker_signal(context)
        assert signal["context"] == context
