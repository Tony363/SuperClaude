"""
Quality Scoring System for SuperClaude Framework

Implements quality evaluation and the agentic loop pattern for
automatic iteration until quality thresholds are met.
"""

import logging
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

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
    PAL_REVIEW = "pal_review"


@dataclass
class QualityMetric:
    """Individual quality metric."""

    dimension: QualityDimension
    score: float  # 0-100
    weight: float  # Importance weight
    details: str
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class QualityAssessment:
    """Complete quality assessment."""

    overall_score: float  # 0-100
    metrics: list[QualityMetric]
    timestamp: datetime
    iteration: int
    passed: bool
    threshold: float
    context: dict[str, Any]
    improvements_needed: list[str] = field(default_factory=list)
    band: str = "iterate"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IterationResult:
    """Result of an agentic loop iteration."""

    iteration: int
    input_quality: float
    output_quality: float
    improvements_applied: list[str]
    time_taken: float
    success: bool
    termination_reason: str = ""  # Why the loop stopped


class IterationTermination:
    """Constants for iteration termination reasons."""

    QUALITY_MET = "quality_threshold_met"
    MAX_ITERATIONS = "max_iterations_reached"
    INSUFFICIENT_IMPROVEMENT = "insufficient_improvement"
    STAGNATION = "score_stagnation"
    OSCILLATION = "score_oscillation"
    ERROR = "improver_error"
    HUMAN_ESCALATION = "requires_human_review"
    TIMEOUT = "timeout"  # Wall-clock timeout exceeded


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


@dataclass
class DeterministicSignals:
    """
    P1: Deterministic signals that ground quality scoring in verifiable facts.

    These signals come from actual tool execution (tests, linters, builds)
    rather than LLM self-evaluation, providing trustworthy quality gates.
    """

    # Test results
    tests_passed: bool = False
    tests_total: int = 0
    tests_failed: int = 0
    test_coverage: float = 0.0  # 0-100

    # Lint/type check results
    lint_passed: bool = False
    lint_errors: int = 0
    lint_warnings: int = 0
    type_check_passed: bool = False
    type_errors: int = 0

    # Build results
    build_passed: bool = False
    build_errors: int = 0

    # Security scan
    security_passed: bool = False
    security_critical: int = 0
    security_high: int = 0

    def has_hard_failures(self) -> bool:
        """Check for any hard failures that should cap the score."""
        return (
            self.tests_failed > 0
            or self.security_critical > 0
            or (not self.build_passed and self.build_errors > 0)
        )

    def get_hard_failure_cap(self) -> float:
        """
        Get the maximum score allowed given hard failures.

        P1 SAFETY: Prevents high scores when critical issues exist.
        """
        if self.security_critical > 0:
            return 30.0  # Critical security = very low cap
        if self.tests_failed > 0:
            # More tests failed = lower cap
            if self.tests_total > 0:
                fail_rate = self.tests_failed / self.tests_total
                if fail_rate > 0.5:
                    return 40.0
                elif fail_rate > 0.2:
                    return 50.0
                else:
                    return 60.0
            return 50.0
        if not self.build_passed and self.build_errors > 0:
            return 45.0
        if self.security_high > 0:
            return 65.0

        return 100.0  # No cap

    def calculate_bonus(self) -> float:
        """
        Calculate bonus points from positive signals.

        Clean lints, passing tests, and good coverage earn bonus points.
        """
        bonus = 0.0

        # Test coverage bonus (up to 10 points)
        if self.test_coverage >= 80:
            bonus += 10.0
        elif self.test_coverage >= 60:
            bonus += 5.0
        elif self.test_coverage >= 40:
            bonus += 2.0

        # Clean lint bonus
        if self.lint_passed and self.lint_errors == 0:
            bonus += 5.0

        # Type check bonus
        if self.type_check_passed and self.type_errors == 0:
            bonus += 5.0

        # All tests passing bonus
        if self.tests_passed and self.tests_failed == 0 and self.tests_total > 0:
            bonus += 5.0

        # Security clean bonus
        if self.security_passed:
            bonus += 5.0

        return min(bonus, 25.0)  # Cap total bonus


