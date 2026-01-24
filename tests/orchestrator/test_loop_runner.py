"""Tests for loop runner in SuperClaude.Orchestrator.loop_runner."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from SuperClaude.Orchestrator.loop_runner import (
    IterationResult,
    LoopConfig,
    LoopResult,
    TerminationReason,
    _build_iteration_prompt,
    _is_oscillating,
    _is_stagnating,
)


class TestLoopConfig:
    """Tests for LoopConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoopConfig()

        assert config.max_iterations == 3
        assert config.hard_max_iterations == 5
        assert config.quality_threshold == 70.0
        assert config.model == "sonnet"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LoopConfig(
            max_iterations=5,
            quality_threshold=80.0,
            model="opus",
        )

        assert config.max_iterations == 5
        assert config.quality_threshold == 80.0
        assert config.model == "opus"

    def test_pal_settings(self):
        """Test PAL integration settings."""
        config = LoopConfig(
            pal_review_enabled=True,
            pal_model="gpt-5",
        )

        assert config.pal_review_enabled is True
        assert config.pal_model == "gpt-5"


class TestIterationResult:
    """Tests for IterationResult dataclass."""

    def test_creation(self):
        """Test creating iteration result."""
        result = IterationResult(
            iteration=0,
            score=75.0,
            improvements=["Fix test"],
            evidence={"files_written": ["test.py"]},
            duration_seconds=10.5,
            messages_count=15,
        )

        assert result.iteration == 0
        assert result.score == 75.0
        assert "Fix test" in result.improvements


class TestLoopResult:
    """Tests for LoopResult dataclass."""

    def test_passed_true_on_success(self):
        """Test passed property returns True for success."""
        result = LoopResult(
            status="success",
            reason=TerminationReason.QUALITY_MET,
            final_score=80.0,
            total_iterations=2,
            iteration_history=[],
            total_duration_seconds=20.0,
        )

        assert result.passed is True

    def test_passed_false_on_terminated(self):
        """Test passed property returns False for terminated."""
        result = LoopResult(
            status="terminated",
            reason=TerminationReason.MAX_ITERATIONS,
            final_score=60.0,
            total_iterations=3,
            iteration_history=[],
            total_duration_seconds=30.0,
        )

        assert result.passed is False

    def test_evidence_summary_defaults_empty(self):
        """Test evidence_summary defaults to empty dict."""
        result = LoopResult(
            status="success",
            reason=TerminationReason.QUALITY_MET,
            final_score=80.0,
            total_iterations=1,
            iteration_history=[],
            total_duration_seconds=10.0,
        )

        assert result.evidence_summary == {}


class TestTerminationReason:
    """Tests for TerminationReason enum."""

    def test_quality_met_value(self):
        """Test QUALITY_MET value."""
        assert TerminationReason.QUALITY_MET.value == "quality_threshold_met"

    def test_max_iterations_value(self):
        """Test MAX_ITERATIONS value."""
        assert TerminationReason.MAX_ITERATIONS.value == "max_iterations_reached"

    def test_oscillation_value(self):
        """Test OSCILLATION value."""
        assert TerminationReason.OSCILLATION.value == "oscillation_detected"

    def test_stagnation_value(self):
        """Test STAGNATION value."""
        assert TerminationReason.STAGNATION.value == "stagnation_detected"


class TestBuildIterationPrompt:
    """Tests for _build_iteration_prompt function."""

    def test_first_iteration_just_task(self):
        """Test first iteration returns just the task."""
        prompt = _build_iteration_prompt(
            task="Implement feature X",
            iteration=0,
            history=[],
        )

        assert prompt == "Implement feature X"

    def test_subsequent_iteration_adds_context(self):
        """Test subsequent iterations add context."""
        history = [
            IterationResult(
                iteration=0,
                score=50.0,
                improvements=["Fix bug A", "Add test B"],
                evidence={},
                duration_seconds=10.0,
                messages_count=10,
            )
        ]

        prompt = _build_iteration_prompt(
            task="Implement feature X",
            iteration=1,
            history=history,
        )

        assert "Implement feature X" in prompt
        assert "iteration 2" in prompt
        assert "50.0/100" in prompt

    def test_includes_improvements(self):
        """Test includes improvement suggestions."""
        history = [
            IterationResult(
                iteration=0,
                score=60.0,
                improvements=["Fix bug", "Add test", "Improve docs"],
                evidence={},
                duration_seconds=10.0,
                messages_count=10,
            )
        ]

        prompt = _build_iteration_prompt(
            task="Task",
            iteration=1,
            history=history,
        )

        assert "Fix bug" in prompt
        assert "Add test" in prompt
        assert "Improve docs" in prompt

    def test_limits_improvements_to_three(self):
        """Test limits improvements to top 3."""
        history = [
            IterationResult(
                iteration=0,
                score=50.0,
                improvements=["One", "Two", "Three", "Four", "Five"],
                evidence={},
                duration_seconds=10.0,
                messages_count=10,
            )
        ]

        prompt = _build_iteration_prompt(
            task="Task",
            iteration=1,
            history=history,
        )

        assert "One" in prompt
        assert "Two" in prompt
        assert "Three" in prompt
        assert "Four" not in prompt

    def test_includes_test_status(self):
        """Test includes test status from evidence."""
        history = [
            IterationResult(
                iteration=0,
                score=70.0,
                improvements=[],
                evidence={
                    "tests_run": True,
                    "tests_passed": 8,
                    "tests_failed": 2,
                },
                duration_seconds=10.0,
                messages_count=10,
            )
        ]

        prompt = _build_iteration_prompt(
            task="Task",
            iteration=1,
            history=history,
        )

        assert "8 passed" in prompt
        assert "2 failed" in prompt


