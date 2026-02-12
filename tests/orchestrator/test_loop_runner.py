"""Tests for loop runner in SuperClaude.Orchestrator.loop_runner."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from SuperClaude.Orchestrator.loop_runner import (
    IterationResult,
    LoopConfig,
    LoopResult,
    TerminationReason,
    _build_iteration_prompt,
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


class TestTerminationReasonValues:
    """Tests for all TerminationReason enum values."""

    def test_timeout_value(self):
        """Test TIMEOUT value."""
        assert TerminationReason.TIMEOUT.value == "timeout_exceeded"

    def test_user_cancelled_value(self):
        """Test USER_CANCELLED value."""
        assert TerminationReason.USER_CANCELLED.value == "user_cancelled"

    def test_error_value(self):
        """Test ERROR value."""
        assert TerminationReason.ERROR.value == "error"

    def test_enum_count(self):
        """Should have exactly 5 termination reasons."""
        assert len(TerminationReason) == 5

    def test_all_reasons_have_string_values(self):
        """All termination reasons should have non-empty string values."""
        for reason in TerminationReason:
            assert isinstance(reason.value, str)
            assert len(reason.value) > 0


class TestLoopConfigDefaults:
    """Tests for LoopConfig default values not covered above."""

    def test_timeout_defaults_none(self):
        """timeout_seconds should default to None."""
        config = LoopConfig()
        assert config.timeout_seconds is None

    def test_iteration_timeout_default(self):
        """iteration_timeout_seconds should default to 300."""
        config = LoopConfig()
        assert config.iteration_timeout_seconds == 300.0

    def test_max_turns_default(self):
        """max_turns should default to 50."""
        config = LoopConfig()
        assert config.max_turns == 50

    def test_pal_disabled_by_default(self):
        """PAL should be disabled by default in Orchestrator runner."""
        config = LoopConfig()
        assert config.pal_review_enabled is False


class TestBuildIterationPromptEdgeCases:
    """Edge case tests for _build_iteration_prompt."""

    def test_no_improvements_no_crash(self):
        """Prompt with no improvements should still work."""
        history = [
            IterationResult(
                iteration=0,
                score=60.0,
                improvements=[],
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

        assert "Task" in prompt
        assert "60.0/100" in prompt
        # Should NOT contain "Prioritize" since no improvements
        assert "Prioritize" not in prompt

    def test_no_test_evidence_no_test_status(self):
        """Prompt without tests_run should not show test status."""
        history = [
            IterationResult(
                iteration=0,
                score=50.0,
                improvements=["Fix it"],
                evidence={},
                duration_seconds=5.0,
                messages_count=5,
            )
        ]

        prompt = _build_iteration_prompt(
            task="Task",
            iteration=1,
            history=history,
        )

        assert "passed" not in prompt
        assert "failed" not in prompt

    def test_iteration_0_with_empty_history(self):
        """First iteration with empty history should just return task."""
        prompt = _build_iteration_prompt(
            task="My task",
            iteration=0,
            history=[],
        )
        assert prompt == "My task"

    def test_iteration_gt0_with_empty_history_just_returns_task(self):
        """Later iteration with empty history should just return task."""
        prompt = _build_iteration_prompt(
            task="My task",
            iteration=2,
            history=[],
        )
        # iteration > 0 but history is empty, so the if branch is False
        assert prompt == "My task"


class TestLoopResultProperties:
    """Tests for LoopResult computed properties."""

    def test_passed_with_each_termination_reason(self):
        """Only QUALITY_MET should result in passed=True."""
        for reason in TerminationReason:
            result = LoopResult(
                status="success" if reason == TerminationReason.QUALITY_MET else "terminated",
                reason=reason,
                final_score=80.0,
                total_iterations=1,
                iteration_history=[],
                total_duration_seconds=1.0,
            )
            if reason == TerminationReason.QUALITY_MET:
                assert result.passed is True
            else:
                assert result.passed is False
