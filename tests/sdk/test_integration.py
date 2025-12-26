"""Integration tests for SDK execution path.

These tests verify the end-to-end behavior from ExecutionFacade through
SDKExecutor, agentic loop, and quality scoring.

Test Suites:
- Suite A: Routing & fallback decisions (Facade contract)
- Suite B: Agent selection & delegation boundary
- Suite C: Agentic loop control (termination + quality behavior)
- Suite E: Hooks/evidence correctness (observer invariants)

Tier 1 (must-have, stable, high ROI):
- A1-A5 Routing/fallback
- C10, C13, C14, C15 Loop termination + scorer safety
- E22 Hooks called once per iteration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from SuperClaude.SDK.executor import (
    SDKExecutionResult,
    SDKExecutor,
    SDKExecutorConfig,
)
from SuperClaude.SDK.types import TerminationReason

# =============================================================================
# Test Fixtures and Mocks
# =============================================================================


@dataclass
class MockCommand:
    """Mock command for testing."""

    name: str = "test"
    arguments: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class MockContext:
    """Mock command context for testing."""

    command: MockCommand = field(default_factory=MockCommand)
    session_id: str = "test-session"
    cwd: str = "/test"
    requires_evidence: bool = False


@dataclass
class MockSDKSelection:
    """Mock SDK selection result."""

    agent_name: str
    confidence: float
    use_sdk: bool = True
    sdk_definition: dict[str, Any] | None = field(default_factory=dict)


class MockSDKClient:
    """Mock SDK client for deterministic testing."""

    def __init__(self, responses: list[list[dict[str, Any]]] | None = None):
        """Initialize with scripted responses.

        Args:
            responses: List of message lists. Each inner list is returned
                      for one call to execute_with_agent(). Messages have
                      'type' and 'content' keys.
        """
        self._responses = responses or [[{"type": "result", "content": "Success"}]]
        self._call_count = 0
        self._sdk_available = True

    async def execute_with_agent(
        self,
        task: str,
        context: dict[str, Any],
        agent_name: str,
        hooks: Any = None,
    ):
        """Yield scripted messages."""
        if self._call_count < len(self._responses):
            messages = self._responses[self._call_count]
            self._call_count += 1
        else:
            messages = self._responses[-1]  # Repeat last response

        for msg in messages:
            # Create a mock message object with type and content
            mock_msg = MagicMock()
            mock_msg.type = msg.get("type", "text")
            mock_msg.content = msg.get("content", "")
            yield mock_msg


class MockSelector:
    """Mock agent selector for deterministic testing."""

    def __init__(
        self, selection: MockSDKSelection | None = None, selections: list | None = None
    ):
        """Initialize with scripted selections.

        Args:
            selection: Single selection to return for all calls.
            selections: List of selections to return sequentially.
        """
        self._selection = selection
        self._selections = selections or []
        self._call_count = 0

    def select_for_sdk(self, context: dict[str, Any]) -> MockSDKSelection | None:
        """Return scripted selection."""
        if self._selections:
            if self._call_count < len(self._selections):
                result = self._selections[self._call_count]
                self._call_count += 1
                return result
            return self._selections[-1]
        return self._selection


# =============================================================================
# Suite A: Routing & Fallback Decisions
# =============================================================================


class TestSuiteA_RoutingAndFallback:
    """Suite A: Routing & fallback decisions (Facade contract)."""

    @pytest.mark.asyncio
    async def test_a1_sdk_disabled_never_calls_executor(self):
        """A1: SDK disabled → never calls SDKExecutor."""
        # Setup: SDK explicitly disabled
        config = SDKExecutorConfig(enabled=False, allowlist={"test"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        # Execute
        result = await executor.execute(context)

        # Assert: fallback requested, SDK not called
        assert result.should_fallback is True
        assert result.routing_decision == "sdk_not_enabled"
        assert result.termination_reason == TerminationReason.FALLBACK
        assert client._call_count == 0

    @pytest.mark.asyncio
    async def test_a2_sdk_enabled_success_no_fallback(self):
        """A2: SDK enabled + SDKExecutor returns success (should_fallback=False)."""
        # Setup: SDK enabled and configured
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient([[{"type": "result", "content": "Done!"}]])
        selector = MockSelector(MockSDKSelection("code-agent", 0.85))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        # Execute
        result = await executor.execute(context)

        # Assert: success, no fallback
        assert result.success is True
        assert result.should_fallback is False
        assert result.routing_decision == "sdk_executed"
        assert result.agent_used == "code-agent"
        assert result.confidence == 0.85
        assert result.termination_reason == TerminationReason.SINGLE_ITERATION
        assert client._call_count == 1

    @pytest.mark.asyncio
    async def test_a3_command_not_in_allowlist_fallback(self):
        """A3: SDK enabled + command not in allowlist → fallback."""
        # Setup: SDK enabled but command not allowed
        config = SDKExecutorConfig(enabled=True, allowlist={"analyze", "review"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext(command=MockCommand(name="build"))

        # Execute
        result = await executor.execute(context)

        # Assert: fallback due to command not allowed
        assert result.should_fallback is True
        assert result.routing_decision == "command_not_allowed"
        assert "build" in result.fallback_reason.lower()
        assert client._call_count == 0

    @pytest.mark.asyncio
    async def test_a4_sdk_exception_triggers_fallback(self):
        """A4: SDK enabled + SDKExecutor raises exception → fallback."""
        # Setup: SDK will raise an exception
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        # Create a client that raises
        async def raise_on_execute(*args, **kwargs):
            raise RuntimeError("SDK connection failed")
            yield  # Make it a generator

        client = MockSDKClient()
        client.execute_with_agent = raise_on_execute

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        # Execute
        result = await executor.execute(context)

        # Assert: fallback with error info
        assert result.should_fallback is True
        assert result.routing_decision == "sdk_exception"
        assert result.error_type == "RuntimeError"
        assert result.termination_reason == TerminationReason.EXECUTION_ERROR

    @pytest.mark.asyncio
    async def test_a5_low_confidence_triggers_fallback(self):
        """A5: SDK selection confidence below threshold → fallback."""
        # Setup: confidence below threshold
        config = SDKExecutorConfig(
            enabled=True, allowlist={"test"}, confidence_threshold=0.7
        )
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.5, use_sdk=True))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        # Execute
        result = await executor.execute(context)

        # Assert: fallback due to low confidence
        assert result.should_fallback is True
        assert result.routing_decision == "low_confidence"
        assert "0.50" in result.fallback_reason
        assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_a5b_selection_declined_triggers_fallback(self):
        """A5b: SDK selection declined (use_sdk=False) → fallback."""
        # Setup: selector declines SDK
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9, use_sdk=False))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        # Execute
        result = await executor.execute(context)

        # Assert: fallback due to selection decline
        assert result.should_fallback is True
        assert result.routing_decision == "selection_declined"

    @pytest.mark.asyncio
    async def test_force_sdk_bypasses_gates(self):
        """force_sdk=True bypasses enabled/allowlist/confidence gates."""
        # Setup: everything disabled
        config = SDKExecutorConfig(
            enabled=False, allowlist=set(), confidence_threshold=0.99
        )
        client = MockSDKClient([[{"type": "result", "content": "Forced!"}]])
        selector = MockSelector(MockSDKSelection("forced-agent", 0.1))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext(command=MockCommand(name="any_command"))

        # Execute with force
        result = await executor.execute(context, force_sdk=True)

        # Assert: success despite disabled config
        assert result.success is True
        assert result.should_fallback is False
        assert result.agent_used == "forced-agent"

    @pytest.mark.asyncio
    async def test_disable_sdk_override_highest_priority(self):
        """disable_sdk=True takes precedence over everything."""
        # Setup: everything enabled
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        # Execute with disable override
        result = await executor.execute(context, disable_sdk=True)

        # Assert: fallback even though everything is enabled
        assert result.should_fallback is True
        assert result.routing_decision == "sdk_disabled_override"
        assert client._call_count == 0


# =============================================================================
# Suite B: Agent Selection & Delegation
# =============================================================================


class TestSuiteB_AgentSelection:
    """Suite B: Agent selection & delegation boundary."""

    @pytest.mark.asyncio
    async def test_b6_single_eligible_agent_selected(self):
        """B6: Single eligible agent → deterministic selection."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("only-agent", 0.75))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)

        assert result.agent_used == "only-agent"
        assert result.confidence == 0.75

    @pytest.mark.asyncio
    async def test_b8_no_eligible_agent_fallback(self):
        """B8: No eligible agent for SDK → falls back."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        # Selector returns selection with no SDK definition
        selector = MockSelector(MockSDKSelection("agent", 0.9, sdk_definition=None))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "no_sdk_definition"

    @pytest.mark.asyncio
    async def test_no_selector_configured_fallback(self):
        """No selector configured → falls back."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()

        executor = SDKExecutor(client=client, selector=None, config=config)
        context = MockContext()

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "no_selector"


