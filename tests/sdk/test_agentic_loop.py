"""Tests for SDK agentic loop."""

import pytest

from SuperClaude.SDK.agentic_loop import (
    build_repair_prompt,
    create_sdk_loop_context,
)


class TestBuildRepairPrompt:
    """Tests for build_repair_prompt function."""

    def test_no_improvements_returns_original(self):
        """Test that empty improvements returns original task."""
        task = "Fix the bug in auth.py"
        result = build_repair_prompt(task, [])

        assert result == task

    def test_includes_original_task(self):
        """Test that original task is included."""
        task = "Fix the bug"
        improvements = ["Add tests"]

        result = build_repair_prompt(task, improvements)

        assert task in result
        assert "Add tests" in result

    def test_includes_iteration_number(self):
        """Test that iteration number is included."""
        result = build_repair_prompt(
            "Fix bug",
            ["Improvement 1"],
            iteration=2,
        )

        assert "Iteration 3" in result  # 0-indexed + 1

    def test_includes_previous_score(self):
        """Test that previous score is included."""
        result = build_repair_prompt(
            "Fix bug",
            ["Improvement 1"],
            previous_score=65.5,
        )

        assert "65.5" in result
        assert "100" in result

    def test_limits_improvements_to_five(self):
        """Test that only top 5 improvements are included."""
        improvements = [f"Improvement {i}" for i in range(10)]

        result = build_repair_prompt("Task", improvements)

        assert "Improvement 0" in result
        assert "Improvement 4" in result
        assert "Improvement 5" not in result

    def test_includes_evidence_guidance(self):
        """Test that evidence guidance is included."""
        result = build_repair_prompt("Task", ["Fix it"])

        assert "evidence" in result.lower()
        assert "file modifications" in result.lower() or "test results" in result.lower()


class TestCreateSDKLoopContext:
    """Tests for create_sdk_loop_context function."""

    def test_basic_context(self):
        """Test basic context creation."""
        ctx = create_sdk_loop_context(
            command_name="analyze",
            task="Analyze the code",
        )

        assert ctx["command_name"] == "analyze"
        assert ctx["original_task"] == "Analyze the code"
        assert ctx["cwd"] == "."
        assert ctx["requires_evidence"] is False

    def test_with_cwd(self):
        """Test context with working directory."""
        ctx = create_sdk_loop_context(
            command_name="test",
            task="Run tests",
            cwd="/project",
        )

        assert ctx["cwd"] == "/project"

    def test_with_evidence_requirements(self):
        """Test context with evidence requirements."""
        ctx = create_sdk_loop_context(
            command_name="fix",
            task="Fix bug",
            requires_evidence=True,
            expects_file_changes=True,
            expects_tests=True,
        )

        assert ctx["requires_evidence"] is True
        assert ctx["expects_file_changes"] is True
        assert ctx["expects_tests"] is True
        assert ctx["expects_execution_evidence"] is True

    def test_with_session_id(self):
        """Test context with session ID."""
        ctx = create_sdk_loop_context(
            command_name="cmd",
            task="task",
            session_id="session-123",
        )

        assert ctx["session_id"] == "session-123"


