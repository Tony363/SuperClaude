"""
Agent Coordination Manager for SuperClaude.

Orchestrates multi-agent workflows with delegation, parallelization, and conflict resolution.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import networkx as nx
from collections import defaultdict

logger = logging.getLogger(__name__)


class CoordinationStrategy(Enum):
    """Agent coordination strategies."""

    SEQUENTIAL = "sequential"      # One agent at a time
    PARALLEL = "parallel"          # All agents simultaneously
    PIPELINE = "pipeline"          # Output of one feeds next
    HIERARCHICAL = "hierarchical"  # Parent-child delegation
    CONSENSUS = "consensus"        # Multiple agents vote
    COMPETITIVE = "competitive"    # Best solution wins


class AgentRole(Enum):
    """Roles agents can play in coordination."""

    LEADER = "leader"           # Orchestrates others
    WORKER = "worker"           # Executes tasks
    VALIDATOR = "validator"     # Validates outputs
    REVIEWER = "reviewer"       # Reviews quality
    SPECIALIST = "specialist"   # Domain expert
    GENERALIST = "generalist"   # Multi-purpose


@dataclass
class AgentTask:
    """Task assigned to an agent."""

    id: str
    agent_id: str
    task_type: str
    priority: int
    input_data: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from agent execution."""

    task_id: str
    agent_id: str
    status: str  # success, failure, timeout
    output: Any
    duration_ms: float
    confidence: float = 0.0
    artifacts: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class CoordinationPlan:
    """Execution plan for multi-agent coordination."""

    id: str
    strategy: CoordinationStrategy
    tasks: List[AgentTask]
    dependencies: Dict[str, List[str]]  # task_id -> [dependency_ids]
    phases: List[List[str]]  # Grouped task IDs by execution phase
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentCoordinator:
    """
    Coordinates multi-agent workflows.

    Features:
    - Intelligent task delegation
    - Parallel execution management
    - Dependency resolution
    - Conflict resolution
    - Result aggregation
    - Circular dependency detection
    """

    def __init__(self, max_delegation_depth: int = 5):
        """
        Initialize coordinator.

        Args:
            max_delegation_depth: Maximum delegation chain depth
        """
        self.max_delegation_depth = max_delegation_depth
        self.agent_registry: Dict[str, Any] = {}
        self.active_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentResult] = {}
        self.delegation_graph = nx.DiGraph()
        self.execution_history: List[Dict[str, Any]] = []
        # Expose available strategies for simple introspection/APIs
        self.strategies = [s.value for s in CoordinationStrategy]

    def register_agent(self, agent_id: str, agent: Any, role: AgentRole = AgentRole.WORKER):
        """
        Register an agent.

        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
            role: Agent's role in coordination
        """
        self.agent_registry[agent_id] = {
            'agent': agent,
            'role': role,
            'busy': False,
            'task_count': 0
        }
        logger.debug(f"Registered agent: {agent_id} with role {role.value}")

    async def execute_plan(self, plan: CoordinationPlan) -> Dict[str, AgentResult]:
        """
        Execute a coordination plan.

        Args:
            plan: Coordination plan to execute

        Returns:
            Dictionary of task_id -> result
        """
        logger.info(f"Executing plan {plan.id} with strategy {plan.strategy.value}")

        # Build dependency graph
        self._build_dependency_graph(plan)

        # Check for circular dependencies
        if self._has_circular_dependencies():
            raise ValueError("Circular dependencies detected in plan")

        # Execute based on strategy
        if plan.strategy == CoordinationStrategy.SEQUENTIAL:
            return await self._execute_sequential(plan)
        elif plan.strategy == CoordinationStrategy.PARALLEL:
            return await self._execute_parallel(plan)
        elif plan.strategy == CoordinationStrategy.PIPELINE:
            return await self._execute_pipeline(plan)
        elif plan.strategy == CoordinationStrategy.HIERARCHICAL:
            return await self._execute_hierarchical(plan)
        elif plan.strategy == CoordinationStrategy.CONSENSUS:
            return await self._execute_consensus(plan)
        elif plan.strategy == CoordinationStrategy.COMPETITIVE:
            return await self._execute_competitive(plan)
        else:
            raise ValueError(f"Unknown strategy: {plan.strategy}")

    async def delegate_task(
        self,
        task: str,
        from_agent: str,
        to_agents: List[str],
        strategy: CoordinationStrategy = CoordinationStrategy.PARALLEL
    ) -> List[AgentResult]:
        """
        Delegate task from one agent to others.

        Args:
            task: Task description
            from_agent: Delegating agent ID
            to_agents: Target agent IDs
            strategy: Coordination strategy

        Returns:
            Results from delegated agents
        """
        # Check delegation depth
        depth = self._get_delegation_depth(from_agent)
        if depth >= self.max_delegation_depth:
            raise ValueError(f"Max delegation depth {self.max_delegation_depth} exceeded")

        # Create tasks for each agent
        tasks = []
        for agent_id in to_agents:
            agent_task = AgentTask(
                id=f"{from_agent}_to_{agent_id}_{datetime.now().timestamp()}",
                agent_id=agent_id,
                task_type="delegated",
                priority=1,
                input_data={'task': task, 'from_agent': from_agent}
            )
            tasks.append(agent_task)

        # Create coordination plan
        plan = CoordinationPlan(
            id=f"delegation_{datetime.now().timestamp()}",
            strategy=strategy,
            tasks=tasks,
            dependencies={},
            phases=[],
            metadata={'delegator': from_agent}
        )

        # Execute and return results
        results = await self.execute_plan(plan)
        return list(results.values())

    async def execute_task(self, task: AgentTask) -> AgentResult:
        """
        Execute a single task with an agent.

        Args:
            task: Task to execute

        Returns:
            Execution result
        """
        if task.agent_id not in self.agent_registry:
            return AgentResult(
                task_id=task.id,
                agent_id=task.agent_id,
                status="failure",
                output=None,
                duration_ms=0,
                errors=[f"Agent {task.agent_id} not found"]
            )

        agent_info = self.agent_registry[task.agent_id]
        agent = agent_info['agent']

        # Mark agent as busy
        agent_info['busy'] = True
        self.active_tasks[task.id] = task

        start_time = datetime.now()
        result = AgentResult(
            task_id=task.id,
            agent_id=task.agent_id,
            status="running",
            output=None,
            duration_ms=0
        )

        try:
            # Execute with timeout
            output = await asyncio.wait_for(
                self._call_agent(agent, task),
                timeout=task.timeout_seconds
            )

            result.status = "success"
            result.output = output
            result.confidence = self._calculate_confidence(output)

            logger.info(f"Task {task.id} completed by {task.agent_id}")

        except asyncio.TimeoutError:
            result.status = "timeout"
            result.errors.append(f"Task timed out after {task.timeout_seconds}s")
            logger.warning(f"Task {task.id} timed out")

        except Exception as e:
            result.status = "failure"
            result.errors.append(str(e))
            logger.error(f"Task {task.id} failed: {e}")

        finally:
            # Calculate duration
            end_time = datetime.now()
            result.duration_ms = (end_time - start_time).total_seconds() * 1000

            # Mark agent as available
            agent_info['busy'] = False
            agent_info['task_count'] += 1

            # Store result
            del self.active_tasks[task.id]
            self.completed_tasks[task.id] = result

        return result

    def create_plan(
        self,
        tasks: List[Dict[str, Any]],
        strategy: CoordinationStrategy = CoordinationStrategy.PARALLEL
    ) -> CoordinationPlan:
        """
        Create a coordination plan.

        Args:
            tasks: List of task definitions
            strategy: Coordination strategy

        Returns:
            Coordination plan
        """
        agent_tasks = []
        dependencies = {}

        for task_def in tasks:
            agent_task = AgentTask(
                id=task_def.get('id', f"task_{len(agent_tasks)}"),
                agent_id=task_def['agent_id'],
                task_type=task_def.get('type', 'standard'),
                priority=task_def.get('priority', 5),
                input_data=task_def.get('input', {}),
                dependencies=task_def.get('dependencies', [])
            )
            agent_tasks.append(agent_task)

            if agent_task.dependencies:
                dependencies[agent_task.id] = agent_task.dependencies

        # Calculate execution phases
        phases = self._calculate_phases(agent_tasks, dependencies)

        return CoordinationPlan(
            id=f"plan_{datetime.now().timestamp()}",
            strategy=strategy,
            tasks=agent_tasks,
            dependencies=dependencies,
            phases=phases
        )

    def resolve_conflicts(self, results: List[AgentResult]) -> AgentResult:
        """
        Resolve conflicts between agent results.

        Args:
            results: Conflicting results

        Returns:
            Resolved result
        """
        if not results:
            return None

        if len(results) == 1:
            return results[0]

        # Strategy 1: Highest confidence wins
        best_by_confidence = max(results, key=lambda r: r.confidence)

        # Strategy 2: Majority voting (if applicable)
        if all(isinstance(r.output, (str, int, bool)) for r in results):
            from collections import Counter
            outputs = [r.output for r in results]
            most_common = Counter(outputs).most_common(1)[0][0]

            for result in results:
                if result.output == most_common:
                    return result

        # Default to highest confidence
        return best_by_confidence

    def get_agent_workload(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current workload for all agents.

        Returns:
            Agent workload statistics
        """
        workload = {}

        for agent_id, info in self.agent_registry.items():
            workload[agent_id] = {
                'role': info['role'].value,
                'busy': info['busy'],
                'task_count': info['task_count'],
                'active_tasks': [
                    task_id for task_id, task in self.active_tasks.items()
                    if task.agent_id == agent_id
                ]
            }

        return workload

    def visualize_delegation_graph(self) -> str:
        """
        Generate visualization of delegation graph.

        Returns:
            Graph representation (DOT format)
        """
        if not self.delegation_graph.nodes():
            return "digraph { /* empty */ }"

        lines = ["digraph DelegationGraph {"]
        lines.append("  rankdir=TB;")

        # Add nodes
        for node in self.delegation_graph.nodes():
            role = self.agent_registry.get(node, {}).get('role', AgentRole.WORKER)
            color = {
                AgentRole.LEADER: "red",
                AgentRole.VALIDATOR: "blue",
                AgentRole.REVIEWER: "green",
                AgentRole.SPECIALIST: "orange",
                AgentRole.WORKER: "gray",
                AgentRole.GENERALIST: "purple"
            }.get(role, "gray")

            lines.append(f'  "{node}" [color={color}];')

        # Add edges
        for source, target in self.delegation_graph.edges():
            lines.append(f'  "{source}" -> "{target}";')

        lines.append("}")
        return "\n".join(lines)

    # Private helper methods

    async def _execute_sequential(self, plan: CoordinationPlan) -> Dict[str, AgentResult]:
        """Execute tasks sequentially."""
        results = {}

        for task in plan.tasks:
            # Wait for dependencies
            await self._wait_for_dependencies(task, results)

            # Execute task
            result = await self.execute_task(task)
            results[task.id] = result

            if result.status == "failure":
                logger.warning(f"Sequential execution stopped due to failure: {task.id}")
                break

        return results

    async def _execute_parallel(self, plan: CoordinationPlan) -> Dict[str, AgentResult]:
        """Execute tasks in parallel."""
        results = {}

        # Group tasks by phase
        for phase_tasks in plan.phases:
            # Execute all tasks in phase parallel
            phase_coroutines = []

            for task_id in phase_tasks:
                task = next(t for t in plan.tasks if t.id == task_id)
                phase_coroutines.append(self.execute_task(task))

            # Wait for all tasks in phase
            phase_results = await asyncio.gather(*phase_coroutines)

            # Store results
            for task_id, result in zip(phase_tasks, phase_results):
                results[task_id] = result

        return results

    async def _execute_pipeline(self, plan: CoordinationPlan) -> Dict[str, AgentResult]:
        """Execute tasks in pipeline (output feeds next)."""
        results = {}
        previous_output = None

        for task in plan.tasks:
            # Add previous output to input
            if previous_output is not None:
                task.input_data['previous_output'] = previous_output

            # Execute task
            result = await self.execute_task(task)
            results[task.id] = result

            # Use output for next task
            previous_output = result.output

            if result.status == "failure":
                logger.warning(f"Pipeline broken at: {task.id}")
                break

        return results

    async def _execute_hierarchical(self, plan: CoordinationPlan) -> Dict[str, AgentResult]:
        """Execute with hierarchical delegation."""
        # Identify leader tasks
        leader_tasks = [
            t for t in plan.tasks
            if self.agent_registry.get(t.agent_id, {}).get('role') == AgentRole.LEADER
        ]

        if not leader_tasks:
            # No leaders, fall back to parallel
            return await self._execute_parallel(plan)

        results = {}

        # Execute leader tasks first
        for task in leader_tasks:
            result = await self.execute_task(task)
            results[task.id] = result

            # Leader can delegate
            if result.output and isinstance(result.output, dict):
                delegations = result.output.get('delegations', [])
                for delegation in delegations:
                    sub_results = await self.delegate_task(
                        delegation['task'],
                        task.agent_id,
                        delegation['agents']
                    )
                    # Store sub-results
                    for sub_result in sub_results:
                        results[sub_result.task_id] = sub_result

        # Execute remaining tasks
        for task in plan.tasks:
            if task.id not in results:
                result = await self.execute_task(task)
                results[task.id] = result

        return results

    async def _execute_consensus(self, plan: CoordinationPlan) -> Dict[str, AgentResult]:
        """Execute with consensus building."""
        results = {}

        # Group tasks by type for consensus
        task_groups = defaultdict(list)
        for task in plan.tasks:
            task_groups[task.task_type].append(task)

        for task_type, tasks in task_groups.items():
            # Execute all tasks of same type
            group_coroutines = [self.execute_task(task) for task in tasks]
            group_results = await asyncio.gather(*group_coroutines)

            # Build consensus
            consensus = self.resolve_conflicts(group_results)

            # Store individual and consensus results
            for task, result in zip(tasks, group_results):
                results[task.id] = result

            # Add consensus as special result
            if consensus:
                consensus.task_id = f"consensus_{task_type}"
                results[consensus.task_id] = consensus

        return results

    async def _execute_competitive(self, plan: CoordinationPlan) -> Dict[str, AgentResult]:
        """Execute competitively (best solution wins)."""
        # Execute all tasks in parallel
        all_coroutines = [self.execute_task(task) for task in plan.tasks]
        all_results = await asyncio.gather(*all_coroutines)

        # Find best result
        best_result = max(all_results, key=lambda r: r.confidence if r.status == "success" else -1)

        # Return all results with best marked
        results = {task.id: result for task, result in zip(plan.tasks, all_results)}

        # Mark winner
        if best_result.status == "success":
            best_result.metadata['winner'] = True

        return results

    async def _wait_for_dependencies(
        self,
        task: AgentTask,
        results: Dict[str, AgentResult]
    ):
        """Wait for task dependencies to complete."""
        for dep_id in task.dependencies:
            while dep_id not in results:
                await asyncio.sleep(0.1)

            if results[dep_id].status == "failure":
                raise ValueError(f"Dependency {dep_id} failed")

    async def _call_agent(self, agent: Any, task: AgentTask) -> Any:
        """Call agent with task."""
        # Check for different agent interfaces
        if hasattr(agent, 'execute'):
            return await agent.execute(task.input_data)
        elif hasattr(agent, 'run'):
            return await agent.run(task.input_data)
        elif callable(agent):
            return await agent(task.input_data)
        else:
            raise ValueError(f"Agent {task.agent_id} has no callable interface")

    def _calculate_confidence(self, output: Any) -> float:
        """Calculate confidence score for output."""
        if output is None:
            return 0.0

        # Check for explicit confidence
        if isinstance(output, dict) and 'confidence' in output:
            return float(output['confidence'])

        # Default confidence based on output type
        if isinstance(output, (dict, list)) and len(output) > 0:
            return 0.8
        elif isinstance(output, str) and len(output) > 10:
            return 0.7
        else:
            return 0.5

    def _build_dependency_graph(self, plan: CoordinationPlan):
        """Build dependency graph from plan."""
        self.delegation_graph.clear()

        # Add all tasks as nodes
        for task in plan.tasks:
            self.delegation_graph.add_node(task.id, agent_id=task.agent_id)

        # Add dependencies as edges
        for task_id, deps in plan.dependencies.items():
            for dep_id in deps:
                self.delegation_graph.add_edge(dep_id, task_id)

    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies."""
        try:
            nx.topological_sort(self.delegation_graph)
            return False
        except nx.NetworkXError:
            return True

    def _get_delegation_depth(self, agent_id: str) -> int:
        """Get current delegation depth for agent."""
        if agent_id not in self.delegation_graph:
            return 0

        # Find longest path to this agent
        max_depth = 0
        for node in self.delegation_graph.nodes():
            if nx.has_path(self.delegation_graph, node, agent_id):
                path_length = len(nx.shortest_path(self.delegation_graph, node, agent_id)) - 1
                max_depth = max(max_depth, path_length)

        return max_depth

    def _calculate_phases(
        self,
        tasks: List[AgentTask],
        dependencies: Dict[str, List[str]]
    ) -> List[List[str]]:
        """Calculate execution phases based on dependencies."""
        if not dependencies:
            # No dependencies, all tasks in one phase
            return [[t.id for t in tasks]]

        # Build dependency graph
        graph = nx.DiGraph()
        for task in tasks:
            graph.add_node(task.id)

        for task_id, deps in dependencies.items():
            for dep_id in deps:
                graph.add_edge(dep_id, task_id)

        # Calculate phases using topological generations
        phases = []
        for generation in nx.topological_generations(graph):
            phases.append(list(generation))

        return phases


# Convenience functions

def create_coordinator(max_depth: int = 5) -> AgentCoordinator:
    """Create and initialize agent coordinator."""
    return AgentCoordinator(max_delegation_depth=max_depth)
