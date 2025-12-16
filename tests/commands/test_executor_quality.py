"""Tests for CommandExecutor quality loop methods."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.Commands import CommandContext
from SuperClaude.Modes.behavioral_manager import BehavioralMode
from SuperClaude.Quality.quality_scorer import QualityAssessment, IterationResult


def make_assessment(
    overall_score: float = 85.0,
    passed: bool = True,
    improvements_needed: list = None,
) -> QualityAssessment:
    """Helper to create QualityAssessment with default values."""
    return QualityAssessment(
        overall_score=overall_score,
        metrics=[],
        timestamp=datetime.now(),
        iteration=0,
        passed=passed,
        threshold=75.0,
        context={},
        improvements_needed=improvements_needed or [],
    )


class TestMaybeRunQualityLoop:
    """Tests for _maybe_run_quality_loop method."""

    def test_maybe_run_quality_loop_returns_none_if_already_assessed(
        self, executor, sample_context
    ):
        """_maybe_run_quality_loop skips if loop_assessment already set."""
        sample_context.results["loop_assessment"] = {"score": 0.9}
        sample_context.loop_enabled = True

        result = executor._maybe_run_quality_loop(sample_context, {"output": "test"})

        assert result is None

    def test_maybe_run_quality_loop_uses_context_iterations(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_maybe_run_quality_loop uses context.loop_iterations when set."""
        sample_context.loop_enabled = True
        sample_context.loop_iterations = 5
        sample_context.loop_min_improvement = None
        executor.quality_scorer = mock_quality_scorer

        mock_quality_scorer.agentic_loop.return_value = (
            {"improved": True},
            make_assessment(overall_score=90.0, passed=True),
            [],
        )

        executor._maybe_run_quality_loop(sample_context, {"output": "test"})

        # Check that max_iterations was passed as 5
        call_kwargs = mock_quality_scorer.agentic_loop.call_args
        assert call_kwargs.kwargs.get("max_iterations") == 5

    def test_maybe_run_quality_loop_uses_default_max_iterations(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_maybe_run_quality_loop uses scorer MAX_ITERATIONS as default."""
        sample_context.loop_enabled = True
        sample_context.loop_iterations = None
        sample_context.loop_min_improvement = None
        executor.quality_scorer = mock_quality_scorer
        mock_quality_scorer.MAX_ITERATIONS = 7

        mock_quality_scorer.agentic_loop.return_value = (
            {"improved": True},
            make_assessment(overall_score=90.0, passed=True),
            [],
        )

        executor._maybe_run_quality_loop(sample_context, {"output": "test"})

        call_kwargs = mock_quality_scorer.agentic_loop.call_args
        assert call_kwargs.kwargs.get("max_iterations") == 7

    def test_maybe_run_quality_loop_passes_min_improvement(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_maybe_run_quality_loop passes min_improvement to scorer."""
        sample_context.loop_enabled = True
        sample_context.loop_iterations = None
        sample_context.loop_min_improvement = 0.15
        executor.quality_scorer = mock_quality_scorer

        mock_quality_scorer.agentic_loop.return_value = (
            {"improved": True},
            make_assessment(overall_score=90.0, passed=True),
            [],
        )

        executor._maybe_run_quality_loop(sample_context, {"output": "test"})

        call_kwargs = mock_quality_scorer.agentic_loop.call_args
        assert call_kwargs.kwargs.get("min_improvement") == 0.15

    def test_maybe_run_quality_loop_handles_exception(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_maybe_run_quality_loop handles exception gracefully."""
        sample_context.loop_enabled = True
        sample_context.loop_iterations = None
        sample_context.loop_min_improvement = None
        executor.quality_scorer = mock_quality_scorer

        mock_quality_scorer.agentic_loop.side_effect = Exception("loop crashed")

        result = executor._maybe_run_quality_loop(sample_context, {"output": "test"})

        assert result is None
        assert "loop_error" in sample_context.results
        assert "loop crashed" in sample_context.results["loop_error"]

    def test_maybe_run_quality_loop_records_iterations(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_maybe_run_quality_loop records iteration count in results."""
        sample_context.loop_enabled = True
        sample_context.loop_iterations = None
        sample_context.loop_min_improvement = None
        executor.quality_scorer = mock_quality_scorer

        # Create mock iteration history using IterationResult
        iteration_history = [
            IterationResult(
                iteration=0,
                input_quality=70.0,
                output_quality=80.0,
                improvements_applied=["fix-1"],
                time_taken=1.0,
                success=True,
            ),
            IterationResult(
                iteration=1,
                input_quality=80.0,
                output_quality=90.0,
                improvements_applied=["fix-2"],
                time_taken=0.5,
                success=True,
            ),
        ]
        mock_quality_scorer.agentic_loop.return_value = (
            {"improved": True},
            make_assessment(overall_score=90.0, passed=True),
            iteration_history,
        )

        result = executor._maybe_run_quality_loop(sample_context, {"output": "test"})

        assert result is not None
        assert sample_context.results["loop_iterations_executed"] == 2

    def test_maybe_run_quality_loop_returns_improved_output(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_maybe_run_quality_loop returns improved output and assessment."""
        sample_context.loop_enabled = True
        sample_context.loop_iterations = None
        sample_context.loop_min_improvement = None
        executor.quality_scorer = mock_quality_scorer

        improved = {"status": "improved", "quality": "high"}
        assessment = make_assessment(overall_score=95.0, passed=True)
        mock_quality_scorer.agentic_loop.return_value = (improved, assessment, [])

        result = executor._maybe_run_quality_loop(sample_context, {"output": "test"})

        assert result is not None
        assert result["output"] == improved
        assert result["assessment"] == assessment


class TestEvaluateQualityGate:
    """Tests for _evaluate_quality_gate method."""

    def test_evaluate_quality_gate_uses_precomputed(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_evaluate_quality_gate uses precomputed assessment if passed."""
        executor.quality_scorer = mock_quality_scorer
        precomputed = make_assessment(overall_score=90.0, passed=True)

        result = executor._evaluate_quality_gate(
            sample_context,
            {"output": "test"},
            changed_paths=[],
            status="success",
            precomputed=precomputed,
        )

        assert result == precomputed
        mock_quality_scorer.evaluate.assert_not_called()

    def test_evaluate_quality_gate_calls_scorer(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_evaluate_quality_gate calls quality_scorer.evaluate."""
        executor.quality_scorer = mock_quality_scorer
        mock_quality_scorer.evaluate.return_value = make_assessment(
            overall_score=85.0, passed=True
        )

        result = executor._evaluate_quality_gate(
            sample_context,
            {"output": "test"},
            changed_paths=[Path("/fake/file.py")],
            status="success",
        )

        assert result is not None
        assert result.overall_score == 85.0
        mock_quality_scorer.evaluate.assert_called_once()

    def test_evaluate_quality_gate_triggers_loop_on_failure(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_evaluate_quality_gate triggers agentic_loop when assessment fails."""
        executor.quality_scorer = mock_quality_scorer
        mock_quality_scorer.evaluate.return_value = make_assessment(
            overall_score=40.0, passed=False, improvements_needed=["issue1"]
        )
        mock_quality_scorer.agentic_loop.return_value = (
            {"remediated": True},
            make_assessment(overall_score=90.0, passed=True),
            [],
        )

        result = executor._evaluate_quality_gate(
            sample_context,
            {"output": "test"},
            changed_paths=[],
            status="success",
        )

        assert result is not None
        mock_quality_scorer.agentic_loop.assert_called_once()

    def test_evaluate_quality_gate_handles_exception(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_evaluate_quality_gate handles exception gracefully."""
        executor.quality_scorer = mock_quality_scorer
        mock_quality_scorer.evaluate.side_effect = Exception("scorer error")

        result = executor._evaluate_quality_gate(
            sample_context,
            {"output": "test"},
            changed_paths=[],
            status="success",
        )

        assert result is None
        assert "quality_assessment_error" in sample_context.results

    def test_evaluate_quality_gate_includes_changed_files(
        self, executor, sample_context, mock_quality_scorer
    ):
        """_evaluate_quality_gate passes changed files to evaluation context."""
        executor.quality_scorer = mock_quality_scorer
        mock_quality_scorer.evaluate.return_value = make_assessment(
            overall_score=90.0, passed=True
        )

        executor._evaluate_quality_gate(
            sample_context,
            {"output": "test"},
            changed_paths=[Path("/repo/src/file.py")],
            status="applied",
        )

        call_args = mock_quality_scorer.evaluate.call_args
        evaluation_context = call_args[0][1]
        assert "changed_files" in evaluation_context
        assert "status" in evaluation_context
        assert evaluation_context["status"] == "applied"


class TestQualityLoopImprover:
    """Tests for _quality_loop_improver method."""

    def test_quality_loop_improver_calls_remediation(
        self, executor, sample_context
    ):
        """_quality_loop_improver calls _run_quality_remediation_iteration."""
        loop_context = {"iteration": 0}

        with patch.object(
            executor, "_run_quality_remediation_iteration", return_value={"improved": True}
        ) as mock_method:
            result = executor._quality_loop_improver(
                sample_context, {"original": True}, loop_context
            )

            mock_method.assert_called_once()
            assert result == {"improved": True}

    def test_quality_loop_improver_handles_exception(
        self, executor, sample_context
    ):
        """_quality_loop_improver handles exception and returns current output."""
        loop_context = {"iteration": 0}
        current_output = {"original": True}

        with patch.object(
            executor,
            "_run_quality_remediation_iteration",
            side_effect=Exception("remediation failed"),
        ):
            result = executor._quality_loop_improver(
                sample_context, current_output, loop_context
            )

            # Should return current output on failure
            assert result == current_output
            assert "errors" in loop_context
            assert "remediation failed" in loop_context["errors"][0]

    def test_quality_loop_improver_records_warnings(
        self, executor, sample_context
    ):
        """_quality_loop_improver records warnings on exception."""
        loop_context = {"iteration": 0}

        with patch.object(
            executor,
            "_run_quality_remediation_iteration",
            side_effect=Exception("remediation error"),
        ):
            executor._quality_loop_improver(
                sample_context, {"output": True}, loop_context
            )

            assert "quality_loop_warnings" in sample_context.results
            assert "remediation error" in sample_context.results["quality_loop_warnings"][0]


class TestRunQualityRemediationIteration:
    """Tests for _run_quality_remediation_iteration method."""

    def test_remediation_iteration_prepares_agents(
        self, executor, sample_context
    ):
        """_run_quality_remediation_iteration prepares remediation agents."""
        loop_context = {"improvements_needed": ["fix tests"]}
        sample_context.command.parameters = {}
        sample_context.agents = []

        with patch.object(executor, "_prepare_remediation_agents") as mock_prep:
            with patch.object(executor, "_run_agent_pipeline", return_value={}):
                with patch.object(
                    executor, "_derive_change_plan", return_value=[]
                ):
                    with patch.object(
                        executor, "_apply_change_plan", return_value={"applied": [], "warnings": []}
                    ):
                        with patch.object(
                            executor, "_run_requested_tests", return_value={"passed": True}
                        ):
                            with patch.object(
                                executor, "_summarize_test_results", return_value="tests ok"
                            ):
                                executor._run_quality_remediation_iteration(
                                    sample_context, {}, loop_context, 0
                                )

                                mock_prep.assert_called_once()
                                call_args = mock_prep.call_args[0]
                                assert "quality-engineer" in call_args[1]

    def test_remediation_iteration_runs_agent_pipeline(
        self, executor, sample_context
    ):
        """_run_quality_remediation_iteration runs agent pipeline."""
        loop_context = {"improvements_needed": []}
        sample_context.command.parameters = {}
        sample_context.agents = []

        with patch.object(executor, "_prepare_remediation_agents"):
            with patch.object(
                executor, "_run_agent_pipeline", return_value={}
            ) as mock_pipeline:
                with patch.object(executor, "_derive_change_plan", return_value=[]):
                    with patch.object(
                        executor, "_apply_change_plan", return_value={"applied": [], "warnings": []}
                    ):
                        with patch.object(
                            executor, "_run_requested_tests", return_value={"passed": True}
                        ):
                            with patch.object(
                                executor, "_summarize_test_results", return_value="tests ok"
                            ):
                                executor._run_quality_remediation_iteration(
                                    sample_context, {}, loop_context, 0
                                )

                                mock_pipeline.assert_called_once()

    def test_remediation_iteration_records_status(
        self, executor, sample_context
    ):
        """_run_quality_remediation_iteration records iteration status."""
        loop_context = {"improvements_needed": ["improve coverage"]}
        sample_context.command.parameters = {}
        sample_context.agents = []

        with patch.object(executor, "_prepare_remediation_agents"):
            with patch.object(executor, "_run_agent_pipeline", return_value={}):
                with patch.object(executor, "_derive_change_plan", return_value=[]):
                    with patch.object(
                        executor,
                        "_apply_change_plan",
                        return_value={"applied": ["file.py"], "warnings": []},
                    ):
                        with patch.object(
                            executor,
                            "_run_requested_tests",
                            return_value={"passed": True, "summary": "ok"},
                        ):
                            with patch.object(
                                executor, "_summarize_test_results", return_value="1 passed"
                            ):
                                executor._run_quality_remediation_iteration(
                                    sample_context, {}, loop_context, 0
                                )

                                iterations = sample_context.results.get(
                                    "quality_loop_iterations", []
                                )
                                assert len(iterations) == 1
                                assert iterations[0]["status"] == "improved"

    def test_remediation_iteration_status_no_changes(
        self, executor, sample_context
    ):
        """_run_quality_remediation_iteration sets no-changes status."""
        loop_context = {"improvements_needed": []}
        sample_context.command.parameters = {}
        sample_context.agents = []

        with patch.object(executor, "_prepare_remediation_agents"):
            with patch.object(executor, "_run_agent_pipeline", return_value={}):
                with patch.object(executor, "_derive_change_plan", return_value=[]):
                    with patch.object(
                        executor,
                        "_apply_change_plan",
                        return_value={"applied": [], "warnings": []},
                    ):
                        with patch.object(
                            executor,
                            "_run_requested_tests",
                            return_value={"passed": True},
                        ):
                            with patch.object(
                                executor, "_summarize_test_results", return_value="ok"
                            ):
                                executor._run_quality_remediation_iteration(
                                    sample_context, {}, loop_context, 0
                                )

                                iterations = sample_context.results.get(
                                    "quality_loop_iterations", []
                                )
                                assert iterations[0]["status"] == "no-changes"


class TestPrepareRemediationAgents:
    """Tests for _prepare_remediation_agents method."""

    def test_prepare_remediation_agents_loads_agents(
        self, executor, sample_context, mock_agent_loader
    ):
        """_prepare_remediation_agents loads specified agents."""
        executor.agent_loader = mock_agent_loader
        sample_context.agent_instances = {}
        sample_context.agents = []

        executor._prepare_remediation_agents(
            sample_context, ["quality-engineer", "refactoring-expert"]
        )

        assert mock_agent_loader.load_agent.call_count == 2

    def test_prepare_remediation_agents_skips_existing(
        self, executor, sample_context, mock_agent_loader
    ):
        """_prepare_remediation_agents skips already loaded agents."""
        executor.agent_loader = mock_agent_loader
        sample_context.agent_instances = {"quality-engineer": MagicMock()}
        sample_context.agents = ["quality-engineer"]

        executor._prepare_remediation_agents(
            sample_context, ["quality-engineer", "refactoring-expert"]
        )

        # Should only load refactoring-expert, not quality-engineer
        assert mock_agent_loader.load_agent.call_count == 1
        mock_agent_loader.load_agent.assert_called_with("refactoring-expert")

    def test_prepare_remediation_agents_handles_load_failure(
        self, executor, sample_context, mock_agent_loader
    ):
        """_prepare_remediation_agents handles agent load failures."""
        executor.agent_loader = mock_agent_loader
        mock_agent_loader.load_agent.side_effect = Exception("load failed")
        sample_context.agent_instances = {}
        sample_context.agents = []

        # Should not raise
        executor._prepare_remediation_agents(sample_context, ["failing-agent"])

        assert "quality_loop_warnings" in sample_context.results
        assert "load failed" in sample_context.results["quality_loop_warnings"][0]

    def test_prepare_remediation_agents_adds_to_context(
        self, executor, sample_context, mock_agent_loader
    ):
        """_prepare_remediation_agents adds loaded agents to context."""
        executor.agent_loader = mock_agent_loader
        mock_agent = MagicMock()
        mock_agent_loader.load_agent.return_value = mock_agent
        sample_context.agent_instances = {}
        sample_context.agents = []

        executor._prepare_remediation_agents(sample_context, ["new-agent"])

        assert "new-agent" in sample_context.agent_instances
        assert "new-agent" in sample_context.agents


class TestShouldAutoTriggerQualityLoop:
    """Tests for _should_auto_trigger_quality_loop method."""

    def test_should_auto_trigger_false_when_not_plan_only(
        self, executor, sample_context
    ):
        """_should_auto_trigger_quality_loop returns False when not plan-only."""
        result = executor._should_auto_trigger_quality_loop(sample_context, "applied")
        assert result is False

    def test_should_auto_trigger_false_when_loop_already_enabled(
        self, executor, sample_context
    ):
        """_should_auto_trigger_quality_loop returns False when loop already enabled."""
        sample_context.loop_enabled = True
        result = executor._should_auto_trigger_quality_loop(sample_context, "plan-only")
        assert result is False

    def test_should_auto_trigger_false_without_safe_apply(
        self, executor, sample_context
    ):
        """_should_auto_trigger_quality_loop returns False without safe apply."""
        sample_context.loop_enabled = False
        sample_context.command.flags = {}

        with patch.object(executor, "_safe_apply_requested", return_value=False):
            result = executor._should_auto_trigger_quality_loop(
                sample_context, "plan-only"
            )

        assert result is False

    def test_should_auto_trigger_false_when_files_changed(
        self, executor, sample_context
    ):
        """_should_auto_trigger_quality_loop returns False when files changed."""
        sample_context.loop_enabled = False
        sample_context.results["changed_files"] = ["file.py"]

        with patch.object(executor, "_safe_apply_requested", return_value=True):
            result = executor._should_auto_trigger_quality_loop(
                sample_context, "plan-only"
            )

        assert result is False

    def test_should_auto_trigger_true_with_safe_apply_snapshots(
        self, executor, sample_context
    ):
        """_should_auto_trigger_quality_loop returns True with safe_apply_snapshots."""
        sample_context.loop_enabled = False
        sample_context.results["safe_apply_snapshots"] = {"dir": "/tmp/snap"}
        sample_context.results["changed_files"] = []

        with patch.object(executor, "_safe_apply_requested", return_value=True):
            result = executor._should_auto_trigger_quality_loop(
                sample_context, "plan-only"
            )

        assert result is True

    def test_should_auto_trigger_true_with_safe_apply_directory(
        self, executor, sample_context
    ):
        """_should_auto_trigger_quality_loop returns True with safe_apply_directory."""
        sample_context.loop_enabled = False
        sample_context.results["safe_apply_directory"] = "/tmp/safe"
        sample_context.results["changed_files"] = []

        with patch.object(executor, "_safe_apply_requested", return_value=True):
            result = executor._should_auto_trigger_quality_loop(
                sample_context, "plan-only"
            )

        assert result is True


class TestSerializeAssessment:
    """Tests for _serialize_assessment helper method."""

    def test_serialize_assessment_converts_to_dict(self, executor):
        """_serialize_assessment converts QualityAssessment to dict."""
        assessment = make_assessment(
            overall_score=85.0,
            passed=True,
            improvements_needed=["improve_coverage"],
        )

        result = executor._serialize_assessment(assessment)

        assert isinstance(result, dict)
        assert result["overall_score"] == 85.0
        assert result["passed"] is True
        assert result["improvements_needed"] == ["improve_coverage"]
        assert "timestamp" in result  # Should be ISO-formatted

    def test_serialize_assessment_formats_timestamp(self, executor):
        """_serialize_assessment formats timestamp as ISO string."""
        assessment = make_assessment(overall_score=90.0, passed=True)

        result = executor._serialize_assessment(assessment)

        # timestamp should be ISO-formatted string, not datetime object
        assert isinstance(result["timestamp"], str)
        assert "T" in result["timestamp"]  # ISO format contains T