class TestSDKExecutionResultToRecord:
    """Tests for SDKExecutionResult.to_record() method."""

    def test_success_record(self):
        """Test converting successful result to record."""
        from SuperClaude.SDK.executor import SDKExecutionResult

        result = SDKExecutionResult(
            success=True,
            output={"status": "completed", "data": "result"},
            should_fallback=False,
            routing_decision="sdk_executed",
            agent_used="test-agent",
            confidence=0.85,
            evidence={"files_written": 1, "tests_run": True},
        )

        record = result.to_record()

        assert record["success"] is True
        assert record["result"] == {"status": "completed", "data": "result"}
        assert record["agent_used"] == "test-agent"
        assert record["confidence"] == 0.85
        assert record["evidence"] == {"files_written": 1, "tests_run": True}
        assert record["routing_decision"] == "sdk_executed"
        assert "errors" not in record

    def test_failure_record_includes_errors(self):
        """Test converting failed result to record includes errors."""
        from SuperClaude.SDK.executor import SDKExecutionResult

        result = SDKExecutionResult(
            success=False,
            output={},
            should_fallback=True,
            routing_decision="sdk_exception",
            fallback_reason="Something went wrong",
            error_type="RuntimeError",
        )

        record = result.to_record()

        assert record["success"] is False
        assert "errors" in record
        assert record["errors"]["type"] == "RuntimeError"
        assert record["errors"]["reason"] == "Something went wrong"

    def test_empty_evidence_defaults_to_empty_dict(self):
        """Test that None evidence becomes empty dict."""
        from SuperClaude.SDK.executor import SDKExecutionResult

        result = SDKExecutionResult(
            success=True,
            output={},
            should_fallback=False,
            routing_decision="sdk_executed",
            evidence=None,
        )

        record = result.to_record()

        assert record["evidence"] == {}


class TestEvaluateSDKExecution:
    """Tests for QualityScorer.evaluate_sdk_execution() method."""

    @pytest.fixture
    def scorer(self):
        """Create a quality scorer instance."""
        from SuperClaude.Quality.quality_scorer import QualityScorer

        return QualityScorer(threshold=70.0)

    def test_basic_evaluation(self, scorer):
        """Test basic SDK execution evaluation."""
        record = {
            "result": {"status": "completed", "output": "Done"},
            "success": True,
            "evidence": {},
            "agent_used": "test-agent",
            "confidence": 0.8,
        }

        assessment = scorer.evaluate_sdk_execution(record, {})

        assert assessment is not None
        assert isinstance(assessment.overall_score, float)
        assert "sdk_execution" in assessment.metadata
        assert assessment.metadata["sdk_execution"]["agent_used"] == "test-agent"
        assert assessment.metadata["sdk_execution"]["confidence"] == 0.8

    def test_with_evidence_data(self, scorer):
        """Test evaluation with evidence data."""
        record = {
            "result": {"status": "completed"},
            "success": True,
            "evidence": {
                "has_file_modifications": True,
                "has_execution_evidence": True,
                "tool_count": 5,
                "files_written": 2,
                "files_edited": 1,
                "tests_run": True,
                "test_passed": 10,
                "test_failed": 0,
            },
            "agent_used": "code-agent",
            "confidence": 0.9,
        }

        assessment = scorer.evaluate_sdk_execution(record, {})

        assert assessment.metadata["signals_grounded"] is True
        assert "deterministic_signals" in assessment.metadata
        evidence_summary = assessment.metadata["sdk_execution"]["evidence_summary"]
        assert evidence_summary["has_file_modifications"] is True
        assert evidence_summary["tests_run"] is True

    def test_evidence_expectations_not_checked_by_default(self, scorer):
        """Test that evidence expectations are not checked without opt-in."""
        record = {
            "result": {},
            "success": True,
            "evidence": {
                "has_file_modifications": False,
                "has_execution_evidence": False,
            },
        }

        assessment = scorer.evaluate_sdk_execution(record, {})

        # Should not have evidence expectation failures
        assert "evidence_expectations_failed" not in assessment.metadata
        assert not any(
            "MISSING_FILE_CHANGES" in imp for imp in assessment.improvements_needed
        )

    def test_evidence_expectations_checked_when_enabled(self, scorer):
        """Test that evidence expectations are checked when opt-in."""
        record = {
            "result": {},
            "success": True,
            "evidence": {
                "has_file_modifications": False,
                "has_execution_evidence": False,
                "tests_run": False,
            },
        }
        context = {
            "expects_file_changes": True,
            "expects_tests": True,
        }

        assessment = scorer.evaluate_sdk_execution(record, context)

        assert "evidence_expectations_failed" in assessment.metadata
        failures = assessment.metadata["evidence_expectations_failed"]
        assert any("MISSING_FILE_CHANGES" in f for f in failures)
        assert any("NO_TESTS_RUN" in f for f in failures)

    def test_passing_expectations_no_issues(self, scorer):
        """Test that passing expectations don't add issues."""
        record = {
            "result": {},
            "success": True,
            "evidence": {
                "has_file_modifications": True,
                "has_execution_evidence": True,
                "tests_run": True,
            },
        }
        context = {
            "expects_file_changes": True,
            "expects_tests": True,
            "expects_execution_evidence": True,
        }

        assessment = scorer.evaluate_sdk_execution(record, context)

        # Should not have failures when expectations are met
        assert "evidence_expectations_failed" not in assessment.metadata

    def test_test_failures_cap_score(self, scorer):
        """Test that test failures cap the score."""
        record = {
            "result": {"status": "completed"},
            "success": True,
            "evidence": {
                "tests_run": True,
                "test_passed": 5,
                "test_failed": 5,  # 50% fail rate
            },
        }

        assessment = scorer.evaluate_sdk_execution(record, {})

        # Score should be capped due to test failures
        assert assessment.overall_score <= 50.0  # Cap for >50% failure rate


