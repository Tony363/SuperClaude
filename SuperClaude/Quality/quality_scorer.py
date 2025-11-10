"""
Quality Scoring System for SuperClaude Framework

Implements quality evaluation and the agentic loop pattern for
automatic iteration until quality thresholds are met.
"""

import logging
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:  # Optional dependency for YAML configs
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore

DEFAULT_COMPONENT_WEIGHTS = {
    "superclaude": 0.6,
    "completeness": 0.25,
    "test_coverage": 0.15,
}


class QualityDimension(Enum):
    """Quality evaluation dimensions."""

    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    SCALABILITY = "scalability"
    TESTABILITY = "testability"
    USABILITY = "usability"


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
    band: str = "iterate"
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


@dataclass(frozen=True)
class QualityThresholds:
    """Shared thresholds for routing and CI."""

    production_ready: float = 90.0
    needs_attention: float = 75.0
    iterate: float = 0.0

    def classify(self, score: float) -> str:
        if score >= self.production_ready:
            return "production_ready"
        if score >= self.needs_attention:
            return "needs_attention"
        return "iterate"


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

    def __init__(self, threshold: float = DEFAULT_THRESHOLD, config_path: Optional[str] = None):
        """
        Initialize the quality scorer.

        Args:
            threshold: Minimum acceptable quality score (0-100)
        """
        self.logger = logging.getLogger(__name__)
        self.threshold = threshold
        self.config_path = Path(config_path) if config_path else Path(__file__).resolve().parent.parent / "Config" / "quality.yaml"
        self.config_data: Dict[str, Any] = {}

        # Quality evaluators by dimension
        self.evaluators: Dict[QualityDimension, Callable] = {
            QualityDimension.CORRECTNESS: self._evaluate_correctness,
            QualityDimension.COMPLETENESS: self._evaluate_completeness,
            QualityDimension.MAINTAINABILITY: self._evaluate_maintainability,
            QualityDimension.SECURITY: self._evaluate_security,
            QualityDimension.PERFORMANCE: self._evaluate_performance,
            QualityDimension.SCALABILITY: self._evaluate_scalability,
            QualityDimension.TESTABILITY: self._evaluate_testability,
            QualityDimension.USABILITY: self._evaluate_usability
        }

        # Default weights for dimensions
        self.default_weights = {
            QualityDimension.CORRECTNESS: 0.25,
            QualityDimension.COMPLETENESS: 0.20,
            QualityDimension.MAINTAINABILITY: 0.10,
            QualityDimension.SECURITY: 0.10,
            QualityDimension.PERFORMANCE: 0.10,
            QualityDimension.SCALABILITY: 0.10,
            QualityDimension.TESTABILITY: 0.10,
            QualityDimension.USABILITY: 0.05
        }

        self._load_configuration()
        override_threshold = threshold if threshold != self.DEFAULT_THRESHOLD else None
        self.component_weights = self._load_component_weights()
        self.thresholds = self._load_thresholds(override_threshold)
        if override_threshold is None:
            self.threshold = self.thresholds.production_ready

        # Iteration history
        self.iteration_history: List[IterationResult] = []
        self.assessment_history: List[QualityAssessment] = []

        # Custom evaluators
        self.custom_evaluators: List[Callable] = []

    def _load_configuration(self) -> None:
        """Load quality configuration from YAML if available."""
        if not self.config_path.exists():
            self.logger.debug(f"Quality config not found at {self.config_path}")
            return

        if yaml is None:
            self.logger.debug("PyYAML not installed; skipping quality config load")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:
            self.logger.warning(f"Failed to read quality config {self.config_path}: {exc}")
            return

        self.config_data = data

        # Update weights based on configuration
        dimensions_cfg = data.get("dimensions", {})
        for dim_name, dim_config in dimensions_cfg.items():
            try:
                dimension = QualityDimension(dim_name)
            except ValueError:
                self.logger.debug(f"Ignoring unknown quality dimension '{dim_name}' from config")
                continue

            weight = dim_config.get("weight")
            if isinstance(weight, (int, float)):
                self.default_weights[dimension] = float(weight)

        # Update threshold if scoring thresholds are defined
        scoring_cfg = data.get("scoring", {})
        thresholds_cfg = scoring_cfg.get("thresholds", {})
        if "good" in thresholds_cfg:
            try:
                self.threshold = float(thresholds_cfg["good"])
            except (TypeError, ValueError):
                self.logger.debug("Invalid 'good' threshold in quality config")

    def _load_component_weights(self) -> Dict[str, float]:
        weights = DEFAULT_COMPONENT_WEIGHTS.copy()
        config_weights: Dict[str, Any] = {}
        if self.config_data:
            scoring_cfg = self.config_data.get("scoring") or {}
            config_weights = scoring_cfg.get("component_weights", {}) or {}

        for key, value in config_weights.items():
            if key in weights and isinstance(value, (int, float)):
                weights[key] = max(0.0, float(value))

        total = sum(weights.values())
        if total <= 0:
            return DEFAULT_COMPONENT_WEIGHTS.copy()
        return weights

    def _load_thresholds(self, override_threshold: Optional[float]) -> QualityThresholds:
        scoring_cfg = self.config_data.get("scoring", {}) if self.config_data else {}
        thresholds_cfg = scoring_cfg.get("thresholds", {}) if isinstance(scoring_cfg, dict) else {}

        def _coerce(keys: Sequence[str], default: float) -> float:
            for key in keys:
                if key in thresholds_cfg:
                    try:
                        return float(thresholds_cfg[key])
                    except (TypeError, ValueError):
                        continue
            return default

        thresholds = QualityThresholds(
            production_ready=_coerce(["production_ready", "excellent", "production"], 90.0),
            needs_attention=_coerce(["needs_attention", "good"], 75.0),
            iterate=_coerce(["iterate", "failing"], 0.0),
        )

        if override_threshold is not None:
            needs_attention = min(thresholds.needs_attention, float(override_threshold))
            thresholds = QualityThresholds(
                production_ready=float(override_threshold),
                needs_attention=needs_attention,
                iterate=thresholds.iterate,
            )

        return thresholds

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
            dimensions = list(self.default_weights.keys())

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
        overall_score, score_metadata = self._calculate_overall_score(metrics, context)

        # Determine if quality passes threshold
        band = self.thresholds.classify(overall_score)
        passed = overall_score >= self.thresholds.production_ready

        # Identify improvements needed
        improvements = self._identify_improvements(metrics, overall_score)

        metadata = {
            **score_metadata,
            "thresholds": {
                "production_ready": self.thresholds.production_ready,
                "needs_attention": self.thresholds.needs_attention,
                "iterate": self.thresholds.iterate,
            },
        }

        # Create assessment
        assessment = QualityAssessment(
            overall_score=overall_score,
            metrics=metrics,
            timestamp=datetime.now(),
            iteration=iteration,
            passed=passed,
            threshold=self.threshold,
            context=context,
            improvements_needed=improvements,
            band=band,
            metadata=metadata,
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

    # Simple convenience API expected by some tests
    def calculate_score(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """Calculate overall quality score and suggested action from dimension scores.

        Args:
            scores: Mapping of dimension name -> score (0-100)

        Returns:
            Dict with 'overall', 'grade', and 'action'.
        """
        component_scores = self._component_inputs_from_dict(scores)
        overall, _weights = self._combine_component_scores(component_scores)
        band = self.thresholds.classify(overall)

        grade_map = {
            'production_ready': 'Excellent',
            'needs_attention': 'Needs Attention',
            'iterate': 'Rework',
        }
        action_map = {
            'production_ready': 'Auto-approve',
            'needs_attention': 'Address feedback and re-run validation',
            'iterate': 'Iterate with assigned specialist agent',
        }

        return {
            'overall': round(overall, 2),
            'grade': grade_map.get(band, 'Unknown'),
            'action': action_map.get(band, 'Investigate further'),
            'band': band,
        }

    def _evaluate_correctness(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate correctness dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        # Check for errors and declared success
        declared_success = False
        if isinstance(output, dict):
            if output.get('errors'):
                score -= 30
                issues.append("Errors present in output")
                suggestions.append("Fix errors before proceeding")

            if not output.get('success', True):
                score -= 20
                issues.append("Operation not marked as successful")
            else:
                declared_success = True

        # Check for test results if available
        if 'test_results' in context:
            test_pass_rate = context['test_results'].get('pass_rate', 0)
            score = test_pass_rate * 100

        execution_evidence = self._extract_execution_evidence(output, context)
        if declared_success and not execution_evidence:
            score = min(score, 40.0)
            issues.append("Declared success without execution evidence")
            suggestions.append("Share applied diffs, commands, or test logs before claiming success")

        return QualityMetric(
            dimension=QualityDimension.CORRECTNESS,
            score=max(0, min(100, score)),
            weight=self.default_weights.get(QualityDimension.CORRECTNESS, 0.25),
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

        execution_evidence = self._extract_execution_evidence(output, context)
        planned_only = False
        if isinstance(output, dict):
            status = output.get('status', '')
            if status == 'plan-only':
                planned_only = True

            planned_actions = output.get('planned_actions') or output.get('plan')
            if planned_actions and not execution_evidence:
                planned_only = True

        if planned_only and not execution_evidence:
            score = min(score, 25.0)
            issues.append("Only a plan was produced; no concrete work verified")
            suggestions.append("Execute the plan and capture diffs/tests before re-evaluating")

        return QualityMetric(
            dimension=QualityDimension.COMPLETENESS,
            score=max(0, min(100, score)),
            weight=self.default_weights.get(QualityDimension.COMPLETENESS, 0.20),
            details="Completeness of implementation",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_scalability(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate scalability dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        scalability_ctx = context.get('scalability', {})
        if scalability_ctx:
            projected_load = scalability_ctx.get('projected_load')
            current_capacity = scalability_ctx.get('current_capacity')
            if isinstance(projected_load, (int, float)) and isinstance(current_capacity, (int, float)):
                if current_capacity < projected_load:
                    score -= 20
                    issues.append("Projected load exceeds current capacity")
                    suggestions.append("Increase capacity or introduce load balancing")
                else:
                    score += 5

            bottlenecks = scalability_ctx.get('bottlenecks', [])
            if bottlenecks:
                penalty = min(30, 10 * len(bottlenecks))
                score -= penalty
                issues.append("Scalability bottlenecks identified")
                suggestions.append("Address bottlenecks: " + ', '.join(map(str, bottlenecks)))

            strategies = scalability_ctx.get('strategies', [])
            if strategies:
                score += min(10, 3 * len(strategies))
        else:
            # Heuristic detection from output text
            if "single server" in output_str.lower() or "monolith" in output_str.lower():
                score -= 10
                issues.append("Potential single server scaling limitation")
                suggestions.append("Consider horizontal scaling or modularization")
            if any(keyword in output_str.lower() for keyword in ("autoscale", "queue", "shard", "partition")):
                score += 5

        score = max(0, min(100, score))

        return QualityMetric(
            dimension=QualityDimension.SCALABILITY,
            score=score,
            weight=self.default_weights.get(QualityDimension.SCALABILITY, 0.1),
            details="Scalability assessment from architecture and context",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_testability(self, output: Any, context: Dict[str, Any]) -> QualityMetric:
        """Evaluate testability dimension."""
        score = 65.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        test_results = context.get('test_results', {})
        if test_results:
            pass_rate = test_results.get('pass_rate')
            if pass_rate is not None:
                score = max(score, pass_rate * 100)
            tests_collected = test_results.get('tests_collected')
            if tests_collected == 0:
                score -= 25
                issues.append("No automated tests were discovered")
                suggestions.append("Add unit and integration tests for critical paths")

            coverage = test_results.get('coverage')
            if isinstance(coverage, (int, float)):
                if coverage < 0.6:
                    score -= 15
                    issues.append("Test coverage below 60%")
                    suggestions.append("Increase coverage for high-risk modules")
        else:
            if "TODO tests" in output_str.lower():
                score -= 20
                issues.append("Tests marked as TODO")
                suggestions.append("Implement pending tests before shipping")

        score = max(0, min(100, score))

        return QualityMetric(
            dimension=QualityDimension.TESTABILITY,
            score=score,
            weight=self.default_weights.get(QualityDimension.TESTABILITY, 0.1),
            details="Testability based on automated test signals",
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
            weight=self.default_weights.get(QualityDimension.MAINTAINABILITY, 0.10),
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
            weight=self.default_weights.get(QualityDimension.SECURITY, 0.10),
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
            weight=self.default_weights.get(QualityDimension.PERFORMANCE, 0.10),
            details="Performance metrics",
            issues=issues,
            suggestions=suggestions
        )

    def _evaluate_usability(
        self,
        output: Any,
        context: Dict[str, Any]
    ) -> QualityMetric:
        """Evaluate usability dimension."""
        score = 75.0  # Base score
        issues = []
        suggestions = []

        feedback = context.get('usability_feedback') or context.get('user_feedback')
        if isinstance(feedback, dict):
            score = feedback.get('satisfaction', score)
            if feedback.get('issues'):
                issues.extend(feedback['issues'])
            if feedback.get('suggestions'):
                suggestions.extend(feedback['suggestions'])

        # Accessibility hints
        if 'accessibility_issues' in context:
            acc_issues = context['accessibility_issues']
            if isinstance(acc_issues, list) and acc_issues:
                penalty = min(25, 5 * len(acc_issues))
                score -= penalty
                issues.append("Accessibility issues detected")
                suggestions.append("Resolve accessibility gaps: " + ', '.join(map(str, acc_issues)))

        output_str = str(output).lower()
        if "poor ux" in output_str or "hard to use" in output_str:
            score -= 10
            issues.append("Negative usability feedback noted")
            suggestions.append("Iterate on UX with user testing")

        score = max(0, min(100, score))

        return QualityMetric(
            dimension=QualityDimension.USABILITY,
            score=score,
            weight=self.default_weights.get(QualityDimension.USABILITY, 0.05),
            details="Usability and accessibility assessment",
            issues=issues,
            suggestions=suggestions
        )

    def _calculate_overall_score(
        self,
        metrics: List[QualityMetric],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """Calculate the blended score using weighted component signals."""

        component_scores = self._derive_component_scores(metrics, context or {})
        blended_score, normalized_weights = self._combine_component_scores(component_scores)
        metadata = {
            "components": component_scores,
            "weights": normalized_weights,
        }
        return blended_score, metadata

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

    def _derive_component_scores(
        self,
        metrics: List[QualityMetric],
        context: Dict[str, Any],
    ) -> Dict[str, Optional[float]]:
        return {
            "superclaude": self._get_metric_score(metrics, QualityDimension.CORRECTNESS),
            "completeness": self._get_metric_score(metrics, QualityDimension.COMPLETENESS),
            "test_coverage": self._derive_test_coverage(metrics, context),
        }

    def _get_metric_score(
        self,
        metrics: List[QualityMetric],
        dimension: QualityDimension,
    ) -> Optional[float]:
        for metric in metrics:
            if metric.dimension == dimension:
                try:
                    return float(metric.score)
                except (TypeError, ValueError):
                    return None
        return None

    def _derive_test_coverage(
        self,
        metrics: List[QualityMetric],
        context: Dict[str, Any],
    ) -> Optional[float]:
        metric_score = self._get_metric_score(metrics, QualityDimension.TESTABILITY)
        if metric_score is not None:
            return metric_score

        test_results = context.get("test_results") if isinstance(context, dict) else None
        if isinstance(test_results, dict):
            coverage = test_results.get("coverage")
            if coverage is None:
                coverage = test_results.get("pass_rate")
                if isinstance(coverage, (int, float)) and coverage <= 1:
                    coverage = coverage * 100
            elif isinstance(coverage, (int, float)) and coverage <= 1:
                coverage = coverage * 100

            if coverage is not None:
                try:
                    return max(0.0, min(100.0, float(coverage)))
                except (TypeError, ValueError):
                    return None

        return None

    def _combine_component_scores(
        self,
        component_scores: Dict[str, Optional[float]],
    ) -> Tuple[float, Dict[str, float]]:
        available = {key: val for key, val in component_scores.items() if val is not None}
        if not available:
            return 0.0, {}

        weight_total = sum(self.component_weights.get(key, 0.0) for key in available)
        if weight_total <= 0:
            normalized = {key: 1.0 / len(available) for key in available}
        else:
            normalized = {
                key: self.component_weights.get(key, 0.0) / weight_total
                for key in available
            }

        blended = 0.0
        for key, score in available.items():
            blended += score * normalized.get(key, 0.0)

        return blended, normalized

    def _component_inputs_from_dict(self, values: Dict[str, Any]) -> Dict[str, Optional[float]]:
        values = values or {}
        return {
            "superclaude": self._coerce_score_value(values.get("superclaude") or values.get("correctness")),
            "completeness": self._coerce_score_value(values.get("completeness")),
            "test_coverage": self._coerce_score_value(
                values.get("test_coverage")
                or values.get("tests")
                or values.get("coverage")
                or values.get("testability")
            ),
        }

    def _coerce_score_value(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, min(100.0, numeric))

    def _check_requirement_met(self, output: Any, requirement: str) -> bool:
        """Check if a requirement is met in output."""
        output_str = str(output).lower()
        requirement_lower = requirement.lower()

        # Simple keyword matching
        keywords = requirement_lower.split()
        return all(keyword in output_str for keyword in keywords)

    def _extract_execution_evidence(
        self,
        output: Any,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Collect any evidence that real work was performed.

        Args:
            output: Agent or command output
            context: Quality evaluation context

        Returns:
            List of execution evidence descriptions
        """

        def collect(value: Any, prefix: Optional[str] = None) -> List[str]:
            evidence: List[str] = []
            label = f"{prefix}: " if prefix else ""

            if isinstance(value, list):
                for item in value:
                    if item:
                        evidence.append(f"{label}{item}")
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    evidence.extend(collect(subvalue, f"{label}{subkey}" if not prefix else f"{label}{subkey}"))
            elif isinstance(value, (str, int, float)) and str(value).strip():
                evidence.append(f"{label}{value}")

            return evidence

        evidence: List[str] = []

        if isinstance(output, dict):
            for key in (
                'actions_taken',
                'executed_operations',
                'applied_changes',
                'files_modified',
                'commands_run',
                'diff_summary',
                'evidence'
            ):
                if key in output:
                    evidence.extend(collect(output[key], key))

        # Context provided evidence
        for key in (
            'evidence',
            'execution',
            'diff_summary',
            'applied_changes'
        ):
            if key in context:
                evidence.extend(collect(context[key], key))

        test_results = context.get('test_results', {})
        if isinstance(test_results, dict):
            passed = test_results.get('passed')
            pass_rate = test_results.get('pass_rate')
            if passed:
                evidence.append("tests: suite passed")
            if isinstance(pass_rate, (int, float)) and pass_rate > 0:
                evidence.append(f"tests: pass rate {pass_rate * 100:.0f}%")

        # Remove duplicates while keeping order
        seen = set()
        unique_evidence = []
        for item in evidence:
            if item not in seen:
                seen.add(item)
                unique_evidence.append(item)

        return unique_evidence

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
