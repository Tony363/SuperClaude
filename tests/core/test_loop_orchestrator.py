"""Tests for core/loop_orchestrator.py - Main loop controller."""

import logging
import time
from unittest.mock import patch

from core.loop_orchestrator import LoopOrchestrator, create_skill_invoker_signal
from core.metrics import InMemoryMetricsCollector
from core.types import LoopConfig, QualityAssessment, TerminationReason


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

    def test_custom_logger(self):
        """Should use provided logger."""
        custom_logger = logging.getLogger("test.custom")
        orchestrator = LoopOrchestrator(logger=custom_logger)
        assert orchestrator.logger is custom_logger

    def test_custom_metrics_emitter(self):
        """Should use provided metrics emitter."""
        collector = InMemoryMetricsCollector()
        orchestrator = LoopOrchestrator(metrics_emitter=collector)
        assert orchestrator.metrics_emitter is collector

    def test_unique_loop_id(self):
        """Each orchestrator should have a unique loop_id."""
        o1 = LoopOrchestrator()
        o2 = LoopOrchestrator()
        assert o1.loop_id != o2.loop_id
        assert len(o1.loop_id) == 12

    def test_assessor_uses_config_threshold(self):
        """Assessor should use the config quality_threshold."""
        config = LoopConfig(quality_threshold=85.0)
        orchestrator = LoopOrchestrator(config)
        assert orchestrator.assessor.threshold == 85.0


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
        config = LoopConfig(max_iterations=2, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config)

        call_count = [0]
        # Scores that improve
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

                # Improving scores
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


