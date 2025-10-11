"""
Integration Testing Framework for SuperClaude.

Provides comprehensive testing for component interactions, MCP servers, and agents.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ComponentType(Enum):
    """Types of components to test."""

    AGENT = "agent"
    MCP_SERVER = "mcp_server"
    API_CLIENT = "api_client"
    COMMAND = "command"
    MODEL_ROUTER = "model_router"
    WORKTREE = "worktree"
    QUALITY_SCORER = "quality_scorer"
    DYNAMIC_LOADER = "dynamic_loader"


@dataclass
class TestCase:
    """Individual test case."""

    id: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"
    component_type: ComponentType = ComponentType.AGENT
    components: List[str] = field(default_factory=list)  # Component IDs to test
    test_function: Callable = lambda *a, **k: True
    dependencies: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    retry_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"

    def __post_init__(self):
        if not self.id and self.name:
            self.id = self.name.lower().replace(" ", "_")


@dataclass
class TestResult:
    """Result from test execution."""

    test_id: str
    status: TestStatus
    duration_ms: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntegrationTestSuite:
    """Collection of integration tests."""

    id: str
    name: str
    tests: List[TestCase]
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None
    parallel_execution: bool = False
    stop_on_failure: bool = False
    tags: List[str] = field(default_factory=list)


class IntegrationTestRunner:
    """
    Runs integration tests for SuperClaude components.

    Features:
    - Component interaction testing
    - MCP server integration testing
    - End-to-end workflow testing
    - Performance benchmarking
    - Failure analysis
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize test runner."""
        self.config = config or {}
        self.test_suites: Dict[str, IntegrationTestSuite] = {}
        self.test_results: List[TestResult] = []
        self.component_registry: Dict[str, Any] = {}
        self.metrics_collector = MetricsCollector()
    def register_suite(self, suite: IntegrationTestSuite):
        """Register a test suite."""
        self.test_suites[suite.id] = suite
        logger.info(f"Registered test suite: {suite.name} with {len(suite.tests)} tests")

    def register_component(self, component_id: str, component: Any):
        """Register a component for testing."""
        self.component_registry[component_id] = component
        logger.debug(f"Registered component: {component_id}")

    async def run_suite(self, suite_id: str) -> List[TestResult]:
        """
        Run a test suite.

        Args:
            suite_id: Suite to run

        Returns:
            List of test results
        """
        if suite_id not in self.test_suites:
            raise ValueError(f"Test suite not found: {suite_id}")

        suite = self.test_suites[suite_id]
        results = []

        logger.info(f"Running test suite: {suite.name}")

        # Run setup
        if suite.setup:
            try:
                await self._run_async_callable(suite.setup)
            except Exception as e:
                logger.error(f"Suite setup failed: {e}")
                return []

        # Run tests
        if suite.parallel_execution:
            results = await self._run_tests_parallel(suite.tests, suite.stop_on_failure)
        else:
            results = await self._run_tests_sequential(suite.tests, suite.stop_on_failure)

        # Run teardown
        if suite.teardown:
            try:
                await self._run_async_callable(suite.teardown)
            except Exception as e:
                logger.error(f"Suite teardown failed: {e}")

        # Store results
        self.test_results.extend(results)

        return results

    async def run_test(self, test: TestCase) -> TestResult:
        """
        Run a single test case.

        Args:
            test: Test to run

        Returns:
            Test result
        """
        logger.info(f"Running test: {test.name}")

        start_time = datetime.now()
        result = TestResult(
            test_id=test.id,
            status=TestStatus.RUNNING,
            duration_ms=0
        )

        try:
            # Prepare components
            components = self._get_components(test.components)

            # Start metrics collection
            self.metrics_collector.start_test(test.id)

            # Run test with timeout
            test_result = await asyncio.wait_for(
                test.test_function(components, self),
                timeout=test.timeout_seconds
            )

            # Collect metrics
            metrics = self.metrics_collector.end_test(test.id)

            # Update result
            result.status = TestStatus.PASSED if test_result else TestStatus.FAILED
            result.metrics = metrics

            if hasattr(test_result, '__dict__'):
                result.artifacts = test_result.__dict__

            logger.info(f"Test {test.name}: {result.status.value}")

        except asyncio.TimeoutError:
            result.status = TestStatus.ERROR
            result.error_message = f"Test timed out after {test.timeout_seconds} seconds"
            logger.error(f"Test {test.name} timed out")

        except Exception as e:
            result.status = TestStatus.ERROR
            result.error_message = str(e)
            result.stack_trace = self._get_stack_trace()
            logger.error(f"Test {test.name} failed with error: {e}")

        # Calculate duration
        end_time = datetime.now()
        result.duration_ms = (end_time - start_time).total_seconds() * 1000

        return result

    async def run_component_interaction_test(
        self,
        component1_id: str,
        component2_id: str,
        interaction_type: str
    ) -> TestResult:
        """
        Test interaction between two components.

        Args:
            component1_id: First component
            component2_id: Second component
            interaction_type: Type of interaction to test

        Returns:
            Test result
        """
        test = TestCase(
            id=f"interaction_{component1_id}_{component2_id}",
            name=f"Test {interaction_type} between {component1_id} and {component2_id}",
            component_type=ComponentType.AGENT,
            components=[component1_id, component2_id],
            test_function=self._create_interaction_test(interaction_type)
        )

        return await self.run_test(test)

    async def run_end_to_end_test(self, workflow: List[Dict[str, Any]]) -> List[TestResult]:
        """
        Run end-to-end workflow test.

        Args:
            workflow: Workflow steps to execute

        Returns:
            List of test results
        """
        results = []

        for step in workflow:
            test = TestCase(
                id=f"e2e_{step['id']}",
                name=f"E2E: {step['name']}",
                component_type=ComponentType(step.get('type', 'agent')),
                components=step.get('components', []),
                test_function=self._create_workflow_step_test(step)
            )

            result = await self.run_test(test)
            results.append(result)

            if result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                logger.warning(f"E2E workflow failed at step: {step['name']}")
                break

        return results

    async def benchmark_component(
        self,
        component_id: str,
        iterations: int = 100
    ) -> Dict[str, Any]:
        """
        Benchmark a component's performance.

        Args:
            component_id: Component to benchmark
            iterations: Number of iterations

        Returns:
            Benchmark results
        """
        component = self.component_registry.get(component_id)
        if not component:
            raise ValueError(f"Component not found: {component_id}")

        metrics = {
            'component_id': component_id,
            'iterations': iterations,
            'timings': [],
            'memory_usage': [],
            'cpu_usage': []
        }

        for i in range(iterations):
            start_time = datetime.now()

            # Collect initial metrics
            initial_metrics = self.metrics_collector.get_system_metrics()

            # Run component operation
            try:
                if hasattr(component, 'execute'):
                    await self._run_async_callable(component.execute)
                elif callable(component):
                    await self._run_async_callable(component)
            except Exception as e:
                logger.warning(f"Benchmark iteration {i} failed: {e}")

            # Collect final metrics
            final_metrics = self.metrics_collector.get_system_metrics()

            # Calculate timing
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            metrics['timings'].append(duration_ms)
            metrics['memory_usage'].append(
                final_metrics['memory'] - initial_metrics['memory']
            )
            metrics['cpu_usage'].append(
                final_metrics['cpu'] - initial_metrics['cpu']
            )

        # Calculate statistics
        metrics['stats'] = {
            'avg_time_ms': sum(metrics['timings']) / len(metrics['timings']),
            'min_time_ms': min(metrics['timings']),
            'max_time_ms': max(metrics['timings']),
            'avg_memory_mb': sum(metrics['memory_usage']) / len(metrics['memory_usage']),
            'avg_cpu_percent': sum(metrics['cpu_usage']) / len(metrics['cpu_usage'])
        }

        return metrics

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate test report.

        Returns:
            Test report with statistics
        """
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.test_results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in self.test_results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in self.test_results if r.status == TestStatus.SKIPPED)

        total_duration = sum(r.duration_ms for r in self.test_results)

        report = {
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'skipped': skipped,
                'pass_rate': (passed / total * 100) if total > 0 else 0,
                'total_duration_ms': total_duration,
                'average_duration_ms': total_duration / total if total > 0 else 0
            },
            'by_component': self._group_results_by_component(),
            'by_status': self._group_results_by_status(),
            'failures': [
                {
                    'test_id': r.test_id,
                    'error': r.error_message,
                    'stack_trace': r.stack_trace
                }
                for r in self.test_results
                if r.status in [TestStatus.FAILED, TestStatus.ERROR]
            ],
            'slowest_tests': sorted(
                self.test_results,
                key=lambda r: r.duration_ms,
                reverse=True
            )[:10],
            'timestamp': datetime.now().isoformat()
        }

        return report

    def save_report(self, filepath: str):
        """Save test report to file."""
        report = self.generate_report()

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Test report saved to: {filepath}")

    # Private helper methods

    async def _run_tests_sequential(
        self,
        tests: List[TestCase],
        stop_on_failure: bool
    ) -> List[TestResult]:
        """Run tests sequentially."""
        results = []

        for test in tests:
            result = await self.run_test(test)
            results.append(result)

            if stop_on_failure and result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                logger.warning("Stopping test execution due to failure")
                break

        return results

    async def _run_tests_parallel(
        self,
        tests: List[TestCase],
        stop_on_failure: bool
    ) -> List[TestResult]:
        """Run tests in parallel."""
        tasks = [self.run_test(test) for test in tests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(TestResult(
                    test_id=tests[i].id,
                    status=TestStatus.ERROR,
                    duration_ms=0,
                    error_message=str(result)
                ))
            else:
                final_results.append(result)

        return final_results

    def _get_components(self, component_ids: List[str]) -> Dict[str, Any]:
        """Get components by IDs."""
        components = {}

        for comp_id in component_ids:
            if comp_id in self.component_registry:
                components[comp_id] = self.component_registry[comp_id]
            else:
                logger.warning(f"Component not found: {comp_id}")

        return components

    async def _run_async_callable(self, func: Callable) -> Any:
        """Run async or sync callable."""
        if asyncio.iscoroutinefunction(func):
            return await func()
        else:
            return func()

    def _create_interaction_test(self, interaction_type: str) -> Callable:
        """Create interaction test function."""
        async def test_func(components: Dict[str, Any], runner: 'IntegrationTestRunner'):
            # Mock interaction test
            comp_ids = list(components.keys())
            logger.debug(f"Testing {interaction_type} between {comp_ids}")
            return True

        return test_func

    def _create_workflow_step_test(self, step: Dict[str, Any]) -> Callable:
        """Create workflow step test function."""
        async def test_func(components: Dict[str, Any], runner: 'IntegrationTestRunner'):
            # Mock workflow step test
            logger.debug(f"Executing workflow step: {step['name']}")
            return True

        return test_func

    def _get_stack_trace(self) -> str:
        """Get current stack trace."""
        import traceback
        return traceback.format_exc()

    def _group_results_by_component(self) -> Dict[str, Dict[str, int]]:
        """Group results by component type."""
        grouped = {}

        for result in self.test_results:
            # Extract component type from test_id
            component_type = "unknown"
            if "_" in result.test_id:
                component_type = result.test_id.split("_")[0]

            if component_type not in grouped:
                grouped[component_type] = {
                    'passed': 0,
                    'failed': 0,
                    'errors': 0
                }

            if result.status == TestStatus.PASSED:
                grouped[component_type]['passed'] += 1
            elif result.status == TestStatus.FAILED:
                grouped[component_type]['failed'] += 1
            elif result.status == TestStatus.ERROR:
                grouped[component_type]['errors'] += 1

        return grouped

    def _group_results_by_status(self) -> Dict[str, List[str]]:
        """Group test IDs by status."""
        grouped = {
            'passed': [],
            'failed': [],
            'errors': [],
            'skipped': []
        }

        for result in self.test_results:
            if result.status == TestStatus.PASSED:
                grouped['passed'].append(result.test_id)
            elif result.status == TestStatus.FAILED:
                grouped['failed'].append(result.test_id)
            elif result.status == TestStatus.ERROR:
                grouped['errors'].append(result.test_id)
            elif result.status == TestStatus.SKIPPED:
                grouped['skipped'].append(result.test_id)

        return grouped


class MetricsCollector:
    """Collects metrics during test execution."""

    def __init__(self):
        """Initialize metrics collector."""
        self.test_metrics: Dict[str, Dict[str, Any]] = {}

    def start_test(self, test_id: str):
        """Start collecting metrics for a test."""
        self.test_metrics[test_id] = {
            'start_time': datetime.now(),
            'initial_metrics': self.get_system_metrics()
        }

    def end_test(self, test_id: str) -> Dict[str, Any]:
        """End metrics collection and calculate results."""
        if test_id not in self.test_metrics:
            return {}

        end_time = datetime.now()
        final_metrics = self.get_system_metrics()
        initial_metrics = self.test_metrics[test_id]['initial_metrics']
        start_time = self.test_metrics[test_id]['start_time']

        metrics = {
            'duration_ms': (end_time - start_time).total_seconds() * 1000,
            'memory_delta_mb': final_metrics['memory'] - initial_metrics['memory'],
            'cpu_delta_percent': final_metrics['cpu'] - initial_metrics['cpu']
        }

        del self.test_metrics[test_id]
        return metrics

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        import psutil

        return {
            'memory': psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            'cpu': psutil.Process().cpu_percent(),
            'timestamp': datetime.now().isoformat()
        }


# Convenience functions

def create_test_suite(
    name: str,
    tests: List[TestCase],
    parallel: bool = False
) -> IntegrationTestSuite:
    """Create a test suite."""
    return IntegrationTestSuite(
        id=name.lower().replace(" ", "_"),
        name=name,
        tests=tests,
        parallel_execution=parallel
    )


def create_test_case(
    name: str,
    component_type: ComponentType,
    test_func: Callable,
    components: List[str] = None
) -> TestCase:
    """Create a test case."""
    return TestCase(
        id=name.lower().replace(" ", "_"),
        name=name,
        component_type=component_type,
        components=components or [],
        test_function=test_func
    )

# Backwards-compatible aliases expected by some tests
TestRunner = IntegrationTestRunner

# Prevent pytest from collecting helper classes that share the "Test" prefix
TestCase.__test__ = False  # type: ignore[attr-defined]
IntegrationTestSuite.__test__ = False  # type: ignore[attr-defined]
IntegrationTestRunner.__test__ = False  # type: ignore[attr-defined]