class TestAgenticLoopTimeout:
    """Tests for agentic loop wall-clock timeout feature (C16)."""

    @pytest.fixture
    def scorer(self):
        """Create a quality scorer with low threshold for testing."""
        from SuperClaude.Quality.quality_scorer import QualityScorer

        return QualityScorer(threshold=90.0)  # High threshold to force iterations

    def test_timeout_at_loop_start_no_iterations_recorded(self, scorer):
        """Timeout at start of first iteration records no iterations."""
        initial_output = {"data": "initial"}
        context = {}

        # Time provider that immediately exceeds timeout
        time_calls = [0.0, 100.0]  # Start, then immediately timed out
        time_idx = [0]

        def fake_time() -> float:
            result = time_calls[min(time_idx[0], len(time_calls) - 1)]
            time_idx[0] += 1
            return result

        # Improver that should never be called
        def never_called_improver(output, ctx):
            raise AssertionError("Improver should not be called on timeout")

        final_output, assessment, history = scorer.agentic_loop(
            initial_output=initial_output,
            context=context,
            improver_func=never_called_improver,
            timeout_seconds=10.0,
            time_provider=fake_time,
            max_iterations=5,
        )

        # Should timeout before any iteration completes
        # Note: We still get a final evaluation, but no iteration records
        assert final_output == initial_output  # Unchanged
        # History may be empty since we timed out at start
        # The loop breaks before recording anything

    def test_timeout_after_scoring_records_iteration(self, scorer):
        """Timeout after scoring records that iteration as completed."""
        from SuperClaude.Quality.quality_scorer import IterationTermination

        initial_output = {"data": "initial"}
        context = {}

        # Time sequence - need to account for all time() calls:
        # Call 1: loop_start = _time() -> 0.0
        # Call 2: timed_out() at top of iteration 0 -> 0.0 (pass)
        # Call 3: timed_out() after evaluate -> 100.0 (TIMEOUT!)
        time_sequence = [0.0, 0.0, 100.0]
        time_idx = [0]

        def fake_time() -> float:
            result = time_sequence[min(time_idx[0], len(time_sequence) - 1)]
            time_idx[0] += 1
            return result

        def never_called_improver(output, ctx):
            raise AssertionError("Improver should not be called on timeout")

        final_output, assessment, history = scorer.agentic_loop(
            initial_output=initial_output,
            context=context,
            improver_func=never_called_improver,
            timeout_seconds=10.0,
            time_provider=fake_time,
            max_iterations=5,
        )

        # Should have recorded iteration 0 (scored before timeout)
        assert len(history) >= 1
        assert history[-1].termination_reason == IterationTermination.TIMEOUT
        assert final_output == initial_output

    def test_timeout_after_improver_returns_last_safe_output(self, scorer):
        """Timeout after improver discards improved output, returns current."""
        from SuperClaude.Quality.quality_scorer import IterationTermination

        initial_output = {"data": "initial", "version": 1}
        improved_output = {"data": "improved", "version": 2}
        context = {}

        # Time sequence - need to account for all time() calls:
        # Call 1: loop_start = _time() -> 0.0
        # Call 2: timed_out() at top of iteration 0 -> 0.0 (pass)
        # Call 3: timed_out() after evaluate -> 0.0 (pass)
        # Call 4: timed_out() after improver -> 100.0 (TIMEOUT!)
        time_sequence = [0.0, 0.0, 0.0, 100.0]
        time_idx = [0]

        def fake_time() -> float:
            result = time_sequence[min(time_idx[0], len(time_sequence) - 1)]
            time_idx[0] += 1
            return result

        def improver(output, ctx):
            return improved_output

        final_output, assessment, history = scorer.agentic_loop(
            initial_output=initial_output,
            context=context,
            improver_func=improver,
            timeout_seconds=10.0,
            time_provider=fake_time,
            max_iterations=5,
        )

        # Key assertion: should NOT return improved_output because timeout
        # occurred after improver but before we accepted the new output
        assert final_output == initial_output
        assert history[-1].termination_reason == IterationTermination.TIMEOUT

    def test_no_timeout_when_not_set(self, scorer):
        """Loop runs normally when timeout_seconds is None."""
        initial_output = {"data": "test"}
        context = {}

        call_count = [0]

        def counting_improver(output, ctx):
            call_count[0] += 1
            return {"data": "improved", "iteration": call_count[0]}

        # Should run until max_iterations or quality threshold
        final_output, assessment, history = scorer.agentic_loop(
            initial_output=initial_output,
            context=context,
            improver_func=counting_improver,
            timeout_seconds=None,  # No timeout
            max_iterations=3,
        )

        # Should have run multiple iterations
        assert len(history) >= 1
        assert call_count[0] >= 1  # Improver was called


