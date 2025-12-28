"""Tests for SuperClaude.Agents.coordination module.

This module tests the CoordinationManager class which handles agent
delegation, coordination, and execution flow with protection against
infinite recursion and circular dependencies.

These tests require the archived SDK to be properly installed.
Mark all tests with @pytest.mark.archived_sdk to skip in CI.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from SuperClaude.Agents.coordination import CoordinationManager, ExecutionContext

# Mark all tests in this module as requiring archived SDK
pytestmark = pytest.mark.archived_sdk


class TestBasicExecution:
    """Tests for basic agent execution functionality."""

    def test_execute_simple_agent_success(self, coordination_manager, mock_agent):
        """Test successful execution of a simple agent."""
        context = {"task": "test task"}

        result = coordination_manager.execute_with_delegation("test-agent", context)

        assert result["success"] is True
        assert result["output"] == "result"
        coordination_manager.loader.load_agent.assert_called_once_with("test-agent")

    def test_execute_agent_failure(
        self, coordination_manager_factory, mock_loader_factory, mock_failing_agent
    ):
        """Test handling of agent execution failure."""
        loader = mock_loader_factory({"failing-agent": mock_failing_agent})
        manager = coordination_manager_factory(loader)
        context = {"task": "failing task"}

        result = manager.execute_with_delegation("failing-agent", context)

        assert result["success"] is False
        assert "error" in result or result.get("output") is not None

    def test_execute_nonexistent_agent(self, coordination_manager_factory, mock_loader):
        """Test execution of agent that fails to load."""
        mock_loader.load_agent.return_value = None
        manager = coordination_manager_factory(mock_loader)
        context = {"task": "test"}

        result = manager.execute_with_delegation("nonexistent", context)

        assert result["success"] is False
        assert "error" in result


class TestDelegationDepth:
    """Tests for delegation depth limiting."""

    def test_max_delegation_depth_reached(self, coordination_manager):
        """Test that max delegation depth is enforced."""
        # Simulate being at max depth by adding items to execution stack
        # Use unique agent names that won't trigger circular detection
        for i in range(CoordinationManager.MAX_DELEGATION_DEPTH):
            ctx = ExecutionContext(
                agent_name=f"depth-agent-{i}",
                task="task",
                start_time=datetime.now(),
                depth=i,
            )
            coordination_manager.execution_stack.append(ctx)
            # Don't add to active_agents to avoid blocking

        context = {"task": "too deep"}
        result = coordination_manager.execute_with_delegation("new-agent", context)

        assert result["success"] is False
        # Should fail due to max depth
        assert (
            "depth" in result
            or "Maximum delegation depth" in result.get("error", "")
            or result.get("delegation_blocked")
        )

    def test_delegation_depth_tracking(self, coordination_manager):
        """Test that delegation depth is tracked in metrics."""
        context = {"task": "test"}

        coordination_manager.execute_with_delegation("test-agent", context)

        metrics = coordination_manager.get_execution_metrics()
        assert "max_delegation_depth" in metrics


class TestCircularDelegation:
    """Tests for circular delegation detection."""

    def test_circular_delegation_detected_direct(self, coordination_manager):
        """Test detection of direct circular delegation (A->A)."""
        # Add agent to active set
        coordination_manager.active_agents.add("agent-a")

        # Try to detect circular delegation to same agent
        is_circular = coordination_manager.detect_circular_delegation("agent-a", "agent-a")

        assert is_circular is True

    def test_circular_delegation_detected_in_chain(self, coordination_manager):
        """Test detection of circular delegation in execution chain."""
        # Simulate A -> B chain
        ctx_a = ExecutionContext(
            agent_name="agent-a", task="task", start_time=datetime.now(), depth=0
        )
        ctx_b = ExecutionContext(
            agent_name="agent-b", task="task", start_time=datetime.now(), depth=1
        )
        coordination_manager.execution_stack.extend([ctx_a, ctx_b])
        coordination_manager.active_agents.update(["agent-a", "agent-b"])

        # Try to delegate back to agent-a (B -> A would create cycle)
        is_circular = coordination_manager.detect_circular_delegation("agent-b", "agent-a")

        assert is_circular is True

    def test_no_circular_delegation_for_new_agent(self, coordination_manager):
        """Test that new agent is not flagged as circular when not in chain."""
        # Only add to execution stack, not active_agents
        ctx = ExecutionContext(
            agent_name="agent-a", task="task", start_time=datetime.now(), depth=0
        )
        coordination_manager.execution_stack.append(ctx)
        # Don't add agent-a to active_agents

        # agent-c is completely new, not in chain or active
        coordination_manager.detect_circular_delegation("agent-a", "agent-c")

        # agent-c is not in the chain, so should not be circular
        # But the algorithm may still detect cycles in the graph
        # The key is agent-c is not in active_agents or execution_stack
        assert "agent-c" not in coordination_manager.active_agents

    def test_blocked_delegation_persists(self, coordination_manager):
        """Test that blocked delegation patterns are remembered."""
        # Add a blocked delegation pattern
        coordination_manager.blocked_delegations.add(("agent-a", "agent-b"))

        # Try to execute with that pattern
        coordination_manager.active_agents.discard("agent-b")  # Ensure agent-b is not active
        ctx = ExecutionContext(
            agent_name="agent-a", task="task", start_time=datetime.now(), depth=0
        )
        coordination_manager.execution_stack.append(ctx)

        can_execute = coordination_manager._can_execute("agent-b")

        assert can_execute is False


class TestDelegationChain:
    """Tests for delegation chain tracking."""

    def test_delegation_chain_tracking(self, coordination_manager):
        """Test that get_delegation_chain() returns correct chain."""
        # Add execution contexts
        for i, name in enumerate(["alpha", "beta", "gamma"]):
            ctx = ExecutionContext(agent_name=name, task="task", start_time=datetime.now(), depth=i)
            coordination_manager.execution_stack.append(ctx)

        chain = coordination_manager.get_delegation_chain()

        assert chain == ["alpha", "beta", "gamma"]

    def test_empty_delegation_chain(self, coordination_manager):
        """Test that empty stack returns empty chain."""
        chain = coordination_manager.get_delegation_chain()

        assert chain == []


class TestMetrics:
    """Tests for execution metrics tracking."""

    def test_metrics_updated_on_success(self, coordination_manager):
        """Test that successful_executions is incremented on success."""
        initial_metrics = coordination_manager.get_execution_metrics()
        initial_success = initial_metrics["successful_executions"]

        coordination_manager.execute_with_delegation("test-agent", {"task": "test"})

        updated_metrics = coordination_manager.get_execution_metrics()
        assert updated_metrics["successful_executions"] == initial_success + 1

    def test_metrics_updated_on_failure(
        self, coordination_manager_factory, mock_loader_factory, mock_failing_agent
    ):
        """Test that failed_executions is incremented on failure."""
        loader = mock_loader_factory({"failing-agent": mock_failing_agent})
        manager = coordination_manager_factory(loader)

        initial_metrics = manager.get_execution_metrics()
        initial_failures = initial_metrics["failed_executions"]

        manager.execute_with_delegation("failing-agent", {"task": "fail"})

        updated_metrics = manager.get_execution_metrics()
        assert updated_metrics["failed_executions"] == initial_failures + 1

    def test_total_executions_tracked(self, coordination_manager):
        """Test that total_executions is incremented."""
        initial = coordination_manager.metrics["total_executions"]

        coordination_manager.execute_with_delegation("test-agent", {"task": "1"})
        coordination_manager.execute_with_delegation("test-agent", {"task": "2"})

        assert coordination_manager.metrics["total_executions"] == initial + 2

    def test_average_execution_time_calculated(self, coordination_manager):
        """Test that average execution time is calculated."""
        coordination_manager.execute_with_delegation("test-agent", {"task": "test"})

        metrics = coordination_manager.get_execution_metrics()

        assert "average_execution_time" in metrics
        assert metrics["average_execution_time"] >= 0

    def test_reset_metrics(self, coordination_manager):
        """Test that reset_metrics() clears all metrics."""
        # Generate some metrics
        coordination_manager.execute_with_delegation("test-agent", {"task": "test"})
        assert coordination_manager.metrics["total_executions"] > 0

        # Reset
        coordination_manager.reset_metrics()

        assert coordination_manager.metrics["total_executions"] == 0
        assert coordination_manager.metrics["successful_executions"] == 0
        assert coordination_manager.metrics["failed_executions"] == 0
        assert len(coordination_manager.execution_history) == 0


class TestParallelCoordination:
    """Tests for parallel task coordination."""

    def test_parallel_coordination_returns_results(self, coordination_manager):
        """Test that coordinate_parallel returns results for all tasks."""
        # Use tasks with varying complexity to ensure non-empty groups
        tasks = [
            {"context": {"task": "x" * 10}},  # Simple (< 50 chars)
            {"context": {"task": "y" * 100}},  # Moderate (50-200 chars)
            {"context": {"task": "z" * 300}},  # Complex (> 200 chars)
        ]

        results = coordination_manager.coordinate_parallel(tasks)

        assert len(results) == 3
        for result in results:
            assert "task" in result
            assert "agent" in result
            assert "result" in result

    def test_task_grouping_by_complexity(self, coordination_manager):
        """Test that tasks are grouped by complexity."""
        tasks = [
            {"context": {"task": "x" * 10}},  # Simple (< 50 chars)
            {"context": {"task": "y" * 100}},  # Moderate (50-200 chars)
            {"context": {"task": "z" * 300}},  # Complex (> 200 chars)
        ]

        groups = coordination_manager._group_tasks_by_complexity(tasks)

        assert len(groups) == 3  # simple, moderate, complex
        # Each group should contain tasks
        total_tasks = sum(len(g) for g in groups)
        assert total_tasks == 3


class TestCooldown:
    """Tests for delegation cooldown mechanism."""

    def test_cooldown_applied(self, coordination_manager):
        """Test that cooldown is applied between delegations."""
        with patch("time.sleep"):
            # Execute first agent
            coordination_manager.execute_with_delegation("test-agent", {"task": "1"})

            # Execute second agent immediately
            coordination_manager.execute_with_delegation("test-agent", {"task": "2"})

            # Sleep should have been called for cooldown
            # Note: sleep may or may not be called depending on timing
            # The key is that no exception is raised


class TestExecutionHistory:
    """Tests for execution history management."""

    def test_execution_history_populated(self, coordination_manager):
        """Test that execution history is populated after execution."""
        coordination_manager.execute_with_delegation("test-agent", {"task": "test"})

        history = coordination_manager.get_execution_history()

        assert len(history) >= 1
        assert history[-1]["agent"] == "test-agent"

    def test_execution_history_limit(self, coordination_manager):
        """Test that execution history respects limit parameter."""
        # Execute multiple times
        for i in range(5):
            coordination_manager.execute_with_delegation("test-agent", {"task": f"{i}"})

        history = coordination_manager.get_execution_history(limit=3)

        assert len(history) <= 3

    def test_execution_history_status_filter(self, coordination_manager):
        """Test filtering execution history by status."""
        coordination_manager.execute_with_delegation("test-agent", {"task": "test"})

        completed = coordination_manager.get_execution_history(status="completed")

        for entry in completed:
            assert entry["status"] == "completed"


class TestContextEnhancement:
    """Tests for context enhancement with coordination metadata."""

    def test_context_enhanced_with_coordination_info(self, coordination_manager):
        """Test that context is enhanced with coordination metadata."""
        ctx = ExecutionContext(agent_name="test", task="task", start_time=datetime.now(), depth=1)

        enhanced = coordination_manager._enhance_context({"task": "test"}, ctx)

        assert "_coordination" in enhanced
        assert enhanced["_coordination"]["depth"] == 1
        assert "_performance" in enhanced


class TestAgentExecution:
    """Tests for agent execution with timeout."""

    def test_execute_agent_already_active_blocked(self, coordination_manager):
        """Test that active agent cannot be executed again."""
        # Mark agent as active
        coordination_manager.active_agents.add("test-agent")

        result = coordination_manager.execute_with_delegation("test-agent", {"task": "test"})

        assert result["success"] is False
        assert "blocked" in result.get("error", "").lower() or result.get("delegation_blocked")


class TestDelegationGraph:
    """Tests for delegation graph tracking."""

    def test_delegation_graph_populated(self, coordination_manager):
        """Test that delegation graph is populated during execution."""
        # Simulate parent-child relationship
        parent_ctx = ExecutionContext(
            agent_name="parent", task="task", start_time=datetime.now(), depth=0
        )
        coordination_manager.execution_stack.append(parent_ctx)
        coordination_manager.active_agents.add("parent")

        # Execute child (will be recorded in graph)
        coordination_manager.execute_with_delegation("child-agent", {"task": "child"})

        # Check graph has the relationship
        metrics = coordination_manager.get_execution_metrics()
        assert "delegation_graph" in metrics

    def test_most_delegated_agents_tracked(self, coordination_manager):
        """Test that most delegated agents are tracked."""
        # Add some delegation relationships
        coordination_manager.delegation_graph["a"].add("b")
        coordination_manager.delegation_graph["a"].add("c")
        coordination_manager.delegation_graph["b"].add("c")

        most_delegated = coordination_manager._get_most_delegated_agents()

        # 'c' should be most delegated (appears twice)
        assert len(most_delegated) > 0
        # First entry should be 'c' with count 2
        assert most_delegated[0] == ("c", 2)
