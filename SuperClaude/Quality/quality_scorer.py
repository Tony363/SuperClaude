"""
Quality Scoring System for SuperClaude Framework

Implements quality evaluation and the agentic loop pattern for
automatic iteration until quality thresholds are met.
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QualityDimension(Enum):
    """Quality evaluation dimensions."""

    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    EFFICIENCY = "efficiency"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER_SATISFACTION = "user_satisfaction"


@dataclass
class QualityMetric:
    """Individual quality metric."""

    dimension: QualityDimension
    score: float  # 0-100
    weight: float  # Importance weight
    details: str
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityAssessment:
    """Complete quality assessment."""

    overall_score: float  # 0-100
    metrics: List[QualityMetric]
    timestamp: datetime
    iteration: int
    passed: bool
    threshold: float
    context: Dict[str, Any]
    improvements_needed: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IterationResult:
    """Result of an agentic loop iteration."""

    iteration: int
    input_quality: float
    output_quality: float
    improvements_applied: List[str]
    time_taken: float
    success: bool


class QualityScorer:
    """
    Evaluates output quality and manages the agentic loop pattern.

    Automatically iterates on outputs until quality thresholds are met
    or maximum iterations are reached.
    """

    # Configuration constants
    DEFAULT_THRESHOLD = 70.0  # Minimum acceptable quality score
    MAX_ITERATIONS = 5  # Maximum improvement iterations
    MIN_IMPROVEMENT = 5.0  # Minimum score improvement to continue

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        """
        Initialize the quality scorer.

        Args:
            threshold: Minimum acceptable quality score (0-100)
        """
        self.logger = logging.getLogger(__name__)
        self.threshold = threshold

        # Quality evaluators by dimension
        self.evaluators: Dict[QualityDimension, Callable] = {
            QualityDimension.CORRECTNESS: self._evaluate_correctness,
            QualityDimension.COMPLETENESS: self._evaluate_completeness,
            QualityDimension.CLARITY: self._evaluate_clarity,
            QualityDimension.EFFICIENCY: self._evaluate_efficiency,
            QualityDimension.MAINTAINABILITY: self._evaluate_maintainability,
            QualityDimension.SECURITY: self._evaluate_security,
            QualityDimension.PERFORMANCE: self._evaluate_performance,
            QualityDimension.USER_SATISFACTION: self._evaluate_user_satisfaction
        }

        # Default weights for dimensions
        self.default_weights = {
            QualityDimension.CORRECTNESS: 0.25,
            QualityDimension.COMPLETENESS: 0.20,
            QualityDimension.CLARITY: 0.15,
            QualityDimension.EFFICIENCY: 0.10,
            QualityDimension.MAINTAINABILITY: 0.10,
            QualityDimension.SECURITY: 0.10,
            QualityDimension.PERFORMANCE: 0.05,
            QualityDimension.USER_SATISFACTION: 0.05
        }

        # Iteration history
        self.iteration_history: List[IterationResult] = []
        self.assessment_history: List[QualityAssessment] = []

        # Custom evaluators
        self.custom_evaluators: List[Callable] = []

    def evaluate(
        self,
        output: Any,
        context: Dict[str, Any],
        dimensions: Optional[List[QualityDimension]] = None,
        weights: Optional[Dict[QualityDimension, float]] = None,
        iteration: int = 0
    ) -> QualityAssessment:
        """
        Evaluate output quality.

        Args:
            output: Output to evaluate
            context: Evaluation context
            dimensions: Specific dimensions to evaluate (all if None)
            weights: Custom dimension weights
            iteration: Current iteration number

        Returns:
            Quality assessment
        """
        # Select dimensions to evaluate
        if dimensions is None:
            dimensions = list(QualityDimension)

        # Use custom weights or defaults
        eval_weights = weights or self.default_weights

        # Evaluate each dimension
        metrics = []
        for dimension in dimensions:
            if dimension in self.evaluators:
                evaluator = self.evaluators[dimension]
                metric = evaluator(output, context)
                metric.weight = eval_weights.get(dimension, 0.1)
                metrics.append(metric)

        # Apply custom evaluators
        for custom_evaluator in self.custom_evaluators:
            try:
                custom_metric = custom_evaluator(output, context)
                if custom_metric:
                    metrics.append(custom_metric)
            except Exception as e:
                self.logger.error(f"Custom evaluator error: {e}")

        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics)

        # Determine if quality passes threshold
        passed = overall_score >= self.threshold

        # Identify improvements needed
        improvements = self._identify_improvements(metrics, overall_score)

        # Create assessment
        assessment = QualityAssessment(
            overall_score=overall_score,
            metrics=metrics,
            timestamp=datetime.now(),
            iteration=iteration,
            passed=passed,
            threshold=self.threshold,
            context=context,
            improvements_needed=improvements
        )

        # Store in history
        self.assessment_history.append(assessment)

        return assessment

    def agentic_loop(
        self,
        initial_output: Any,
        context: Dict[str, Any],
        improver_func: Callable,
        max_iterations: Optional[int] = None,
        min_improvement: Optional[float] = None
    ) -> Tuple[Any, QualityAssessment, List[IterationResult]]:
        """
        Run agentic loop to iteratively improve output quality.

        Args:
            initial_output: Initial output to improve
            context: Execution context
            improver_func: Function to improve output
            max_iterations: Maximum iterations (default: MAX_ITERATIONS)
            min_improvement: Minimum improvement to continue (default: MIN_IMPROVEMENT)

        Returns:
            Tuple of (final_output, final_assessment, iteration_history)
        """
        max_iter = max_iterations or self.MAX_ITERATIONS
        min_improv = min_improvement or self.MIN_IMPROVEMENT

        current_output = initial_output
        iteration_results = []
        previous_score = 0.0

        for iteration in range(max_iter):
            start_time = datetime.now()

            # Evaluate current quality
            assessment = self.evaluate(
                current_output,
                context,
                iteration=iteration
            )

            current_score = assessment.overall_score

            # Check if quality threshold is met
            if assessment.passed:
                self.logger.info(f"Quality threshold met at iteration {iteration}: {current_score:.1f}")
                result = IterationResult(
                    iteration=iteration,
                    input_quality=previous_score,
                    output_quality=current_score,
                    improvements_applied=[],
                    time_taken=(datetime.now() - start_time).total_seconds(),
                    success=True
                )
                iteration_results.append(result)
                break

            # Check if improvement is sufficient
            if iteration > 0:
                improvement = current_score - previous_score
                if improvement < min_improv:
                    self.logger.info(
                        f"Insufficient improvement ({improvement:.1f}) at iteration {iteration}"
                    )
                    result = IterationResult(
                        iteration=iteration,
                        input_quality=previous_score,
                        output_quality=current_score,
                        improvements_applied=[],
                        time_taken=(datetime.now() - start_time).total_seconds(),
                        success=False
                    )
                    iteration_results.append(result)
                    break

            # Apply improvements
            improvements_context = {
                **context,
                'quality_assessment': assessment,
                'improvements_needed': assessment.improvements_needed,
                'current_score': current_score,
                'target_score': self.threshold
            }

            try:
                improved_output = improver_func(
                    current_output,
                    improvements_context
                )

                result = IterationResult(
                    iteration=iteration,
                    input_quality=current_score,
                    output_quality=0.0,  # Will be updated in next iteration
                    improvements_applied=assessment.improvements_needed[:5],  # Top 5
                    time_taken=(datetime.now() - start_time).total_seconds(),
                    success=False
                )
                iteration_results.append(result)

                current_output = improved_output
                previous_score = current_score

            except Exception as e:
                self.logger.error(f"Improvement function error: {e}")
                break

        # Final evaluation
        final_assessment = self.evaluate(
            current_output,
            context,
            iteration=len(iteration_results)
        )

        # Update last iteration result
        if iteration_results:
            iteration_results[-1].output_quality = final_assessment.overall_score
            iteration_results[-1].success = final_assessment.passed

        # Store iteration history
        self.iteration_history.extend(iteration_results)

        return current_output, final_assessment, iteration_results

    def add_custom_evaluator(self, evaluator: Callable):
        """
        Add custom quality evaluator.

        Args:
            evaluator: Function that returns QualityMetric
        """
        self.custom_evaluators.append(evaluator)

    def get_improvement_suggestions(
        self,
        assessment: QualityAssessment
    ) -> List[Dict[str, Any]]:
        """
        Get detailed improvement suggestions.

        Args:
            assessment: Quality assessment

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        # Analyze each metric
        for metric in assessment.metrics:
            if metric.score < 70:  # Focus on low-scoring dimensions
                for suggestion in metric.suggestions:
                    suggestions.append({
                        'dimension': metric.dimension.value,
                        'current_score': metric.score,
                        'suggestion': suggestion,
                        'priority': 'high' if metric.score < 50 else 'medium',
                        'impact': metric.weight * (100 - metric.score)
                    })

        # Sort by impact
        suggestions.sort(key=lambda x: x['impact'], reverse=True)

        return suggestions

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of quality metrics.

        Returns:
            Metrics summary
        """
        if not self.assessment_history:
            return {}

        scores = [a.overall_score for a in self.assessment_history]
        passed = [a for a in self.assessment_history if a.passed]

        return {
            'total_assessments': len(self.assessment_history),
            'average_score': sum(scores) / len(scores),
            'min_score': min(scores),
            'max_score': max(scores),
            'pass_rate': len(passed) / len(self.assessment_history),
            'total_iterations': sum(r.iteration for r in self.iteration_history),
            'average_iterations': (
                sum(r.iteration for r in self.iteration_history) / len(self.iteration_history)
                if self.iteration_history else 0
            )
        }

    def _evaluate_correctness(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate correctness dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        # Check for errors
        if isinstance(output, dict):
            if output.get('errors'):
                score -= 30
                issues.append("Errors present in output")
                suggestions.append("Fix errors before proceeding")

            if not output.get('success', True):
                score -= 20
                issues.append("Operation not successful")

        # Check for test results if available
        if 'test_results' in context:
            test_pass_rate = context['test_results'].get('pass_rate', 0)
            score = test_pass_rate * 100

        return QualityMetric(
            dimension=QualityDimension.CORRECTNESS,
            score=max(0, min(100, score)),
            weight=0.25,
            details="Correctness based on errors and test results",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_completeness(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate completeness dimension."""
        score = 80.0  # Base score
        issues = []
        suggestions = []

        # Check for required fields
        if 'requirements' in context:
            requirements = context['requirements']
            if isinstance(requirements, list):
                met_requirements = 0
                for req in requirements:
                    if self._check_requirement_met(output, req):
                        met_requirements += 1
                    else:
                        issues.append(f"Missing requirement: {req}")
                        suggestions.append(f"Implement {req}")

                if requirements:
                    score = (met_requirements / len(requirements)) * 100

        # Check for TODO comments
        output_str = str(output)
        if 'TODO' in output_str or 'FIXME' in output_str:
            score -= 20
            issues.append("Contains TODO/FIXME comments")
            suggestions.append("Complete all TODO items")

        return QualityMetric(
            dimension=QualityDimension.COMPLETENESS,
            score=max(0, min(100, score)),
            weight=0.20,
            details="Completeness of implementation",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_clarity(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate clarity dimension."""
        score = 75.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        # Check documentation
        if isinstance(output, dict) and 'code' in output:
            code = output['code']

            # Check for docstrings
            if 'def ' in code and '"""' not in code:
                score -= 15
                issues.append("Missing docstrings")
                suggestions.append("Add docstrings to functions")

            # Check for comments
            if len(code.split('\n')) > 20 and '#' not in code:
                score -= 10
                issues.append("No comments in complex code")
                suggestions.append("Add explanatory comments")

        # Check naming conventions
        if re.search(r'\b[a-z]\b', output_str):  # Single letter variables
            score -= 10
            issues.append("Single letter variable names")
            suggestions.append("Use descriptive variable names")

        return QualityMetric(
            dimension=QualityDimension.CLARITY,
            score=max(0, min(100, score)),
            weight=0.15,
            details="Code clarity and documentation",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_efficiency(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate efficiency dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        # Check for obvious inefficiencies
        if 'for' in output_str:
            # Check for nested loops
            if output_str.count('for') > 2:
                score -= 15
                issues.append("Multiple nested loops detected")
                suggestions.append("Consider optimizing nested loops")

        # Check for performance metrics if available
        if 'performance' in context:
            perf = context['performance']
            if perf.get('execution_time', 0) > perf.get('target_time', float('inf')):
                score -= 20
                issues.append("Execution time exceeds target")
                suggestions.append("Optimize for performance")

        return QualityMetric(
            dimension=QualityDimension.EFFICIENCY,
            score=max(0, min(100, score)),
            weight=0.10,
            details="Code efficiency and performance",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_maintainability(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate maintainability dimension."""
        score = 75.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        # Check complexity
        if isinstance(output, dict) and 'code' in output:
            code = output['code']
            lines = code.split('\n')

            # Check function length
            if any(len(func) > 50 for func in self._extract_functions(code)):
                score -= 15
                issues.append("Functions too long")
                suggestions.append("Break down long functions")

            # Check file length
            if len(lines) > 500:
                score -= 10
                issues.append("File too long")
                suggestions.append("Split into multiple modules")

        # Check for code duplication (simplified)
        if self._has_duplication(output_str):
            score -= 15
            issues.append("Code duplication detected")
            suggestions.append("Extract common functionality")

        return QualityMetric(
            dimension=QualityDimension.MAINTAINABILITY,
            score=max(0, min(100, score)),
            weight=0.10,
            details="Code maintainability",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_security(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate security dimension."""
        score = 80.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        # Check for common security issues
        security_patterns = [
            (r'eval\(', 'Use of eval() is dangerous', 20),
            (r'exec\(', 'Use of exec() is dangerous', 20),
            (r'pickle\.loads', 'Unsafe deserialization', 15),
            (r'os\.system', 'Direct system calls', 15),
            (r'password\s*=\s*["\']', 'Hardcoded password', 25)
        ]

        for pattern, issue, penalty in security_patterns:
            if re.search(pattern, output_str, re.IGNORECASE):
                score -= penalty
                issues.append(issue)
                suggestions.append(f"Fix security issue: {issue}")

        # Check for input validation
        if 'user_input' in output_str and 'validate' not in output_str:
            score -= 10
            issues.append("No input validation")
            suggestions.append("Add input validation")

        return QualityMetric(
            dimension=QualityDimension.SECURITY,
            score=max(0, min(100, score)),
            weight=0.10,
            details="Security assessment",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_performance(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate performance dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        # Check performance metrics if available
        if 'metrics' in context:
            metrics = context['metrics']

            # Response time
            if metrics.get('response_time', 0) > 1000:  # >1s
                score -= 20
                issues.append("High response time")
                suggestions.append("Optimize response time")

            # Memory usage
            if metrics.get('memory_mb', 0) > 500:  # >500MB
                score -= 15
                issues.append("High memory usage")
                suggestions.append("Reduce memory footprint")

        return QualityMetric(
            dimension=QualityDimension.PERFORMANCE,
            score=max(0, min(100, score)),
            weight=0.05,
            details="Performance metrics",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_user_satisfaction(
        self,
        output: Any,
        context: Dict[str, Any]
    ) -> QualityMetric:
        """Evaluate user satisfaction dimension."""
        score = 75.0  # Base score
        issues = []
        suggestions = []

        # Check if user feedback is available
        if 'user_feedback' in context:
            feedback = context['user_feedback']
            if isinstance(feedback, dict):
                score = feedback.get('satisfaction', 75)
                if feedback.get('issues'):
                    issues.extend(feedback['issues'])
                if feedback.get('suggestions'):
                    suggestions.extend(feedback['suggestions'])

        return QualityMetric(
            dimension=QualityDimension.USER_SATISFACTION,
            score=max(0, min(100, score)),
            weight=0.05,
            details="User satisfaction estimate",
            issues=issues,
            suggestions=suggestions
        )

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """Calculate weighted overall score."""
        if not metrics:
            return 0.0

        total_weight = sum(m.weight for m in metrics)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(m.score * m.weight for m in metrics)
        return weighted_sum / total_weight

    def _identify_improvements(
        self,
        metrics: List[QualityMetric],
        overall_score: float
    ) -> List[str]:
        """Identify key improvements needed."""
        improvements = []

        # Sort metrics by score (lowest first)
        sorted_metrics = sorted(metrics, key=lambda m: m.score)

        # Focus on lowest scoring dimensions
        for metric in sorted_metrics[:3]:  # Top 3 worst
            if metric.score < 70:
                # Add top suggestions from this dimension
                for suggestion in metric.suggestions[:2]:
                    improvements.append(f"{metric.dimension.value}: {suggestion}")

        # Add general improvements if score is low
        if overall_score < 50:
            improvements.append("Major refactoring needed")
        elif overall_score < 70:
            improvements.append("Address critical issues first")

        return improvements

    def _check_requirement_met(self, output: Any, requirement: str) -> bool:
        """Check if a requirement is met in output."""
        output_str = str(output).lower()
        requirement_lower = requirement.lower()

        # Simple keyword matching
        keywords = requirement_lower.split()
        return all(keyword in output_str for keyword in keywords)

    def _extract_functions(self, code: str) -> List[str]:
        """Extract function bodies from code."""
        functions = []
        lines = code.split('\n')
        current_function = []
        in_function = False

        for line in lines:
            if line.strip().startswith('def '):
                if current_function:
                    functions.append('\n'.join(current_function))
                current_function = [line]
                in_function = True
            elif in_function:
                if line and not line[0].isspace() and not line.startswith('#'):
                    # End of function
                    functions.append('\n'.join(current_function))
                    current_function = []
                    in_function = False
                else:
                    current_function.append(line)

        if current_function:
            functions.append('\n'.join(current_function))

        return functions

    def _has_duplication(self, text: str) -> bool:
        """Check for code duplication (simplified)."""
        lines = text.split('\n')
        line_count = {}

        for line in lines:
            stripped = line.strip()
            if len(stripped) > 20:  # Ignore short lines
                line_count[stripped] = line_count.get(stripped, 0) + 1

        # If any line appears more than twice, consider it duplication
        return any(count > 2 for count in line_count.values())

    def reset_history(self):
        """Reset assessment and iteration history."""
        self.iteration_history.clear()
        self.assessment_history.clear()