class TestLoopOrchestratorMetrics:
    """Tests for metrics emission during loop execution."""

    def test_loop_started_metric_emitted(self):
        """loop.started.count metric should be emitted at start."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1, quality_threshold=50.0)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        orchestrator.run({"task": "t"}, invoker)

        assert collector.get("loop.started.count") == 1

    def test_loop_completed_metric_emitted(self):
        """loop.completed.count metric should be emitted with reason tag."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(
                overall_score=50.0, passed=False, improvements_needed=["more"]
            )
            orchestrator.run({"task": "t"}, invoker)

        completed = collector.filter_by_tags(
            "loop.completed.count",
            {"termination_reason": "max_iterations_reached"},
        )
        assert len(completed) == 1

    def test_loop_duration_metric_emitted(self):
        """loop.duration.seconds metric should be emitted."""
        collector = InMemoryMetricsCollector()
        orchestrator = LoopOrchestrator(LoopConfig(max_iterations=1), metrics_emitter=collector)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        orchestrator.run({"task": "t"}, invoker)

        assert collector.get("loop.duration.seconds") is not None
        assert collector.get("loop.duration.seconds") >= 0

    def test_iteration_metrics_emitted(self):
        """Per-iteration metrics should be emitted."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=2, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(
                overall_score=50.0, passed=False, improvements_needed=["more"]
            )
            orchestrator.run({"task": "t"}, invoker)

        assert collector.count("loop.iteration.duration.seconds") == 2
        assert collector.count("loop.iteration.quality_score.gauge") == 2
        assert collector.count("loop.iteration.quality_delta.gauge") == 2

    def test_final_score_metric_emitted(self):
        """loop.quality_score.final.gauge should reflect the final score."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=1, quality_threshold=50.0)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(overall_score=75.0, passed=True)

            def invoker(ctx):
                return {"changes": ["f.py"], "changed_files": ["f.py"]}

            orchestrator.run({"task": "t"}, invoker)

        assert collector.get("loop.quality_score.final.gauge") == 75.0

    def test_error_metric_emitted_on_failure(self):
        """loop.errors.count should be emitted on skill error."""
        collector = InMemoryMetricsCollector()
        orchestrator = LoopOrchestrator(metrics_emitter=collector)

        def failing(ctx):
            raise RuntimeError("boom")

        orchestrator.run({"task": "t"}, failing)

        errors = collector.filter_by_tags("loop.errors.count", {"reason": "skill_invocation"})
        assert len(errors) == 1

    def test_iterations_total_metric(self):
        """loop.iterations.total.gauge should match actual iterations."""
        collector = InMemoryMetricsCollector()
        config = LoopConfig(max_iterations=3, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(
                overall_score=50.0, passed=False, improvements_needed=["more"]
            )
            orchestrator.run({"task": "t"}, invoker)

        assert collector.get("loop.iterations.total.gauge") == 3


class TestCheckTimeout:
    """Tests for LoopOrchestrator._check_timeout()."""

    def test_no_timeout_returns_false(self):
        """Should return False when timeout is not configured."""
        orchestrator = LoopOrchestrator(LoopConfig(timeout_seconds=None))
        orchestrator._start_time = time.monotonic()
        assert orchestrator._check_timeout() is False

    def test_timeout_not_exceeded_returns_false(self):
        """Should return False when timeout is configured but not exceeded."""
        orchestrator = LoopOrchestrator(LoopConfig(timeout_seconds=100.0))
        orchestrator._start_time = time.monotonic()
        assert orchestrator._check_timeout() is False

    def test_timeout_exceeded_returns_true(self):
        """Should return True when timeout is exceeded."""
        orchestrator = LoopOrchestrator(LoopConfig(timeout_seconds=0.01))
        orchestrator._start_time = time.monotonic() - 1.0  # 1 second ago
        assert orchestrator._check_timeout() is True


class TestRecordIteration:
    """Tests for LoopOrchestrator._record_iteration()."""

    def test_first_iteration_input_quality_zero(self):
        """First iteration should have input_quality of 0.0."""
        orchestrator = LoopOrchestrator()
        orchestrator.score_history = [65.0]
        assessment = QualityAssessment(overall_score=65.0, passed=False)

        orchestrator._record_iteration(
            iteration=0,
            assessment=assessment,
            time_taken=1.0,
            success=False,
            termination="",
            changed_files=["f.py"],
        )

        assert orchestrator.iteration_history[0].input_quality == 0.0
        assert orchestrator.iteration_history[0].output_quality == 65.0

    def test_second_iteration_uses_previous_score(self):
        """Second iteration should use previous score as input_quality."""
        orchestrator = LoopOrchestrator()
        orchestrator.score_history = [50.0, 70.0]
        assessment = QualityAssessment(overall_score=70.0, passed=True)

        orchestrator._record_iteration(
            iteration=1,
            assessment=assessment,
            time_taken=2.0,
            success=True,
            termination="quality_met",
            changed_files=["f.py"],
        )

        assert orchestrator.iteration_history[0].input_quality == 50.0
        assert orchestrator.iteration_history[0].output_quality == 70.0

    def test_pal_signal_stored(self):
        """PAL signal should be stored in iteration result."""
        orchestrator = LoopOrchestrator()
        orchestrator.score_history = [60.0]
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        pal = {"tool": "mcp__pal__codereview", "action_required": True}

        orchestrator._record_iteration(
            iteration=0,
            assessment=assessment,
            time_taken=1.0,
            success=False,
            termination="",
            changed_files=[],
            pal_signal=pal,
        )

        assert orchestrator.iteration_history[0].pal_review == pal

    def test_improvements_capped_at_5(self):
        """Improvements should be capped at 5 entries."""
        orchestrator = LoopOrchestrator()
        orchestrator.score_history = [40.0]
        assessment = QualityAssessment(
            overall_score=40.0,
            passed=False,
            improvements_needed=[f"issue {i}" for i in range(10)],
        )

        orchestrator._record_iteration(
            iteration=0,
            assessment=assessment,
            time_taken=1.0,
            success=False,
            termination="",
            changed_files=[],
        )

        assert len(orchestrator.iteration_history[0].improvements_applied) == 5


class TestPrepareNextIteration:
    """Tests for LoopOrchestrator._prepare_next_iteration()."""

    def test_adds_improvements_to_context(self):
        """Should add improvements_needed from assessment."""
        orchestrator = LoopOrchestrator()
        assessment = QualityAssessment(
            overall_score=50.0,
            passed=False,
            improvements_needed=["Add tests", "Fix lint"],
        )

        result = orchestrator._prepare_next_iteration(
            {"task": "implement"},
            assessment,
            {},
        )

        assert result["improvements_needed"] == ["Add tests", "Fix lint"]

    def test_adds_iteration_and_score_info(self):
        """Should add iteration number and score info."""
        from core.types import IterationResult

        orchestrator = LoopOrchestrator()
        # Use a real IterationResult, not None
        orchestrator.iteration_history = [
            IterationResult(iteration=0, input_quality=0.0, output_quality=55.0)
        ]
        assessment = QualityAssessment(overall_score=55.0, passed=False)

        result = orchestrator._prepare_next_iteration(
            {"task": "implement"},
            assessment,
            {},
        )

        assert result["iteration"] == 1
        assert result["previous_score"] == 55.0
        assert result["target_score"] == 70.0

    def test_adds_previous_changes(self):
        """Should add previous changes from output."""
        orchestrator = LoopOrchestrator()
        assessment = QualityAssessment(overall_score=50.0, passed=False)
        output = {"changes": ["main.py", "utils.py"]}

        result = orchestrator._prepare_next_iteration(
            {"task": "implement"},
            assessment,
            output,
        )

        assert result["previous_changes"] == ["main.py", "utils.py"]

    def test_incorporates_pal_feedback(self):
        """Should incorporate PAL feedback when result key present."""
        from core.types import IterationResult

        orchestrator = LoopOrchestrator()
        pal_result = {
            "issues_found": [
                {"severity": "critical", "description": "SQL injection"},
            ]
        }
        iter_result = IterationResult(
            iteration=0,
            input_quality=0.0,
            output_quality=50.0,
            pal_review={"tool": "codereview", "result": pal_result},
        )
        orchestrator.iteration_history = [iter_result]
        assessment = QualityAssessment(
            overall_score=50.0,
            passed=False,
            improvements_needed=["Fix lint"],
        )

        result = orchestrator._prepare_next_iteration(
            {"task": "implement"},
            assessment,
            {},
        )

        assert "SQL injection" in result["improvements_needed"]

    def test_no_pal_feedback_without_result_key(self):
        """Should not fail when PAL review has no result key."""
        from core.types import IterationResult

        orchestrator = LoopOrchestrator()
        iter_result = IterationResult(
            iteration=0,
            input_quality=0.0,
            output_quality=50.0,
            pal_review={"tool": "codereview"},  # No "result" key
        )
        orchestrator.iteration_history = [iter_result]
        assessment = QualityAssessment(
            overall_score=50.0,
            passed=False,
            improvements_needed=["Fix lint"],
        )

        result = orchestrator._prepare_next_iteration(
            {"task": "implement"},
            assessment,
            {},
        )

        assert result["improvements_needed"] == ["Fix lint"]

    def test_does_not_mutate_original_context(self):
        """Should not mutate the original context dict."""
        orchestrator = LoopOrchestrator()
        assessment = QualityAssessment(overall_score=50.0, passed=False)
        original = {"task": "implement"}

        orchestrator._prepare_next_iteration(original, assessment, {})

        assert "improvements_needed" not in original


class TestPALReviewSignalInLoop:
    """Tests for PAL review signal generation within the loop."""

    def test_pal_signal_not_generated_on_last_iteration(self):
        """PAL signal should NOT be generated on the last iteration."""
        config = LoopConfig(max_iterations=2, quality_threshold=95.0, pal_review_enabled=True)
        orchestrator = LoopOrchestrator(config)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(
                overall_score=50.0, passed=False, improvements_needed=["more"]
            )
            result = orchestrator.run({"task": "t"}, invoker)

        # First iteration should have PAL signal
        assert result.iteration_history[0].pal_review is not None
        # Last iteration should NOT have PAL signal
        assert result.iteration_history[1].pal_review is None

    def test_pal_signal_not_generated_when_disabled(self):
        """PAL signal should not be generated when PAL is disabled."""
        config = LoopConfig(max_iterations=2, quality_threshold=95.0, pal_review_enabled=False)
        orchestrator = LoopOrchestrator(config)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(
                overall_score=50.0, passed=False, improvements_needed=["more"]
            )
            result = orchestrator.run({"task": "t"}, invoker)

        for ir in result.iteration_history:
            assert ir.pal_review is None

    def test_final_validation_attached_on_quality_met(self):
        """Final validation signal should be attached when quality is met."""
        config = LoopConfig(quality_threshold=50.0)
        orchestrator = LoopOrchestrator(config)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(overall_score=75.0, passed=True)
            result = orchestrator.run({"task": "t"}, invoker)

        assert result.termination_reason == TerminationReason.QUALITY_MET
        last_iter = result.iteration_history[-1]
        assert last_iter.pal_review is not None
        assert last_iter.pal_review["is_final"] is True

    def test_no_final_validation_on_max_iterations(self):
        """No final validation signal when terminated by max iterations."""
        config = LoopConfig(max_iterations=1, quality_threshold=95.0)
        orchestrator = LoopOrchestrator(config)

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        with patch.object(orchestrator, "assessor") as mock:
            mock.assess = lambda ctx: QualityAssessment(
                overall_score=50.0, passed=False, improvements_needed=["more"]
            )
            result = orchestrator.run({"task": "t"}, invoker)

        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        # With max_iterations=1, the single iteration is also the last,
        # so PAL review not generated (not on last iteration)
        last_iter = result.iteration_history[-1]
        assert last_iter.pal_review is None

    def test_initial_context_not_mutated(self):
        """run() should not mutate the initial context dict."""
        config = LoopConfig(max_iterations=1, quality_threshold=50.0)
        orchestrator = LoopOrchestrator(config)
        initial = {"task": "implement"}

        def invoker(ctx):
            return {"changes": ["f.py"], "changed_files": ["f.py"]}

        orchestrator.run(initial, invoker)

        assert initial == {"task": "implement"}


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
