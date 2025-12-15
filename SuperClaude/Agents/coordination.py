"""
Agent Coordination System for SuperClaude Framework

Manages agent delegation, coordination, and execution flow with
protection against infinite recursion and circular dependencies.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .loader import AgentLoader
from .registry import AgentRegistry
from .selector import AgentSelector


@dataclass
class ExecutionContext:
    """Context for agent execution tracking."""

    agent_name: str
    task: str
    start_time: datetime
    depth: int = 0
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CoordinationManager:
    """
    Manages agent coordination, delegation, and execution flow.

    Features:
    - Delegation depth protection
    - Circular dependency detection
    - Execution history tracking
    - Performance monitoring
    - Resource management
    """

    # Configuration constants
    MAX_DELEGATION_DEPTH = 5
    MAX_PARALLEL_AGENTS = 3
    EXECUTION_TIMEOUT = 300  # 5 minutes per agent
    DELEGATION_COOLDOWN = 1.0  # Seconds between delegations

    def __init__(
        self, registry: AgentRegistry, selector: AgentSelector, loader: AgentLoader
    ):
        """
        Initialize the coordination manager.

        Args:
            registry: Agent registry
            selector: Agent selector
            loader: Agent loader
        """
        self.registry = registry
        self.selector = selector
        self.loader = loader
        self.logger = logging.getLogger(__name__)

        # Execution tracking
        self.execution_stack: List[ExecutionContext] = []
        self.execution_history: List[ExecutionContext] = []
        self.active_agents: Set[str] = set()
        self.delegation_graph: Dict[str, Set[str]] = defaultdict(set)

        # Performance metrics
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_delegation_time": 0.0,
            "average_execution_time": 0.0,
            "max_delegation_depth": 0,
            "delegation_chains": [],
        }

        # Protection mechanisms
        self.blocked_delegations: Set[Tuple[str, str]] = set()
        self.last_delegation_time = datetime.now()

    def execute_with_delegation(
        self,
        agent_name: str,
        context: Dict[str, Any],
        allow_delegation: bool = True,
        max_depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute an agent with delegation support.

        Args:
            agent_name: Name of agent to execute
            context: Execution context
            allow_delegation: Whether to allow sub-delegations
            max_depth: Override max delegation depth

        Returns:
            Execution result
        """
        # Check if agent can be executed
        if not self._can_execute(agent_name):
            return {
                "success": False,
                "error": f"Agent {agent_name} is blocked or already active",
                "delegation_blocked": True,
            }

        # Create execution context
        current_depth = self._get_current_depth()
        exec_context = ExecutionContext(
            agent_name=agent_name,
            task=context.get("task", ""),
            start_time=datetime.now(),
            depth=current_depth,
            parent=self._get_current_agent(),
        )

        # Check delegation depth
        max_allowed = max_depth or self.MAX_DELEGATION_DEPTH
        if current_depth >= max_allowed:
            self.logger.warning(f"Max delegation depth {max_allowed} reached")
            return {
                "success": False,
                "error": f"Maximum delegation depth ({max_allowed}) reached",
                "depth": current_depth,
            }

        # Add to execution stack
        self.execution_stack.append(exec_context)
        self.active_agents.add(agent_name)

        try:
            # Update metrics
            self.metrics["total_executions"] += 1
            self.metrics["max_delegation_depth"] = max(
                self.metrics["max_delegation_depth"], current_depth
            )

            # Apply delegation cooldown
            self._apply_delegation_cooldown()

            # Load and execute agent
            agent = self.loader.load_agent(agent_name)
            if not agent:
                raise ValueError(f"Failed to load agent: {agent_name}")

            # Inject coordination context
            enhanced_context = self._enhance_context(context, exec_context)

            # Execute with timeout protection
            start_time = time.time()
            result = self._execute_with_timeout(agent, enhanced_context)
            execution_time = time.time() - start_time

            # Update execution context
            exec_context.status = "completed" if result.get("success") else "failed"
            exec_context.result = result
            exec_context.metadata["execution_time"] = execution_time

            # Handle sub-delegations if requested
            if allow_delegation and result.get("delegate_to"):
                result = self._handle_delegation(result, enhanced_context)

            # Update metrics
            if result.get("success"):
                self.metrics["successful_executions"] += 1
            else:
                self.metrics["failed_executions"] += 1

            self.metrics["total_delegation_time"] += execution_time
            self.metrics["average_execution_time"] = (
                self.metrics["total_delegation_time"] / self.metrics["total_executions"]
            )

            return result

        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            exec_context.status = "failed"
            self.metrics["failed_executions"] += 1

            return {
                "success": False,
                "error": str(e),
                "agent": agent_name,
                "depth": current_depth,
            }

        finally:
            # Clean up execution stack
            self.execution_stack.pop()
            self.active_agents.discard(agent_name)

            # Archive execution context
            self.execution_history.append(exec_context)

            # Record delegation chain
            if exec_context.parent:
                self.delegation_graph[exec_context.parent].add(agent_name)
                self._record_delegation_chain()

    def coordinate_parallel(
        self, tasks: List[Dict[str, Any]], strategy: str = "best_match"
    ) -> List[Dict[str, Any]]:
        """
        Coordinate parallel execution of multiple tasks.

        Args:
            tasks: List of tasks with contexts
            strategy: Coordination strategy

        Returns:
            List of execution results
        """
        results = []

        # Group tasks by estimated execution time
        task_groups = self._group_tasks_by_complexity(tasks)

        for group in task_groups:
            # Limit parallel execution
            batch_size = min(len(group), self.MAX_PARALLEL_AGENTS)

            for i in range(0, len(group), batch_size):
                batch = group[i : i + batch_size]

                # Execute batch in parallel (simplified - would use threading/async in production)
                batch_results = []
                for task_info in batch:
                    # Select best agent for task
                    if strategy == "best_match":
                        agent_name = self._select_best_agent(task_info["context"])
                    else:
                        agent_name = task_info.get("agent", "general-purpose")

                    # Execute with delegation
                    result = self.execute_with_delegation(
                        agent_name,
                        task_info["context"],
                        allow_delegation=task_info.get("allow_delegation", True),
                    )

                    batch_results.append(
                        {"task": task_info, "agent": agent_name, "result": result}
                    )

                results.extend(batch_results)

        return results

    def get_delegation_chain(self) -> List[str]:
        """
        Get current delegation chain.

        Returns:
            List of agent names in delegation order
        """
        return [ctx.agent_name for ctx in self.execution_stack]

    def get_execution_metrics(self) -> Dict[str, Any]:
        """
        Get execution metrics.

        Returns:
            Dictionary of metrics
        """
        metrics = self.metrics.copy()

        # Add current state
        metrics["active_agents"] = list(self.active_agents)
        metrics["current_depth"] = self._get_current_depth()
        metrics["delegation_chain"] = self.get_delegation_chain()

        # Add delegation graph summary
        metrics["delegation_graph"] = {
            "nodes": len(self.delegation_graph),
            "edges": sum(len(targets) for targets in self.delegation_graph.values()),
            "most_delegated": self._get_most_delegated_agents(),
        }

        return metrics

    def detect_circular_delegation(self, from_agent: str, to_agent: str) -> bool:
        """
        Detect circular delegation.

        Args:
            from_agent: Source agent
            to_agent: Target agent

        Returns:
            True if circular delegation detected
        """
        # Check direct cycle
        if to_agent in self.active_agents:
            return True

        # Check if target is already in delegation chain
        chain = self.get_delegation_chain()
        if to_agent in chain:
            return True

        # Check delegation graph for cycles
        visited = set()

        def has_cycle(agent: str, path: Set[str]) -> bool:
            if agent in path:
                return True
            if agent in visited:
                return False

            visited.add(agent)
            path.add(agent)

            for target in self.delegation_graph.get(agent, []):
                if has_cycle(target, path.copy()):
                    return True

            return False

        return has_cycle(from_agent, {from_agent})

    def _can_execute(self, agent_name: str) -> bool:
        """Check if agent can be executed."""
        # Check if agent is already active
        if agent_name in self.active_agents:
            self.logger.warning(f"Agent {agent_name} is already active")
            return False

        # Check if delegation is blocked
        current_agent = self._get_current_agent()
        if current_agent and (current_agent, agent_name) in self.blocked_delegations:
            self.logger.warning(
                f"Delegation from {current_agent} to {agent_name} is blocked"
            )
            return False

        # Check for circular delegation
        if current_agent and self.detect_circular_delegation(current_agent, agent_name):
            self.logger.warning(
                f"Circular delegation detected: {current_agent} -> {agent_name}"
            )
            # Block this delegation pattern
            self.blocked_delegations.add((current_agent, agent_name))
            return False

        return True

    def _get_current_depth(self) -> int:
        """Get current delegation depth."""
        return len(self.execution_stack)

    def _get_current_agent(self) -> Optional[str]:
        """Get current executing agent."""
        return self.execution_stack[-1].agent_name if self.execution_stack else None

    def _enhance_context(
        self, context: Dict[str, Any], exec_context: ExecutionContext
    ) -> Dict[str, Any]:
        """
        Enhance context with coordination information.

        Args:
            context: Original context
            exec_context: Execution context

        Returns:
            Enhanced context
        """
        enhanced = context.copy()

        # Add coordination metadata
        enhanced["_coordination"] = {
            "depth": exec_context.depth,
            "parent": exec_context.parent,
            "chain": self.get_delegation_chain(),
            "max_depth": self.MAX_DELEGATION_DEPTH,
            "can_delegate": exec_context.depth < self.MAX_DELEGATION_DEPTH - 1,
        }

        # Add performance hints
        enhanced["_performance"] = {
            "timeout": self.EXECUTION_TIMEOUT,
            "start_time": exec_context.start_time.isoformat(),
            "parallel_limit": self.MAX_PARALLEL_AGENTS,
        }

        return enhanced

    def _execute_with_timeout(
        self, agent: Any, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agent with timeout protection.

        Args:
            agent: Agent instance
            context: Execution context

        Returns:
            Execution result
        """
        # Simplified timeout - in production would use threading/asyncio
        try:
            start = time.time()
            result = agent.execute(context)

            if time.time() - start > self.EXECUTION_TIMEOUT:
                self.logger.warning(f"Agent exceeded timeout: {agent.name}")
                result["timeout_warning"] = True

            return result

        except Exception as e:
            self.logger.error(f"Agent execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": getattr(agent, "name", "unknown"),
            }

    def _handle_delegation(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle sub-delegation request.

        Args:
            result: Current execution result
            context: Execution context

        Returns:
            Enhanced result with delegation
        """
        delegate_to = result.get("delegate_to")
        if not delegate_to:
            return result

        # Check if delegation is allowed
        if not context["_coordination"]["can_delegate"]:
            result["delegation_blocked"] = True
            result["delegation_reason"] = "Max depth reached"
            return result

        # Prepare delegation context
        delegation_context = context.copy()
        delegation_context["task"] = result.get(
            "delegation_task", context.get("task", "")
        )

        # Execute delegation
        delegation_result = self.execute_with_delegation(
            delegate_to, delegation_context, allow_delegation=True
        )

        # Merge results
        result["delegation_result"] = delegation_result
        if delegation_result.get("success"):
            result["success"] = True
            result["output"] = delegation_result.get("output", "")

        return result

    def _apply_delegation_cooldown(self):
        """Apply cooldown between delegations."""
        elapsed = (datetime.now() - self.last_delegation_time).total_seconds()
        if elapsed < self.DELEGATION_COOLDOWN:
            time.sleep(self.DELEGATION_COOLDOWN - elapsed)
        self.last_delegation_time = datetime.now()

    def _select_best_agent(self, context: Dict[str, Any]) -> str:
        """Select best agent for context."""
        scores = self.selector.select_agent(context)
        if scores:
            return scores[0][0]  # Return highest scoring agent
        return "general-purpose"  # Fallback

    def _group_tasks_by_complexity(
        self, tasks: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group tasks by estimated complexity."""
        # Simple grouping - could be enhanced with ML
        simple = []
        moderate = []
        complex = []

        for task in tasks:
            context = task.get("context", {})
            task_str = str(context.get("task", ""))

            # Estimate complexity
            if len(task_str) < 50:
                simple.append(task)
            elif len(task_str) < 200:
                moderate.append(task)
            else:
                complex.append(task)

        return [simple, moderate, complex]

    def _get_most_delegated_agents(self) -> List[Tuple[str, int]]:
        """Get most frequently delegated-to agents."""
        delegation_counts = defaultdict(int)

        for targets in self.delegation_graph.values():
            for target in targets:
                delegation_counts[target] += 1

        return sorted(delegation_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    def _record_delegation_chain(self):
        """Record current delegation chain for analysis."""
        chain = self.get_delegation_chain()
        if len(chain) > 1:
            self.metrics["delegation_chains"].append(
                {
                    "chain": chain,
                    "depth": len(chain),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # Keep only last 100 chains
            if len(self.metrics["delegation_chains"]) > 100:
                self.metrics["delegation_chains"] = self.metrics["delegation_chains"][
                    -100:
                ]

    def reset_metrics(self):
        """Reset execution metrics."""
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_delegation_time": 0.0,
            "average_execution_time": 0.0,
            "max_delegation_depth": 0,
            "delegation_chains": [],
        }
        self.execution_history.clear()
        self.delegation_graph.clear()
        self.blocked_delegations.clear()

    def get_execution_history(
        self, limit: int = 10, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get execution history.

        Args:
            limit: Maximum number of entries
            status: Filter by status

        Returns:
            List of execution records
        """
        history = self.execution_history[-limit:]

        if status:
            history = [h for h in history if h.status == status]

        return [
            {
                "agent": h.agent_name,
                "task": h.task[:100],  # Truncate long tasks
                "depth": h.depth,
                "parent": h.parent,
                "status": h.status,
                "start_time": h.start_time.isoformat(),
                "execution_time": h.metadata.get("execution_time", 0),
                "children": h.children,
            }
            for h in history
        ]