class QualityScorer:
    """
    Evaluates output quality and manages the agentic loop pattern.

    Automatically iterates on outputs until quality thresholds are met
    or maximum iterations are reached.
    """

    # Configuration constants
    DEFAULT_THRESHOLD = 70.0  # Minimum acceptable quality score
    MAX_ITERATIONS = (
        3  # Maximum improvement iterations (P0 safety: prevent infinite loops)
    )
    MIN_IMPROVEMENT = 5.0  # Minimum score improvement to continue
    HARD_MAX_ITERATIONS = 5  # Absolute ceiling, cannot be overridden
    OSCILLATION_WINDOW = 3  # Number of scores to check for oscillation
    STAGNATION_THRESHOLD = 2.0  # Score difference below which is considered stagnation

    def __init__(
        self, threshold: float = DEFAULT_THRESHOLD, config_path: str | None = None
    ):
        """
        Initialize the quality scorer.

        Args:
            threshold: Minimum acceptable quality score (0-100)
        """
        self.logger = logging.getLogger(__name__)
        self.threshold = threshold
        self.config_path = (
            Path(config_path)
            if config_path
            else Path(__file__).resolve().parent.parent / "Config" / "quality.yaml"
        )
        self.config_data: dict[str, Any] = {}

        # Quality evaluators by dimension
        self.evaluators: dict[QualityDimension, Callable] = {
            QualityDimension.CORRECTNESS: self._evaluate_correctness,
            QualityDimension.COMPLETENESS: self._evaluate_completeness,
            QualityDimension.MAINTAINABILITY: self._evaluate_maintainability,
            QualityDimension.SECURITY: self._evaluate_security,
            QualityDimension.PERFORMANCE: self._evaluate_performance,
            QualityDimension.SCALABILITY: self._evaluate_scalability,
            QualityDimension.TESTABILITY: self._evaluate_testability,
            QualityDimension.USABILITY: self._evaluate_usability,
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
            QualityDimension.USABILITY: 0.05,
            QualityDimension.PAL_REVIEW: 0.10,
        }

        self._load_configuration()
        override_threshold = threshold if threshold != self.DEFAULT_THRESHOLD else None
        self.component_weights = self._load_component_weights()
        self.thresholds = self._load_thresholds(override_threshold)
        if override_threshold is None:
            self.threshold = self.thresholds.production_ready

        # Iteration history
        self.iteration_history: list[IterationResult] = []
        self.assessment_history: list[QualityAssessment] = []

        # Custom evaluators
        self.custom_evaluators: list[Callable] = []
        self.primary_evaluator: (
            Callable[[Any, dict[str, Any], int], dict[str, Any] | None] | None
        ) = None

    def _load_configuration(self) -> None:
        """Load quality configuration from YAML if available."""
        if not self.config_path.exists():
            self.logger.debug(f"Quality config not found at {self.config_path}")
            return

        if yaml is None:
            self.logger.debug("PyYAML not installed; skipping quality config load")
            return

        try:
            with open(self.config_path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:
            self.logger.warning(
                f"Failed to read quality config {self.config_path}: {exc}"
            )
            return

        self.config_data = data

        # Update weights based on configuration
        dimensions_cfg = data.get("dimensions", {})
        for dim_name, dim_config in dimensions_cfg.items():
            try:
                dimension = QualityDimension(dim_name)
            except ValueError:
                self.logger.debug(
                    f"Ignoring unknown quality dimension '{dim_name}' from config"
                )
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

    def _load_component_weights(self) -> dict[str, float]:
        weights = DEFAULT_COMPONENT_WEIGHTS.copy()
        config_weights: dict[str, Any] = {}
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

    def _load_thresholds(self, override_threshold: float | None) -> QualityThresholds:
        scoring_cfg = self.config_data.get("scoring", {}) if self.config_data else {}
        thresholds_cfg = (
            scoring_cfg.get("thresholds", {}) if isinstance(scoring_cfg, dict) else {}
        )

        def _coerce(keys: Sequence[str], default: float) -> float:
            for key in keys:
                if key in thresholds_cfg:
                    try:
                        return float(thresholds_cfg[key])
                    except (TypeError, ValueError):
                        continue
            return default

        thresholds = QualityThresholds(
            production_ready=_coerce(
                ["production_ready", "excellent", "production"], 90.0
            ),
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
        context: dict[str, Any],
        dimensions: list[QualityDimension] | None = None,
        weights: dict[QualityDimension, float] | None = None,
        iteration: int = 0,
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
        metrics: list[QualityMetric] = []
        improvements_override: list[str] | None = None
        metadata_overrides: dict[str, Any] = {}

        primary_payload: dict[str, Any] | None = None
        if self.primary_evaluator:
            try:
                primary_payload = self.primary_evaluator(output, context, iteration)
            except Exception as exc:
                self.logger.error(f"Primary evaluator error: {exc}")
                primary_payload = None

        if primary_payload and primary_payload.get("metrics"):
            metrics.extend(primary_payload.get("metrics", []))
            improvements_override = primary_payload.get("improvements")
            metadata_overrides = primary_payload.get("metadata") or {}
        else:
            # Select dimensions to evaluate
            if dimensions is None:
                dimensions = list(self.default_weights.keys())

            # Use custom weights or defaults
            eval_weights = weights or self.default_weights

            # Evaluate each dimension
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
        if improvements_override is not None:
            improvements = improvements_override
        else:
            improvements = self._identify_improvements(metrics, overall_score)

        metadata = {
            **score_metadata,
            "thresholds": {
                "production_ready": self.thresholds.production_ready,
                "needs_attention": self.thresholds.needs_attention,
                "iterate": self.thresholds.iterate,
            },
        }
        if metadata_overrides:
            metadata.update(metadata_overrides)

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
        context: dict[str, Any],
        improver_func: Callable,
        max_iterations: int | None = None,
        min_improvement: float | None = None,
        timeout_seconds: float | None = None,
        time_provider: Callable[[], float] | None = None,
    ) -> tuple[Any, QualityAssessment, list[IterationResult]]:
        """
        Run agentic loop to iteratively improve output quality.

        SAFETY FEATURES (P0):
        - Hard max iteration cap (HARD_MAX_ITERATIONS) cannot be overridden
        - Oscillation detection prevents infinite back-and-forth
        - Stagnation detection stops when no meaningful progress
        - Wall-clock timeout (best-effort, cannot interrupt running calls)
        - All termination reasons are logged for debugging

        Args:
            initial_output: Initial output to improve
            context: Execution context
            improver_func: Function to improve output
            max_iterations: Maximum iterations (default: MAX_ITERATIONS, capped at HARD_MAX_ITERATIONS)
            min_improvement: Minimum improvement to continue (default: MIN_IMPROVEMENT)
            timeout_seconds: Wall-clock timeout in seconds (best-effort, see note below)
            time_provider: Callable returning monotonic time (default: time.monotonic).
                          Inject for deterministic testing.

        Returns:
            Tuple of (final_output, final_assessment, iteration_history)

        Note:
            Wall-clock timeout is best-effort. The loop will not start new iterations
            after the budget is exceeded, but cannot interrupt a running evaluate()
            or improver_func() call. Overall wall time may exceed timeout_seconds if
            those calls run long.
        """
        # P0 SAFETY: Enforce hard maximum - never exceed this regardless of input
        requested_max = max_iterations or self.MAX_ITERATIONS
        max_iter = min(requested_max, self.HARD_MAX_ITERATIONS)
        if requested_max > self.HARD_MAX_ITERATIONS:
            self.logger.warning(
                f"Requested max_iterations={requested_max} exceeds hard limit "
                f"{self.HARD_MAX_ITERATIONS}, capping to prevent infinite loops"
            )

        min_improv = min_improvement or self.MIN_IMPROVEMENT

        # Timeout setup
        _time = time_provider or time.monotonic
        loop_start = _time()
        deadline = loop_start + timeout_seconds if timeout_seconds else None

        def timed_out() -> bool:
            """Check if wall-clock timeout exceeded."""
            return deadline is not None and _time() >= deadline

        current_output = initial_output
        iteration_results: list[IterationResult] = []
        previous_score = 0.0
        score_history: list[float] = []  # Track scores for oscillation detection
        termination_reason = (
            IterationTermination.MAX_ITERATIONS
        )  # Default if loop completes
        last_assessment: QualityAssessment | None = None  # Track for timeout case

        for iteration in range(max_iter):
            iter_start_time = datetime.now()

            # TIMEOUT CHECK 1: Before starting iteration
            if timed_out():
                termination_reason = IterationTermination.TIMEOUT
                self.logger.warning(
                    f"Timeout at start of iteration {iteration}: "
                    f"elapsed={_time() - loop_start:.1f}s, limit={timeout_seconds}s"
                )
                # Don't record this as a completed iteration
                break

            # Evaluate current quality
            assessment = self.evaluate(current_output, context, iteration=iteration)
            last_assessment = assessment  # Track for potential timeout
            current_score = assessment.overall_score
            score_history.append(current_score)

            # TIMEOUT CHECK 2: After scoring (scoring might be slow)
            if timed_out():
                termination_reason = IterationTermination.TIMEOUT
                self.logger.warning(
                    f"Timeout after scoring iteration {iteration}: "
                    f"score={current_score:.1f}, elapsed={_time() - loop_start:.1f}s"
                )
                # Record this as a completed iteration (we did score it)
                result = IterationResult(
                    iteration=iteration,
                    input_quality=previous_score,
                    output_quality=current_score,
                    improvements_applied=[],
                    time_taken=(datetime.now() - iter_start_time).total_seconds(),
                    success=False,
                    termination_reason=termination_reason,
                )
                iteration_results.append(result)
                break

            # Check if quality threshold is met
            if assessment.passed:
                termination_reason = IterationTermination.QUALITY_MET
                self.logger.info(
                    f"Quality threshold met at iteration {iteration}: {current_score:.1f}"
                )
                result = IterationResult(
                    iteration=iteration,
                    input_quality=previous_score,
                    output_quality=current_score,
                    improvements_applied=[],
                    time_taken=(datetime.now() - iter_start_time).total_seconds(),
                    success=True,
                    termination_reason=termination_reason,
                )
                iteration_results.append(result)
                break

            # P0 SAFETY: Check for oscillation (scores alternating up/down)
            if self._detect_oscillation(score_history):
                termination_reason = IterationTermination.OSCILLATION
                self.logger.warning(
                    f"Score oscillation detected at iteration {iteration}: {score_history[-3:]}"
                )
                result = IterationResult(
                    iteration=iteration,
                    input_quality=previous_score,
                    output_quality=current_score,
                    improvements_applied=[],
                    time_taken=(datetime.now() - iter_start_time).total_seconds(),
                    success=False,
                    termination_reason=termination_reason,
                )
                iteration_results.append(result)
                break

            # P0 SAFETY: Check for stagnation (scores not changing meaningfully)
            if self._detect_stagnation(score_history):
                termination_reason = IterationTermination.STAGNATION
                self.logger.warning(
                    f"Score stagnation detected at iteration {iteration}: {score_history[-3:]}"
                )
                result = IterationResult(
                    iteration=iteration,
                    input_quality=previous_score,
                    output_quality=current_score,
                    improvements_applied=[],
                    time_taken=(datetime.now() - iter_start_time).total_seconds(),
                    success=False,
                    termination_reason=termination_reason,
                )
                iteration_results.append(result)
                break

            # Check if improvement is sufficient
            if iteration > 0:
                improvement = current_score - previous_score
                if improvement < min_improv:
                    termination_reason = IterationTermination.INSUFFICIENT_IMPROVEMENT
                    self.logger.info(
                        f"Insufficient improvement ({improvement:.1f}) at iteration {iteration}"
                    )
                    result = IterationResult(
                        iteration=iteration,
                        input_quality=previous_score,
                        output_quality=current_score,
                        improvements_applied=[],
                        time_taken=(datetime.now() - iter_start_time).total_seconds(),
                        success=False,
                        termination_reason=termination_reason,
                    )
                    iteration_results.append(result)
                    break

            # Apply improvements
            improvements_context = {
                **context,
                "quality_assessment": assessment,
                "improvements_needed": assessment.improvements_needed,
                "current_score": current_score,
                "target_score": self.threshold,
                "iteration": iteration,
                "max_iterations": max_iter,
                "remaining_iterations": max_iter - iteration - 1,
            }

            try:
                improved_output = improver_func(current_output, improvements_context)

                # TIMEOUT CHECK 3: After improver returns, before overwriting
                if timed_out():
                    termination_reason = IterationTermination.TIMEOUT
                    self.logger.warning(
                        f"Timeout after improver at iteration {iteration}: "
                        f"elapsed={_time() - loop_start:.1f}s"
                    )
                    # Record iteration but DON'T use improved_output
                    # Return current_output (last safe state)
                    result = IterationResult(
                        iteration=iteration,
                        input_quality=current_score,
                        output_quality=current_score,  # Use current, not improved
                        improvements_applied=assessment.improvements_needed[:5],
                        time_taken=(datetime.now() - iter_start_time).total_seconds(),
                        success=False,
                        termination_reason=termination_reason,
                    )
                    iteration_results.append(result)
                    break

                result = IterationResult(
                    iteration=iteration,
                    input_quality=current_score,
                    output_quality=0.0,  # Will be updated in next iteration
                    improvements_applied=assessment.improvements_needed[:5],  # Top 5
                    time_taken=(datetime.now() - iter_start_time).total_seconds(),
                    success=False,
                    termination_reason="",
                )
                iteration_results.append(result)

                current_output = improved_output
                previous_score = current_score

            except Exception as e:
                termination_reason = IterationTermination.ERROR
                self.logger.error(f"Improvement function error: {e}")
                result = IterationResult(
                    iteration=iteration,
                    input_quality=current_score,
                    output_quality=current_score,
                    improvements_applied=[],
                    time_taken=(datetime.now() - iter_start_time).total_seconds(),
                    success=False,
                    termination_reason=termination_reason,
                )
                iteration_results.append(result)
                break

        # Final evaluation
        final_assessment = self.evaluate(
            current_output, context, iteration=len(iteration_results)
        )

        # Update last iteration result with final info
        if iteration_results:
            iteration_results[-1].output_quality = final_assessment.overall_score
            iteration_results[-1].success = final_assessment.passed
            if not iteration_results[-1].termination_reason:
                iteration_results[-1].termination_reason = termination_reason

        # Log summary for debugging
        self.logger.info(
            f"Agentic loop completed: {len(iteration_results)} iterations, "
            f"final_score={final_assessment.overall_score:.1f}, "
            f"passed={final_assessment.passed}, "
            f"reason={termination_reason}"
        )

        # Store iteration history
        self.iteration_history.extend(iteration_results)

        return current_output, final_assessment, iteration_results

    def _detect_oscillation(self, score_history: list[float]) -> bool:
        """
        Detect if scores are oscillating (alternating up/down).

        This prevents infinite loops where the model keeps switching
        between two approaches without converging.
        """
        if len(score_history) < self.OSCILLATION_WINDOW:
            return False

        # Check last N scores for alternating pattern
        recent = score_history[-self.OSCILLATION_WINDOW :]
        directions = []
        for i in range(1, len(recent)):
            diff = recent[i] - recent[i - 1]
            if abs(diff) > self.STAGNATION_THRESHOLD:
                directions.append(1 if diff > 0 else -1)

        # Oscillation = alternating directions (e.g., [1, -1, 1] or [-1, 1, -1])
        if len(directions) >= 2:
            alternating = all(
                directions[i] != directions[i + 1] for i in range(len(directions) - 1)
            )
            return alternating

        return False

    def _detect_stagnation(self, score_history: list[float]) -> bool:
        """
        Detect if scores have stagnated (not changing meaningfully).

        This prevents wasting tokens on iterations that aren't improving.
        """
        if len(score_history) < self.OSCILLATION_WINDOW:
            return False

        # Check if all recent scores are within STAGNATION_THRESHOLD of each other
        recent = score_history[-self.OSCILLATION_WINDOW :]
        min_score = min(recent)
        max_score = max(recent)

        return (max_score - min_score) < self.STAGNATION_THRESHOLD

    def add_custom_evaluator(self, evaluator: Callable):
        """
        Add custom quality evaluator.

        Args:
            evaluator: Function that returns QualityMetric
        """
        self.custom_evaluators.append(evaluator)

    def apply_deterministic_signals(
        self, base_score: float, signals: DeterministicSignals
    ) -> tuple[float, dict[str, Any]]:
        """
        Apply deterministic signals to adjust the quality score.

        P1 SAFETY: Grounds LLM-based scoring in verifiable facts.
        Hard failures from tests/build/security cap the maximum score.
        Positive signals (coverage, clean lint) add bonus points.

        Args:
            base_score: The base quality score (0-100)
            signals: Deterministic signals from tool execution

        Returns:
            Tuple of (adjusted_score, adjustment_details)
        """
        details: dict[str, Any] = {
            "base_score": base_score,
            "signals_applied": True,
            "hard_failures": [],
            "bonuses": [],
        }

        adjusted_score = base_score

        # Apply hard failure cap (P1: tests/build/security gate the score)
        if signals.has_hard_failures():
            cap = signals.get_hard_failure_cap()
            if adjusted_score > cap:
                details["hard_failure_cap"] = cap
                details["score_before_cap"] = adjusted_score

                if signals.security_critical > 0:
                    details["hard_failures"].append(
                        f"Critical security issues: {signals.security_critical}"
                    )
                if signals.tests_failed > 0:
                    details["hard_failures"].append(
                        f"Failing tests: {signals.tests_failed}/{signals.tests_total}"
                    )
                if not signals.build_passed and signals.build_errors > 0:
                    details["hard_failures"].append(
                        f"Build failures: {signals.build_errors}"
                    )
                if signals.security_high > 0:
                    details["hard_failures"].append(
                        f"High severity security issues: {signals.security_high}"
                    )

                adjusted_score = cap
                self.logger.warning(
                    f"Score capped from {base_score:.1f} to {cap:.1f} due to hard failures: "
                    f"{', '.join(details['hard_failures'])}"
                )

        # Apply bonus for positive signals
        bonus = signals.calculate_bonus()
        if bonus > 0:
            details["bonus_applied"] = bonus

            if signals.test_coverage >= 80:
                details["bonuses"].append(
                    f"High test coverage: {signals.test_coverage:.0f}%"
                )
            if signals.lint_passed:
                details["bonuses"].append("Clean lint")
            if signals.type_check_passed:
                details["bonuses"].append("Clean type check")
            if signals.tests_passed and signals.tests_total > 0:
                details["bonuses"].append(f"All {signals.tests_total} tests passing")
            if signals.security_passed:
                details["bonuses"].append("Security scan passed")

            # Only apply bonus if no hard failures
            if not signals.has_hard_failures():
                adjusted_score = min(100.0, adjusted_score + bonus)

        details["final_score"] = adjusted_score
        details["adjustment"] = adjusted_score - base_score

        return adjusted_score, details

    def evaluate_with_signals(
        self,
        output: Any,
        context: dict[str, Any],
        signals: DeterministicSignals,
        dimensions: list[QualityDimension] | None = None,
        weights: dict[QualityDimension, float] | None = None,
        iteration: int = 0,
    ) -> QualityAssessment:
        """
        Evaluate output quality with deterministic signal grounding.

        P1 SAFETY: Combines LLM-based evaluation with hard facts from
        actual tool execution (tests, linters, builds, security scans).

        Args:
            output: Output to evaluate
            context: Evaluation context
            signals: Deterministic signals from tool execution
            dimensions: Specific dimensions to evaluate
            weights: Custom dimension weights
            iteration: Current iteration number

        Returns:
            Quality assessment with deterministic adjustments
        """
        # First, get the base evaluation
        assessment = self.evaluate(output, context, dimensions, weights, iteration)

        # Apply deterministic signals
        adjusted_score, signal_details = self.apply_deterministic_signals(
            assessment.overall_score, signals
        )

        # Update assessment with adjusted score
        assessment.overall_score = adjusted_score
        assessment.passed = adjusted_score >= self.thresholds.production_ready
        assessment.band = self.thresholds.classify(adjusted_score)

        # Add signal details to metadata
        assessment.metadata["deterministic_signals"] = signal_details
        assessment.metadata["signals_grounded"] = True

        # Add any hard failure reasons to improvements_needed
        if signal_details.get("hard_failures"):
            for failure in signal_details["hard_failures"]:
                if failure not in assessment.improvements_needed:
                    assessment.improvements_needed.insert(0, f"FIX: {failure}")

        return assessment

    @staticmethod
    def signals_from_context(context: dict[str, Any]) -> DeterministicSignals:
        """
        Extract deterministic signals from a context dictionary.

        Convenience method for building signals from typical context format.

        Args:
            context: Context dictionary with test_results, lint_results, etc.

        Returns:
            DeterministicSignals instance
        """
        signals = DeterministicSignals()

        # Extract test results
        test_results = context.get("test_results", {})
        if test_results:
            signals.tests_total = test_results.get("total", 0)
            signals.tests_failed = test_results.get("failed", 0)
            signals.tests_passed = (
                test_results.get("passed", False) or signals.tests_failed == 0
            )
            coverage = test_results.get("coverage", 0)
            if isinstance(coverage, (int, float)):
                signals.test_coverage = coverage * 100 if coverage <= 1 else coverage

        # Extract lint results
        lint_results = context.get("lint_results", {})
        if lint_results:
            signals.lint_passed = lint_results.get("passed", False)
            signals.lint_errors = lint_results.get("errors", 0)
            signals.lint_warnings = lint_results.get("warnings", 0)

        # Extract type check results
        type_results = context.get("type_check_results", {})
        if type_results:
            signals.type_check_passed = type_results.get("passed", False)
            signals.type_errors = type_results.get("errors", 0)

        # Extract build results
        build_results = context.get("build_results", {})
        if build_results:
            signals.build_passed = build_results.get("passed", False)
            signals.build_errors = build_results.get("errors", 0)

        # Extract security results
        security_results = context.get("security_scan", {}) or context.get(
            "security_results", {}
        )
        if security_results:
            signals.security_passed = security_results.get("passed", False)
            signals.security_critical = security_results.get("critical", 0)
            signals.security_high = security_results.get("high", 0)

        return signals

    def set_primary_evaluator(
        self, evaluator: Callable[[Any, dict[str, Any], int], dict[str, Any] | None]
    ) -> None:
        """Set a callable that supplies the primary metrics for evaluation."""
        self.primary_evaluator = evaluator

    def clear_primary_evaluator(self) -> None:
        """Remove the active primary evaluator (if any)."""
        self.primary_evaluator = None

    def get_improvement_suggestions(
        self, assessment: QualityAssessment
    ) -> list[dict[str, Any]]:
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
                    suggestions.append(
                        {
                            "dimension": metric.dimension.value,
                            "current_score": metric.score,
                            "suggestion": suggestion,
                            "priority": "high" if metric.score < 50 else "medium",
                            "impact": metric.weight * (100 - metric.score),
                        }
                    )

        # Sort by impact
        suggestions.sort(key=lambda x: x["impact"], reverse=True)

        return suggestions

    def get_metrics_summary(self) -> dict[str, Any]:
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
            "total_assessments": len(self.assessment_history),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "pass_rate": len(passed) / len(self.assessment_history),
            "total_iterations": sum(r.iteration for r in self.iteration_history),
            "average_iterations": (
                sum(r.iteration for r in self.iteration_history)
                / len(self.iteration_history)
                if self.iteration_history
                else 0
            ),
        }

    # Simple convenience API expected by some tests
    def calculate_score(self, scores: dict[str, float]) -> dict[str, Any]:
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
            "production_ready": "Excellent",
            "needs_attention": "Needs Attention",
            "iterate": "Rework",
        }
        action_map = {
            "production_ready": "Auto-approve",
            "needs_attention": "Address feedback and re-run validation",
            "iterate": "Iterate with assigned specialist agent",
        }

        return {
            "overall": round(overall, 2),
            "grade": grade_map.get(band, "Unknown"),
            "action": action_map.get(band, "Investigate further"),
            "band": band,
        }

    def _evaluate_correctness(
        self, output: Any, context: dict[str, Any]
    ) -> QualityMetric:
        """Evaluate correctness dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        # Check for errors and declared success
        declared_success = False
        if isinstance(output, dict):
            if output.get("errors"):
                score -= 30
                issues.append("Errors present in output")
                suggestions.append("Fix errors before proceeding")

            if not output.get("success", True):
                score -= 20
                issues.append("Operation not marked as successful")
            else:
                declared_success = True

        # Check for test results if available
        if "test_results" in context:
            test_pass_rate = context["test_results"].get("pass_rate", 0)
            score = test_pass_rate * 100

        execution_evidence = self._extract_execution_evidence(output, context)
        if declared_success and not execution_evidence:
            score = min(score, 40.0)
            issues.append("Declared success without execution evidence")
            suggestions.append(
                "Share applied diffs, commands, or test logs before claiming success"
            )

        return QualityMetric(
            dimension=QualityDimension.CORRECTNESS,
            score=max(0, min(100, score)),
            weight=self.default_weights.get(QualityDimension.CORRECTNESS, 0.25),
            details="Correctness based on errors and test results",
            issues=issues,
            suggestions=suggestions,
        )

    def _evaluate_completeness(
        self, output: Any, context: dict[str, Any]
    ) -> QualityMetric:
        """Evaluate completeness dimension."""
        score = 80.0  # Base score
        issues = []
        suggestions = []

        # Check for required fields
        if "requirements" in context:
            requirements = context["requirements"]
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
        if "TODO" in output_str or "FIXME" in output_str:
            score -= 20
            issues.append("Contains TODO/FIXME comments")
            suggestions.append("Complete all TODO items")

        execution_evidence = self._extract_execution_evidence(output, context)
        planned_only = False
        if isinstance(output, dict):
            status = output.get("status", "")
            if status == "plan-only":
                planned_only = True

            planned_actions = output.get("planned_actions") or output.get("plan")
            if planned_actions and not execution_evidence:
                planned_only = True

        if planned_only and not execution_evidence:
            score = min(score, 25.0)
            issues.append("Only a plan was produced; no concrete work verified")
            suggestions.append(
                "Execute the plan and capture diffs/tests before re-evaluating"
            )

        return QualityMetric(
            dimension=QualityDimension.COMPLETENESS,
            score=max(0, min(100, score)),
            weight=self.default_weights.get(QualityDimension.COMPLETENESS, 0.20),
            details="Completeness of implementation",
            issues=issues,
            suggestions=suggestions,
        )

    def _evaluate_scalability(
        self, output: Any, context: dict[str, Any]
    ) -> QualityMetric:
        """Evaluate scalability dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        scalability_ctx = context.get("scalability", {})
        if scalability_ctx:
            projected_load = scalability_ctx.get("projected_load")
            current_capacity = scalability_ctx.get("current_capacity")
            if isinstance(projected_load, (int, float)) and isinstance(
                current_capacity, (int, float)
            ):
                if current_capacity < projected_load:
                    score -= 20
                    issues.append("Projected load exceeds current capacity")
                    suggestions.append("Increase capacity or introduce load balancing")
                else:
                    score += 5

            bottlenecks = scalability_ctx.get("bottlenecks", [])
            if bottlenecks:
                penalty = min(30, 10 * len(bottlenecks))
                score -= penalty
                issues.append("Scalability bottlenecks identified")
                suggestions.append(
                    "Address bottlenecks: " + ", ".join(map(str, bottlenecks))
                )

            strategies = scalability_ctx.get("strategies", [])
            if strategies:
                score += min(10, 3 * len(strategies))
        else:
            # Heuristic detection from output text
            if (
                "single server" in output_str.lower()
                or "monolith" in output_str.lower()
            ):
                score -= 10
                issues.append("Potential single server scaling limitation")
                suggestions.append("Consider horizontal scaling or modularization")
            if any(
                keyword in output_str.lower()
                for keyword in ("autoscale", "queue", "shard", "partition")
            ):
                score += 5

        score = max(0, min(100, score))

        return QualityMetric(
            dimension=QualityDimension.SCALABILITY,
            score=score,
            weight=self.default_weights.get(QualityDimension.SCALABILITY, 0.1),
            details="Scalability assessment from architecture and context",
            issues=issues,
            suggestions=suggestions,
        )

    def _evaluate_testability(
        self, output: Any, context: dict[str, Any]
    ) -> QualityMetric:
        """Evaluate testability dimension."""
        score = 65.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        test_results = context.get("test_results", {})
        if test_results:
            pass_rate = test_results.get("pass_rate")
            if pass_rate is not None:
                score = max(score, pass_rate * 100)
            tests_collected = test_results.get("tests_collected")
            if tests_collected == 0:
                score -= 25
                issues.append("No automated tests were discovered")
                suggestions.append("Add unit and integration tests for critical paths")

            coverage = test_results.get("coverage")
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
            suggestions=suggestions,
        )

    def _evaluate_maintainability(
        self, output: Any, context: dict[str, Any]
    ) -> QualityMetric:
        """Evaluate maintainability dimension."""
        score = 75.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        # Check complexity
        if isinstance(output, dict) and "code" in output:
            code = output["code"]
            lines = code.split("\n")

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
            suggestions=suggestions,
        )

    def _evaluate_security(self, output: Any, context: dict[str, Any]) -> QualityMetric:
        """Evaluate security dimension."""
        score = 80.0  # Base score
        issues = []
        suggestions = []

        output_str = str(output)

        # Check for common security issues
        security_patterns = [
            (r"eval\(", "Use of eval() is dangerous", 20),
            (r"exec\(", "Use of exec() is dangerous", 20),
            (r"pickle\.loads", "Unsafe deserialization", 15),
            (r"os\.system", "Direct system calls", 15),
            (r'password\s*=\s*["\']', "Hardcoded password", 25),
        ]

        for pattern, issue, penalty in security_patterns:
            if re.search(pattern, output_str, re.IGNORECASE):
                score -= penalty
                issues.append(issue)
                suggestions.append(f"Fix security issue: {issue}")

        # Check for input validation
        if "user_input" in output_str and "validate" not in output_str:
            score -= 10
            issues.append("No input validation")
            suggestions.append("Add input validation")

        return QualityMetric(
            dimension=QualityDimension.SECURITY,
            score=max(0, min(100, score)),
            weight=self.default_weights.get(QualityDimension.SECURITY, 0.10),
            details="Security assessment",
            issues=issues,
            suggestions=suggestions,
        )

    def _evaluate_performance(
        self, output: Any, context: dict[str, Any]
    ) -> QualityMetric:
        """Evaluate performance dimension."""
        score = 70.0  # Base score
        issues = []
        suggestions = []

        # Check performance metrics if available
        if "metrics" in context:
            metrics = context["metrics"]

            # Response time
            if metrics.get("response_time", 0) > 1000:  # >1s
                score -= 20
                issues.append("High response time")
                suggestions.append("Optimize response time")

            # Memory usage
            if metrics.get("memory_mb", 0) > 500:  # >500MB
                score -= 15
                issues.append("High memory usage")
                suggestions.append("Reduce memory footprint")

        return QualityMetric(
            dimension=QualityDimension.PERFORMANCE,
            score=max(0, min(100, score)),
            weight=self.default_weights.get(QualityDimension.PERFORMANCE, 0.10),
            details="Performance metrics",
            issues=issues,
            suggestions=suggestions,
        )

    def _evaluate_usability(
        self, output: Any, context: dict[str, Any]
    ) -> QualityMetric:
        """Evaluate usability dimension."""
        score = 75.0  # Base score
        issues = []
        suggestions = []

        feedback = context.get("usability_feedback") or context.get("user_feedback")
        if isinstance(feedback, dict):
            score = feedback.get("satisfaction", score)
            if feedback.get("issues"):
                issues.extend(feedback["issues"])
            if feedback.get("suggestions"):
                suggestions.extend(feedback["suggestions"])

        # Accessibility hints
        if "accessibility_issues" in context:
            acc_issues = context["accessibility_issues"]
            if isinstance(acc_issues, list) and acc_issues:
                penalty = min(25, 5 * len(acc_issues))
                score -= penalty
                issues.append("Accessibility issues detected")
                suggestions.append(
                    "Resolve accessibility gaps: " + ", ".join(map(str, acc_issues))
                )

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
            suggestions=suggestions,
        )

    def _calculate_overall_score(
        self,
        metrics: list[QualityMetric],
        context: dict[str, Any] | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Calculate the blended score using weighted component signals."""

        component_scores = self._derive_component_scores(metrics, context or {})
        blended_score, normalized_weights = self._combine_component_scores(
            component_scores
        )
        metadata = {
            "components": component_scores,
            "weights": normalized_weights,
        }
        return blended_score, metadata

    def _identify_improvements(
        self, metrics: list[QualityMetric], overall_score: float
    ) -> list[str]:
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
        metrics: list[QualityMetric],
        context: dict[str, Any],
    ) -> dict[str, float | None]:
        return {
            "superclaude": self._get_metric_score(
                metrics, QualityDimension.CORRECTNESS
            ),
            "completeness": self._get_metric_score(
                metrics, QualityDimension.COMPLETENESS
            ),
            "test_coverage": self._derive_test_coverage(metrics, context),
        }

    def _get_metric_score(
        self,
        metrics: list[QualityMetric],
        dimension: QualityDimension,
    ) -> float | None:
        for metric in metrics:
            if metric.dimension == dimension:
                try:
                    return float(metric.score)
                except (TypeError, ValueError):
                    return None
        return None

    def _derive_test_coverage(
        self,
        metrics: list[QualityMetric],
        context: dict[str, Any],
    ) -> float | None:
        metric_score = self._get_metric_score(metrics, QualityDimension.TESTABILITY)
        if metric_score is not None:
            return metric_score

        test_results = (
            context.get("test_results") if isinstance(context, dict) else None
        )
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
        component_scores: dict[str, float | None],
    ) -> tuple[float, dict[str, float]]:
        available = {
            key: val for key, val in component_scores.items() if val is not None
        }
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

    def _component_inputs_from_dict(
        self, values: dict[str, Any]
    ) -> dict[str, float | None]:
        values = values or {}
        return {
            "superclaude": self._coerce_score_value(
                values.get("superclaude") or values.get("correctness")
            ),
            "completeness": self._coerce_score_value(values.get("completeness")),
            "test_coverage": self._coerce_score_value(
                values.get("test_coverage")
                or values.get("tests")
                or values.get("coverage")
                or values.get("testability")
            ),
        }

    def _coerce_score_value(self, value: Any) -> float | None:
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
        self, output: Any, context: dict[str, Any]
    ) -> list[str]:
        """
        Collect any evidence that real work was performed.

        Args:
            output: Agent or command output
            context: Quality evaluation context

        Returns:
            List of execution evidence descriptions
        """

        def collect(value: Any, prefix: str | None = None) -> list[str]:
            evidence: list[str] = []
            label = f"{prefix}: " if prefix else ""

            if isinstance(value, list):
                for item in value:
                    if item:
                        evidence.append(f"{label}{item}")
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    evidence.extend(
                        collect(
                            subvalue,
                            f"{label}{subkey}" if not prefix else f"{label}{subkey}",
                        )
                    )
            elif isinstance(value, (str, int, float)) and str(value).strip():
                evidence.append(f"{label}{value}")

            return evidence

        evidence: list[str] = []

        if isinstance(output, dict):
            for key in (
                "actions_taken",
                "executed_operations",
                "applied_changes",
                "files_modified",
                "commands_run",
                "diff_summary",
                "evidence",
            ):
                if key in output:
                    evidence.extend(collect(output[key], key))

        # Context provided evidence
        for key in ("evidence", "execution", "diff_summary", "applied_changes"):
            if key in context:
                evidence.extend(collect(context[key], key))

        test_results = context.get("test_results", {})
        if isinstance(test_results, dict):
            passed = test_results.get("passed")
            pass_rate = test_results.get("pass_rate")
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

    def _extract_functions(self, code: str) -> list[str]:
        """Extract function bodies from code."""
        functions = []
        lines = code.split("\n")
        current_function = []
        in_function = False

        for line in lines:
            if line.strip().startswith("def "):
                if current_function:
                    functions.append("\n".join(current_function))
                current_function = [line]
                in_function = True
            elif in_function:
                if line and not line[0].isspace() and not line.startswith("#"):
                    # End of function
                    functions.append("\n".join(current_function))
                    current_function = []
                    in_function = False
                else:
                    current_function.append(line)

        if current_function:
            functions.append("\n".join(current_function))

        return functions

    def _has_duplication(self, text: str) -> bool:
        """Check for code duplication (simplified)."""
        lines = text.split("\n")
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

    def evaluate_sdk_execution(
        self,
        record: dict[str, Any],
        context: dict[str, Any],
        iteration: int = 0,
    ) -> QualityAssessment:
        """
        Evaluate SDK execution result with evidence-based grounding.

        This method is the single source of truth for scoring SDK executions.
        It unwraps the execution record, applies base evaluation, then applies
        deterministic signals from collected evidence.

        Args:
            record: SDK execution record containing:
                - result: The final output payload (dict or str)
                - success: Whether execution succeeded
                - evidence: Evidence snapshot from hooks (dict)
                - errors: Optional error information
                - agent_used: Name of agent that executed
                - confidence: Agent selection confidence
            context: Evaluation context (may include expectations)
            iteration: Current iteration number

        Returns:
            QualityAssessment with deterministic grounding from evidence.
        """
        # Extract payload for generic evaluation
        payload = record.get("result") or record.get("output") or {}

        # Run base evaluation on the payload
        assessment = self.evaluate(
            output=payload,
            context=context,
            iteration=iteration,
        )

        # Extract evidence and convert to deterministic signals
        evidence_data = record.get("evidence", {})
        signals = self._signals_from_sdk_evidence(evidence_data)

        # Apply deterministic caps/boosts
        adjusted_score, signal_details = self.apply_deterministic_signals(
            assessment.overall_score, signals
        )

        # Update assessment with adjusted score
        assessment.overall_score = adjusted_score
        assessment.passed = adjusted_score >= self.thresholds.production_ready
        assessment.band = self.thresholds.classify(adjusted_score)

        # Attach SDK-specific metadata
        assessment.metadata["sdk_execution"] = {
            "agent_used": record.get("agent_used"),
            "confidence": record.get("confidence", 0.0),
            "success": record.get("success", False),
            "evidence_summary": {
                "has_file_modifications": evidence_data.get(
                    "has_file_modifications", False
                ),
                "has_execution_evidence": evidence_data.get(
                    "has_execution_evidence", False
                ),
                "tool_count": evidence_data.get("tool_count", 0),
                "files_written": evidence_data.get("files_written", 0),
                "files_edited": evidence_data.get("files_edited", 0),
                "tests_run": evidence_data.get("tests_run", False),
            },
        }
        assessment.metadata["deterministic_signals"] = signal_details
        assessment.metadata["signals_grounded"] = True

        # Check evidence expectations if defined (opt-in strictness)
        self._apply_evidence_expectations(assessment, evidence_data, context)

        return assessment

    def _signals_from_sdk_evidence(
        self, evidence_data: dict[str, Any]
    ) -> DeterministicSignals:
        """
        Convert SDK evidence snapshot to DeterministicSignals.

        Args:
            evidence_data: Evidence dict from hooks (already serialized).

        Returns:
            DeterministicSignals for quality scoring.
        """
        return DeterministicSignals(
            tests_passed=(
                evidence_data.get("test_failed", 0) == 0
                and evidence_data.get("tests_run", False)
            ),
            tests_total=(
                evidence_data.get("test_passed", 0)
                + evidence_data.get("test_failed", 0)
            ),
            tests_failed=evidence_data.get("test_failed", 0),
            test_coverage=evidence_data.get("test_coverage", 0.0),
        )

    def _apply_evidence_expectations(
        self,
        assessment: QualityAssessment,
        evidence_data: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        """
        Apply evidence expectation checks (opt-in strictness).

        Only adds evidence-related issues when expectations are explicitly
        enabled in the context. This prevents penalizing read-only or
        advisory commands that don't produce file changes.

        Args:
            assessment: Quality assessment to update.
            evidence_data: Evidence snapshot from hooks.
            context: Context with optional expectations.
        """
        # Check if expectations are enabled (opt-in)
        expects_file_changes = context.get("expects_file_changes", False)
        expects_tests = context.get("expects_tests", False)
        expects_execution_evidence = context.get("expects_execution_evidence", False)

        evidence_issues: list[str] = []

        # Check file changes expectation
        if expects_file_changes:
            has_modifications = evidence_data.get("has_file_modifications", False)
            if not has_modifications:
                evidence_issues.append(
                    "MISSING_FILE_CHANGES: No file modifications detected"
                )

        # Check test execution expectation
        if expects_tests:
            tests_run = evidence_data.get("tests_run", False)
            if not tests_run:
                evidence_issues.append("NO_TESTS_RUN: Test execution was expected")

        # Check general execution evidence expectation
        if expects_execution_evidence:
            has_evidence = evidence_data.get("has_execution_evidence", False)
            if not has_evidence:
                evidence_issues.append(
                    "NO_EXECUTION_EVIDENCE: "
                    "Expected file changes, commands, or tests"
                )

        # Add evidence issues to improvements_needed (at the front for priority)
        if evidence_issues:
            assessment.improvements_needed = (
                evidence_issues + assessment.improvements_needed
            )
            assessment.metadata["evidence_expectations_failed"] = evidence_issues
