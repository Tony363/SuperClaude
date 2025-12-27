"""
Core types for SuperClaude Loop Orchestration.

Ported from archive/python-sdk-v5/Quality/quality_scorer.py
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TerminationReason(Enum):
    """
    Reasons for loop termination.

    Ported from archived quality_scorer.py lines 85-96.
    """

    QUALITY_MET = "quality_threshold_met"
    MAX_ITERATIONS = "max_iterations_reached"
    INSUFFICIENT_IMPROVEMENT = "insufficient_improvement"
    STAGNATION = "score_stagnation"
    OSCILLATION = "score_oscillation"
    ERROR = "improver_error"
    HUMAN_ESCALATION = "requires_human_review"
    TIMEOUT = "timeout"


@dataclass
class LoopConfig:
    """
    Configuration for the agentic loop.

    Attributes:
        max_iterations: Requested maximum iterations (default 3, capped at 5)
        hard_max_iterations: Absolute cap that CANNOT be overridden (5)
        min_improvement: Minimum score improvement to continue (5.0 points)
        quality_threshold: Target quality score to meet (70.0)
        oscillation_window: Number of scores to check for oscillation (3)
        stagnation_threshold: Score variance below which = stagnation (2.0)
        timeout_seconds: Wall-clock timeout (optional)
        pal_review_enabled: Enable PAL MCP review within loop iterations
        pal_model: Model to use for PAL reviews
    """

    max_iterations: int = 3
    hard_max_iterations: int = 5  # P0 SAFETY: Cannot be overridden
    min_improvement: float = 5.0
    quality_threshold: float = 70.0
    oscillation_window: int = 3
    stagnation_threshold: float = 2.0
    timeout_seconds: float | None = None
    pal_review_enabled: bool = True
    pal_model: str = "gpt-5"

    def __post_init__(self):
        """Enforce hard maximum iterations."""
        if self.max_iterations > self.hard_max_iterations:
            self.max_iterations = self.hard_max_iterations


@dataclass
class QualityAssessment:
    """
    Result of quality assessment for an iteration.

    Attributes:
        overall_score: Numeric quality score (0-100)
        passed: Whether quality threshold was met
        threshold: The threshold that was checked against
        improvements_needed: List of specific improvements to make
        metrics: Detailed breakdown of quality dimensions
        band: Quality band (excellent/good/acceptable/poor/failing)
        metadata: Additional context from evidence collection
    """

    overall_score: float
    passed: bool
    threshold: float = 70.0
    improvements_needed: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    band: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IterationResult:
    """
    Result of a single loop iteration.

    Attributes:
        iteration: Zero-based iteration number
        input_quality: Quality score before this iteration
        output_quality: Quality score after this iteration
        improvements_applied: List of improvements that were applied
        time_taken: Duration of this iteration in seconds
        success: Whether this iteration improved quality
        termination_reason: If loop terminated, why (empty if continuing)
        pal_review: Results from PAL MCP review (if performed)
        changed_files: List of files modified in this iteration
    """

    iteration: int
    input_quality: float
    output_quality: float
    improvements_applied: list[str] = field(default_factory=list)
    time_taken: float = 0.0
    success: bool = False
    termination_reason: str = ""
    pal_review: dict[str, Any] | None = None
    changed_files: list[str] = field(default_factory=list)


@dataclass
class LoopResult:
    """
    Final result of the complete loop execution.

    Attributes:
        final_output: The final state after all iterations
        final_assessment: Quality assessment of final state
        iteration_history: List of all iteration results
        termination_reason: Why the loop stopped
        total_iterations: Number of iterations executed
        total_time: Total wall-clock time for all iterations
    """

    final_output: dict[str, Any]
    final_assessment: QualityAssessment
    iteration_history: list[IterationResult]
    termination_reason: TerminationReason
    total_iterations: int
    total_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "loop_completed": True,
            "iterations": self.total_iterations,
            "termination_reason": self.termination_reason.value,
            "final_score": self.final_assessment.overall_score,
            "passed": self.final_assessment.passed,
            "total_time": self.total_time,
            "history": [
                {
                    "iteration": r.iteration,
                    "input_score": r.input_quality,
                    "output_score": r.output_quality,
                    "success": r.success,
                    "improvements": r.improvements_applied,
                    "pal_review": r.pal_review,
                    "changed_files": r.changed_files,
                }
                for r in self.iteration_history
            ],
        }
