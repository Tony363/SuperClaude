"""
Quality Engineer Agent for SuperClaude Framework

This agent specializes in testing, validation, and quality assurance
for software projects.
"""

from typing import Dict, Any, List, Optional
import re
import json
import logging
from pathlib import Path

from ..base import BaseAgent


class QualityEngineer(BaseAgent):
    """
    Agent specialized in software quality assurance and testing.

    Provides comprehensive testing strategies, test generation, coverage
    analysis, and quality metrics for codebases.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the quality engineer.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if 'name' not in config:
            config['name'] = 'quality-engineer'
        if 'description' not in config:
            config['description'] = 'Ensure software quality through comprehensive testing'
        if 'category' not in config:
            config['category'] = 'quality'

        super().__init__(config)

        # Test patterns and strategies
        self.test_patterns = self._initialize_test_patterns()
        self.coverage_thresholds = self._initialize_coverage_thresholds()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute quality engineering tasks.

        Args:
            context: Execution context

        Returns:
            Quality assessment and testing results
        """
        result = {
            'success': False,
            'output': '',
            'actions_taken': [],
            'errors': [],
            'test_strategy': None,
            'coverage_analysis': {},
            'quality_metrics': {}
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result['errors'].append("Failed to initialize agent")
                    return result

            task = context.get('task', '')
            files = context.get('files', [])
            code = context.get('code', '')
            test_type = context.get('test_type', 'unit')

            if not task and not files and not code:
                result['errors'].append("No content to test or validate")
                return result

            self.logger.info(f"Starting quality assessment: {task[:100]}...")

            # Phase 1: Analyze testing requirements
            requirements = self._analyze_test_requirements(task, files, code)
            result['actions_taken'].append(f"Analyzed {len(requirements)} test requirements")

            # Phase 2: Generate test strategy
            strategy = self._generate_test_strategy(requirements, test_type)
            result['test_strategy'] = strategy
            result['actions_taken'].append(f"Generated {strategy['approach']} testing strategy")

            # Phase 3: Create test cases
            test_cases = self._generate_test_cases(strategy, code, files)
            result['actions_taken'].append(f"Generated {len(test_cases)} test cases")

            # Phase 4: Analyze coverage
            coverage = self._analyze_coverage(test_cases, code, files)
            result['coverage_analysis'] = coverage
            result['actions_taken'].append(f"Coverage analysis: {coverage.get('percentage', 0):.1f}%")

            # Phase 5: Calculate quality metrics
            metrics = self._calculate_quality_metrics(
                test_cases, coverage, requirements
            )
            result['quality_metrics'] = metrics

            # Phase 6: Generate quality report
            report = self._generate_quality_report(
                task, strategy, test_cases, coverage, metrics
            )
            result['output'] = report

            result['success'] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            result['errors'].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains quality/testing tasks
        """
        task = context.get('task', '')

        # Check for quality/testing keywords
        quality_keywords = [
            'test', 'testing', 'validate', 'validation', 'verify',
            'quality', 'qa', 'coverage', 'unit test', 'integration test',
            'e2e', 'end-to-end', 'test case', 'test suite', 'tdd', 'bdd'
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in quality_keywords)

    def _initialize_test_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize testing patterns and strategies.

        Returns:
            Dictionary of test patterns
        """
        return {
            'unit': {
                'description': 'Unit testing individual functions/methods',
                'coverage_target': 80,
                'patterns': ['test isolated functionality', 'mock dependencies', 'edge cases']
            },
            'integration': {
                'description': 'Integration testing between components',
                'coverage_target': 70,
                'patterns': ['test component interactions', 'API contracts', 'data flow']
            },
            'e2e': {
                'description': 'End-to-end testing of user flows',
                'coverage_target': 60,
                'patterns': ['user journeys', 'critical paths', 'real scenarios']
            },
            'performance': {
                'description': 'Performance and load testing',
                'coverage_target': None,
                'patterns': ['load testing', 'stress testing', 'benchmark']
            },
            'security': {
                'description': 'Security testing and vulnerability scanning',
                'coverage_target': None,
                'patterns': ['input validation', 'authentication', 'authorization']
            }
        }

    def _initialize_coverage_thresholds(self) -> Dict[str, float]:
        """
        Initialize coverage thresholds.

        Returns:
            Dictionary of coverage thresholds
        """
        return {
            'excellent': 90,
            'good': 80,
            'acceptable': 70,
            'needs_improvement': 60,
            'poor': 50
        }

    def _analyze_test_requirements(
        self, task: str, files: List[str], code: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze testing requirements.

        Args:
            task: Task description
            files: File paths
            code: Code snippet

        Returns:
            List of test requirements
        """
        requirements = []

        # Extract testable components
        if code:
            # Find functions/methods
            function_pattern = r'(?:def|function|const\s+\w+\s*=\s*(?:async\s*)?\()'
            functions = re.findall(function_pattern, code)
            for func in functions:
                requirements.append({
                    'type': 'function',
                    'name': func,
                    'priority': 'high'
                })

        # Identify test types needed
        if 'api' in task.lower() or 'endpoint' in task.lower():
            requirements.append({
                'type': 'api_test',
                'scope': 'integration',
                'priority': 'high'
            })

        if 'ui' in task.lower() or 'component' in task.lower():
            requirements.append({
                'type': 'component_test',
                'scope': 'unit',
                'priority': 'high'
            })

        if 'flow' in task.lower() or 'journey' in task.lower():
            requirements.append({
                'type': 'e2e_test',
                'scope': 'e2e',
                'priority': 'medium'
            })

        # Default requirement
        if not requirements:
            requirements.append({
                'type': 'general_test',
                'scope': 'unit',
                'priority': 'medium'
            })

        return requirements

    def _generate_test_strategy(
        self, requirements: List[Dict[str, Any]], test_type: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive test strategy.

        Args:
            requirements: Test requirements
            test_type: Type of testing

        Returns:
            Test strategy
        """
        strategy = {
            'approach': test_type,
            'levels': [],
            'tools': [],
            'patterns': [],
            'priorities': []
        }

        # Determine test levels
        if test_type == 'unit':
            strategy['levels'] = ['unit', 'component']
            strategy['tools'] = ['jest', 'pytest', 'mocha']
            strategy['patterns'] = ['AAA pattern', 'mocking', 'isolation']
        elif test_type == 'integration':
            strategy['levels'] = ['integration', 'contract']
            strategy['tools'] = ['postman', 'newman', 'supertest']
            strategy['patterns'] = ['API testing', 'database testing']
        elif test_type == 'e2e':
            strategy['levels'] = ['e2e', 'acceptance']
            strategy['tools'] = ['cypress', 'selenium', 'external-playwright']
            strategy['patterns'] = ['page object', 'user flows']

        # Set priorities based on requirements
        high_priority = [r for r in requirements if r.get('priority') == 'high']
        strategy['priorities'] = [
            f"Focus on {r['type']}" for r in high_priority
        ]

        return strategy

    def _generate_test_cases(
        self, strategy: Dict[str, Any], code: str, files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate test cases based on strategy.

        Args:
            strategy: Test strategy
            code: Code to test
            files: Files to test

        Returns:
            List of test cases
        """
        test_cases = []

        # Generate test cases by strategy
        if strategy['approach'] == 'unit':
            # Happy path tests
            test_cases.append({
                'name': 'should work with valid input',
                'type': 'positive',
                'priority': 'high',
                'coverage': ['happy_path']
            })

            # Edge cases
            test_cases.append({
                'name': 'should handle null/undefined input',
                'type': 'edge_case',
                'priority': 'high',
                'coverage': ['error_handling']
            })

            # Boundary cases
            test_cases.append({
                'name': 'should handle boundary values',
                'type': 'boundary',
                'priority': 'medium',
                'coverage': ['boundary_testing']
            })

        elif strategy['approach'] == 'integration':
            # API tests
            test_cases.append({
                'name': 'should integrate with external service',
                'type': 'integration',
                'priority': 'high',
                'coverage': ['api_integration']
            })

            # Data flow tests
            test_cases.append({
                'name': 'should handle data transformation',
                'type': 'data_flow',
                'priority': 'high',
                'coverage': ['data_pipeline']
            })

        elif strategy['approach'] == 'e2e':
            # User flow tests
            test_cases.append({
                'name': 'should complete user journey',
                'type': 'e2e',
                'priority': 'high',
                'coverage': ['user_flow']
            })

            # Critical path tests
            test_cases.append({
                'name': 'should handle critical business flow',
                'type': 'critical_path',
                'priority': 'critical',
                'coverage': ['business_logic']
            })

        # Add negative tests
        test_cases.append({
            'name': 'should handle error conditions',
            'type': 'negative',
            'priority': 'high',
            'coverage': ['error_handling']
        })

        return test_cases

    def _analyze_coverage(
        self, test_cases: List[Dict[str, Any]], code: str, files: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze test coverage.

        Args:
            test_cases: Generated test cases
            code: Code being tested
            files: Files being tested

        Returns:
            Coverage analysis
        """
        coverage = {
            'percentage': 0,
            'lines_covered': 0,
            'lines_total': 0,
            'gaps': [],
            'rating': 'unknown'
        }

        # Calculate coverage metrics
        coverage_areas = set()
        for test_case in test_cases:
            coverage_areas.update(test_case.get('coverage', []))

        # Estimate coverage percentage
        total_areas = 10  # Simplified: assume 10 testable areas
        covered_areas = len(coverage_areas)
        coverage['percentage'] = (covered_areas / total_areas) * 100

        # Estimate line coverage (simplified)
        if code:
            lines = code.split('\n')
            executable_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
            coverage['lines_total'] = len(executable_lines)
            coverage['lines_covered'] = int(len(executable_lines) * coverage['percentage'] / 100)

        # Identify gaps
        essential_areas = {'happy_path', 'error_handling', 'edge_cases', 'boundary_testing'}
        missing_areas = essential_areas - coverage_areas
        coverage['gaps'] = list(missing_areas)

        # Determine rating
        percentage = coverage['percentage']
        for rating, threshold in self.coverage_thresholds.items():
            if percentage >= threshold:
                coverage['rating'] = rating
                break

        return coverage

    def _calculate_quality_metrics(
        self, test_cases: List[Dict[str, Any]],
        coverage: Dict[str, Any],
        requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate quality metrics.

        Args:
            test_cases: Test cases
            coverage: Coverage analysis
            requirements: Test requirements

        Returns:
            Quality metrics
        """
        metrics = {
            'test_count': len(test_cases),
            'coverage_score': coverage['percentage'],
            'requirement_coverage': 0,
            'risk_score': 0,
            'quality_score': 0
        }

        # Calculate requirement coverage
        high_priority_reqs = [r for r in requirements if r.get('priority') == 'high']
        if high_priority_reqs:
            covered_reqs = min(len(test_cases), len(high_priority_reqs))
            metrics['requirement_coverage'] = (covered_reqs / len(high_priority_reqs)) * 100

        # Calculate risk score (inverse of coverage)
        metrics['risk_score'] = 100 - coverage['percentage']

        # Calculate overall quality score
        weights = {
            'coverage': 0.4,
            'test_count': 0.2,
            'requirement': 0.3,
            'risk': 0.1
        }

        normalized_test_count = min(100, len(test_cases) * 10)  # 10 points per test

        metrics['quality_score'] = (
            coverage['percentage'] * weights['coverage'] +
            normalized_test_count * weights['test_count'] +
            metrics['requirement_coverage'] * weights['requirement'] +
            (100 - metrics['risk_score']) * weights['risk']
        )

        return metrics

    def _generate_quality_report(
        self, task: str, strategy: Dict[str, Any],
        test_cases: List[Dict[str, Any]], coverage: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Generate comprehensive quality report.

        Args:
            task: Original task
            strategy: Test strategy
            test_cases: Generated test cases
            coverage: Coverage analysis
            metrics: Quality metrics

        Returns:
            Quality report
        """
        lines = []

        # Header
        lines.append("# Quality Assessment Report\n")
        lines.append(f"**Task**: {task}\n")

        # Test Strategy
        lines.append("\n## Test Strategy\n")
        lines.append(f"**Approach**: {strategy['approach']}")
        lines.append(f"**Levels**: {', '.join(strategy['levels'])}")
        if strategy['tools']:
            lines.append(f"**Recommended Tools**: {', '.join(strategy['tools'])}")
        if strategy['patterns']:
            lines.append(f"**Patterns**: {', '.join(strategy['patterns'])}")

        # Test Cases
        lines.append("\n## Test Cases Generated\n")
        for i, test_case in enumerate(test_cases, 1):
            priority_emoji = '🔴' if test_case['priority'] == 'high' else '🟡'
            lines.append(f"{i}. {priority_emoji} **{test_case['name']}**")
            lines.append(f"   - Type: {test_case['type']}")
            lines.append(f"   - Coverage: {', '.join(test_case['coverage'])}")

        # Coverage Analysis
        lines.append("\n## Coverage Analysis\n")
        lines.append(f"**Coverage**: {coverage['percentage']:.1f}%")
        lines.append(f"**Rating**: {coverage['rating'].replace('_', ' ').title()}")
        if coverage['lines_total']:
            lines.append(f"**Lines**: {coverage['lines_covered']}/{coverage['lines_total']}")

        if coverage['gaps']:
            lines.append("\n### Coverage Gaps")
            for gap in coverage['gaps']:
                lines.append(f"- ⚠️ {gap.replace('_', ' ').title()}")

        # Quality Metrics
        lines.append("\n## Quality Metrics\n")
        lines.append(f"- **Test Count**: {metrics['test_count']}")
        lines.append(f"- **Coverage Score**: {metrics['coverage_score']:.1f}%")
        lines.append(f"- **Requirement Coverage**: {metrics['requirement_coverage']:.1f}%")
        lines.append(f"- **Risk Score**: {metrics['risk_score']:.1f}%")
        lines.append(f"- **Overall Quality Score**: {metrics['quality_score']:.1f}/100")

        # Recommendations
        lines.append("\n## Recommendations\n")

        if metrics['quality_score'] < 70:
            lines.append("1. 🔴 **Urgent**: Increase test coverage to meet quality standards")
        if coverage['gaps']:
            lines.append("2. ⚠️ **Important**: Add tests for missing coverage areas")
        if metrics['risk_score'] > 30:
            lines.append("3. ⚠️ **Risk**: High risk areas need additional testing")

        lines.append("\n### Next Steps")
        lines.append("1. Implement generated test cases")
        lines.append("2. Set up continuous integration for automated testing")
        lines.append("3. Monitor coverage metrics over time")
        lines.append("4. Add tests for new features before implementation")

        return '\n'.join(lines)