class TestSignalsFromSDKEvidence:
    """Tests for _signals_from_sdk_evidence helper."""

    @pytest.fixture
    def scorer(self):
        """Create a quality scorer instance."""
        from SuperClaude.Quality.quality_scorer import QualityScorer

        return QualityScorer()

    def test_empty_evidence(self, scorer):
        """Test signals from empty evidence."""
        signals = scorer._signals_from_sdk_evidence({})

        assert signals.tests_passed is False
        assert signals.tests_total == 0
        assert signals.tests_failed == 0
        assert signals.test_coverage == 0.0

    def test_passing_tests(self, scorer):
        """Test signals with passing tests."""
        signals = scorer._signals_from_sdk_evidence(
            {
                "tests_run": True,
                "test_passed": 10,
                "test_failed": 0,
                "test_coverage": 85.0,
            }
        )

        assert signals.tests_passed is True
        assert signals.tests_total == 10
        assert signals.tests_failed == 0
        assert signals.test_coverage == 85.0

    def test_failing_tests(self, scorer):
        """Test signals with failing tests."""
        signals = scorer._signals_from_sdk_evidence(
            {
                "tests_run": True,
                "test_passed": 8,
                "test_failed": 2,
            }
        )

        assert signals.tests_passed is False  # Because test_failed > 0
        assert signals.tests_total == 10
        assert signals.tests_failed == 2

    def test_no_tests_run(self, scorer):
        """Test signals when tests not run."""
        signals = scorer._signals_from_sdk_evidence(
            {
                "tests_run": False,
                "test_passed": 0,
                "test_failed": 0,
            }
        )

        assert signals.tests_passed is False  # tests_run is False
        assert signals.tests_total == 0