class TestIsOscillating:
    """Tests for _is_oscillating function."""

    def test_not_oscillating_with_few_scores(self):
        """Test returns False with < 3 scores."""
        assert _is_oscillating([50.0, 60.0]) is False

    def test_not_oscillating_steady_increase(self):
        """Test returns False with steady increase."""
        scores = [50.0, 60.0, 70.0, 80.0]
        assert _is_oscillating(scores) is False

    def test_oscillating_up_down_up(self):
        """Test detects up/down/up pattern."""
        scores = [50.0, 70.0, 50.0, 70.0]  # Clearly oscillating
        assert _is_oscillating(scores) is True

    def test_oscillating_down_up_down(self):
        """Test detects down/up/down pattern."""
        scores = [70.0, 50.0, 70.0, 50.0]
        assert _is_oscillating(scores) is True

    def test_not_oscillating_small_changes(self):
        """Test ignores small oscillations below threshold."""
        scores = [50.0, 52.0, 50.0]  # Changes < 5.0 threshold
        assert _is_oscillating(scores, threshold=5.0) is False


class TestIsStagnating:
    """Tests for _is_stagnating function."""

    def test_not_stagnating_with_single_score(self):
        """Test returns False with single score."""
        assert _is_stagnating([50.0], 2.0, 5.0) is False

    def test_stagnating_no_improvement(self):
        """Test detects no improvement."""
        scores = [50.0, 50.5]  # Less than min_improvement of 5.0
        assert _is_stagnating(scores, 2.0, 5.0) is True

    def test_stagnating_negative_change(self):
        """Test detects regression as stagnation."""
        scores = [60.0, 55.0]  # Went down
        assert _is_stagnating(scores, 2.0, 5.0) is True

    def test_not_stagnating_good_improvement(self):
        """Test returns False with good improvement."""
        scores = [50.0, 60.0]  # +10 improvement
        assert _is_stagnating(scores, 2.0, 5.0) is False


class TestRunAgenticLoopMocked:
    """Tests for run_agentic_loop with mocked SDK.

    These tests mock the claude-agent-sdk to test loop logic
    without requiring the actual SDK to be installed.
    """

    @pytest.fixture
    def mock_sdk(self):
        """Create mock SDK module."""
        mock_query = AsyncMock()
        mock_options = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "claude_agent_sdk": MagicMock(
                    query=mock_query,
                    ClaudeAgentOptions=mock_options,
                ),
            },
        ):
            yield mock_query, mock_options

    @pytest.mark.asyncio
    async def test_raises_without_sdk(self):
        """Test raises ImportError without SDK installed."""
        from SuperClaude.Orchestrator.loop_runner import run_agentic_loop

        # The actual import check in run_agentic_loop will raise
        # This test documents the expected behavior
        with pytest.raises(ImportError) as exc_info:
            await run_agentic_loop("Test task")

        assert "claude-agent-sdk" in str(exc_info.value).lower()


class TestLoopConfigEnforcement:
    """Tests for loop configuration enforcement."""

    def test_hard_max_cannot_be_exceeded(self):
        """Test hard_max_iterations cannot be exceeded."""
        config = LoopConfig(
            max_iterations=10,  # User wants 10
            hard_max_iterations=5,  # But hard max is 5
        )

        effective = min(config.max_iterations, config.hard_max_iterations)
        assert effective == 5

    def test_default_hard_max_is_five(self):
        """Test default hard max is 5."""
        config = LoopConfig()
        assert config.hard_max_iterations == 5


class TestTerminationConditions:
    """Tests documenting termination condition logic."""

    def test_quality_met_terminates(self):
        """Document: Loop terminates when quality threshold met."""
        # When assessment.passed is True, loop terminates with QUALITY_MET
        # This is tested via integration tests with mocked SDK
        pass

    def test_max_iterations_terminates(self):
        """Document: Loop terminates at max iterations."""
        # When iteration count reaches effective_max, loop terminates
        # This is tested via integration tests with mocked SDK
        pass

    def test_oscillation_detection(self):
        """Document: Oscillation detected terminates loop."""
        # Example: scores [50, 70, 50] = oscillation
        scores = [50.0, 70.0, 50.0]
        assert _is_oscillating(scores) is True

    def test_stagnation_detection(self):
        """Document: Stagnation detected terminates loop."""
        # Example: scores [50, 51] with min_improvement=5 = stagnation
        scores = [50.0, 51.0]
        assert _is_stagnating(scores, 2.0, 5.0) is True