# =============================================================================
# Suite C: Agentic Loop Control
# =============================================================================


class TestSuiteC_AgenticLoopControl:
    """Suite C: Agentic loop control (termination + quality behavior).

    Note: These tests focus on the SDKExecutor single-iteration behavior.
    Full agentic loop tests are in test_agentic_loop.py.
    """

    @pytest.mark.asyncio
    async def test_c10_single_iteration_success(self):
        """C10: Single iteration happy path."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient([[{"type": "result", "content": "Complete!"}]])
        selector = MockSelector(MockSDKSelection("fast-agent", 0.95))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)

        assert result.success is True
        assert result.iteration_count == 1
        assert result.termination_reason == TerminationReason.SINGLE_ITERATION

    @pytest.mark.asyncio
    async def test_c13_result_contains_iteration_count(self):
        """C13: Result contains iteration_count field."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)

        # Verify iteration_count is present
        assert hasattr(result, "iteration_count")
        assert isinstance(result.iteration_count, int)
        assert result.iteration_count >= 1

        # Verify it's in to_record()
        record = result.to_record()
        assert "iteration_count" in record
        assert record["iteration_count"] == result.iteration_count

    @pytest.mark.asyncio
    async def test_c14_execution_error_graceful_degradation(self):
        """C14: Execution error degrades gracefully, never crashes."""

        async def error_generator(*args, **kwargs):
            raise ValueError("Simulated SDK error")
            yield

        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        client.execute_with_agent = error_generator
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        # Should NOT raise - degrades gracefully
        result = await executor.execute(context)

        assert result.success is False
        assert result.should_fallback is True
        assert result.error_type == "ValueError"
        assert result.termination_reason == TerminationReason.EXECUTION_ERROR

    @pytest.mark.asyncio
    async def test_c15_error_message_in_stream_triggers_fallback(self):
        """C15: Error message in SDK stream triggers fallback."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient([[{"type": "error", "content": "Tool failed"}]])
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "sdk_error_message"
        assert result.termination_reason == TerminationReason.EXECUTION_ERROR


# =============================================================================
# Suite E: Hooks/Evidence Correctness
# =============================================================================


class TestSuiteE_HooksEvidence:
    """Suite E: Hooks/evidence correctness (observer invariants)."""

    @pytest.mark.asyncio
    async def test_e22_evidence_collected_on_success(self):
        """E22: Evidence is collected on successful execution."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient([[{"type": "result", "content": "Done"}]])
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext(requires_evidence=True)

        result = await executor.execute(context)

        assert result.success is True
        # Evidence should be collected (empty dict if no actual tool calls)
        assert result.evidence is not None
        assert isinstance(result.evidence, dict)

    @pytest.mark.asyncio
    async def test_evidence_in_record(self):
        """Evidence is included in to_record() output."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)
        record = result.to_record()

        assert "evidence" in record
        assert isinstance(record["evidence"], dict)

    @pytest.mark.asyncio
    async def test_termination_reason_in_record(self):
        """Termination reason is serialized in to_record()."""
        config = SDKExecutorConfig(enabled=True, allowlist={"test"})
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)
        record = result.to_record()

        # Termination reason should be string value, not enum
        assert "termination_reason" in record
        assert record["termination_reason"] == "single_iteration"

    @pytest.mark.asyncio
    async def test_fallback_termination_reason_in_record(self):
        """Fallback results have termination_reason in record."""
        config = SDKExecutorConfig(enabled=False, allowlist=set())
        client = MockSDKClient()
        selector = MockSelector(MockSDKSelection("test-agent", 0.9))

        executor = SDKExecutor(client=client, selector=selector, config=config)
        context = MockContext()

        result = await executor.execute(context)
        record = result.to_record()

        assert "termination_reason" in record
        assert record["termination_reason"] == "fallback"


# =============================================================================
# Additional Contract Tests
# =============================================================================


class TestSDKExecutionResultContract:
    """Tests for SDKExecutionResult data contract."""

    def test_to_record_includes_all_fields(self):
        """to_record() includes all required fields."""
        result = SDKExecutionResult(
            success=True,
            output={"data": "test"},
            should_fallback=False,
            routing_decision="sdk_executed",
            agent_used="test-agent",
            confidence=0.85,
            evidence={"tool_count": 3},
            termination_reason=TerminationReason.THRESHOLD_MET,
            iteration_count=2,
        )

        record = result.to_record()

        # Verify all fields present
        assert record["success"] is True
        assert record["result"] == {"data": "test"}
        assert record["agent_used"] == "test-agent"
        assert record["confidence"] == 0.85
        assert record["evidence"] == {"tool_count": 3}
        assert record["routing_decision"] == "sdk_executed"
        assert record["iteration_count"] == 2
        assert record["termination_reason"] == "threshold_met"

    def test_to_record_includes_errors_on_failure(self):
        """to_record() includes errors dict on failure."""
        result = SDKExecutionResult(
            success=False,
            output={},
            should_fallback=True,
            routing_decision="sdk_exception",
            error_type="RuntimeError",
            fallback_reason="Connection failed",
            termination_reason=TerminationReason.EXECUTION_ERROR,
        )

        record = result.to_record()

        assert "errors" in record
        assert record["errors"]["type"] == "RuntimeError"
        assert record["errors"]["reason"] == "Connection failed"

    def test_to_record_no_errors_on_success(self):
        """to_record() excludes errors dict on success."""
        result = SDKExecutionResult(
            success=True,
            output={},
            should_fallback=False,
            routing_decision="sdk_executed",
            termination_reason=TerminationReason.SINGLE_ITERATION,
        )

        record = result.to_record()

        assert "errors" not in record


class TestTerminationReasonEnum:
    """Tests for TerminationReason enum."""

    def test_all_reasons_have_string_values(self):
        """All termination reasons have string values."""
        for reason in list(TerminationReason):
            assert isinstance(reason.value, str)
            assert len(reason.value) > 0

    def test_reasons_are_serializable(self):
        """Termination reasons can be used in JSON-like structures."""
        import json

        for reason in list(TerminationReason):
            # Should not raise
            json.dumps({"reason": reason.value})

    def test_reasons_are_comparable_to_strings(self):
        """Termination reasons can be compared to strings."""
        assert TerminationReason.THRESHOLD_MET == "threshold_met"
        assert TerminationReason.MAX_ITERATIONS == "max_iterations"
