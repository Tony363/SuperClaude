"""
Loop Orchestrator for SuperClaude Agentic Loop.

This is the core of the --loop functionality. It manages:
1. Iteration counting and safety limits
2. Quality assessment after each iteration
3. Termination condition detection
4. PAL MCP signal generation within iterations
5. Delegation to Skills via Claude Code

Architecture:
- Orchestrator manages the loop mechanics (procedural/stateful)
- Skills (sc-implement) perform the actual work (declarative)
- Claude Code executes Skills and processes signals
"""

import time
from typing import Any, Callable

from .types import (
    IterationResult,
    LoopConfig,
    LoopResult,
    QualityAssessment,
    TerminationReason,
)
from .termination import (
    detect_oscillation,
    detect_stagnation,
    check_insufficient_improvement,
)
from .quality_assessment import QualityAssessor
from .pal_integration import PALReviewSignal, incorporate_pal_feedback


class LoopOrchestrator:
    """
    Lightweight agentic loop orchestrator.

    This class implements the --loop functionality that was archived
    in v5's QualityScorer.agentic_loop(). It provides:

    - Safety mechanisms (hard max, oscillation/stagnation detection)
    - Quality-driven iteration (stop when threshold met)
    - PAL MCP integration within loop (not just after)
    - Signal-based skill invocation (Claude Code processes signals)

    Usage:
        orchestrator = LoopOrchestrator(config)
        result = orchestrator.run(context, skill_invoker)

    Where skill_invoker is a callable that Claude Code uses to
    execute the sc-implement skill and return evidence.
    """

    def __init__(self, config: LoopConfig | None = None):
        """
        Initialize the loop orchestrator.

        Args:
            config: Loop configuration (defaults to LoopConfig())
        """
        self.config = config or LoopConfig()
        self.assessor = QualityAssessor(self.config.quality_threshold)
        self.iteration_history: list[IterationResult] = []
        self.score_history: list[float] = []
        self.all_changed_files: list[str] = []
        self._start_time: float = 0.0

    def run(
        self,
        initial_context: dict[str, Any],
        skill_invoker: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> LoopResult:
        """
        Execute the agentic loop.

        Args:
            initial_context: Initial task context with:
                - task: Description of what to implement
                - improvements_needed: Initial improvements (optional)
                - changed_files: Already modified files (optional)
            skill_invoker: Function that invokes Skills via Claude Code.
                Should accept context dict and return result dict with:
                - changes: List of file changes
                - tests: Test results
                - lint: Lint results
                - changed_files: Files modified

        Returns:
            LoopResult with final output, assessment, and iteration history
        """
        self._start_time = time.monotonic()
        current_context = initial_context.copy()
        termination_reason = TerminationReason.MAX_ITERATIONS
        output: dict[str, Any] = {}
        assessment = QualityAssessment(overall_score=0.0, passed=False)

        for iteration in range(self.config.max_iterations):
            iter_start = time.monotonic()

            # Check timeout
            if self._check_timeout():
                termination_reason = TerminationReason.TIMEOUT
                break

            # 1. Execute skill (delegated to Claude Code)
            try:
                output = skill_invoker(current_context)
            except Exception as e:
                termination_reason = TerminationReason.ERROR
                self._record_iteration(
                    iteration=iteration,
                    assessment=assessment,
                    time_taken=time.monotonic() - iter_start,
                    success=False,
                    termination="error",
                    changed_files=[],
                )
                break

            # Track changed files
            changed_files = output.get("changed_files", [])
            self.all_changed_files.extend(
                f for f in changed_files if f not in self.all_changed_files
            )

            # 2. Assess quality
            assessment = self.assessor.assess(output)
            self.score_history.append(assessment.overall_score)

            # 3. Check if quality threshold met
            if assessment.passed:
                termination_reason = TerminationReason.QUALITY_MET
                self._record_iteration(
                    iteration=iteration,
                    assessment=assessment,
                    time_taken=time.monotonic() - iter_start,
                    success=True,
                    termination="quality_met",
                    changed_files=changed_files,
                )
                break

            # 4. Check termination conditions
            if detect_oscillation(
                self.score_history,
                self.config.oscillation_window,
            ):
                termination_reason = TerminationReason.OSCILLATION
                self._record_iteration(
                    iteration=iteration,
                    assessment=assessment,
                    time_taken=time.monotonic() - iter_start,
                    success=False,
                    termination="oscillation",
                    changed_files=changed_files,
                )
                break

            if detect_stagnation(
                self.score_history,
                self.config.oscillation_window,
                self.config.stagnation_threshold,
            ):
                termination_reason = TerminationReason.STAGNATION
                self._record_iteration(
                    iteration=iteration,
                    assessment=assessment,
                    time_taken=time.monotonic() - iter_start,
                    success=False,
                    termination="stagnation",
                    changed_files=changed_files,
                )
                break

            if iteration > 0 and check_insufficient_improvement(
                self.score_history[-1],
                self.score_history[-2],
                self.config.min_improvement,
            ):
                termination_reason = TerminationReason.INSUFFICIENT_IMPROVEMENT
                self._record_iteration(
                    iteration=iteration,
                    assessment=assessment,
                    time_taken=time.monotonic() - iter_start,
                    success=False,
                    termination="insufficient_improvement",
                    changed_files=changed_files,
                )
                break

            # 5. Generate PAL review signal (if enabled and not last iteration)
            pal_signal = None
            if (
                self.config.pal_review_enabled
                and iteration < self.config.max_iterations - 1
            ):
                pal_signal = PALReviewSignal.generate_review_signal(
                    iteration=iteration,
                    changed_files=changed_files,
                    quality_assessment=assessment,
                    model=self.config.pal_model,
                )

            # 6. Record iteration
            self._record_iteration(
                iteration=iteration,
                assessment=assessment,
                time_taken=time.monotonic() - iter_start,
                success=False,  # Not done yet
                termination="",
                changed_files=changed_files,
                pal_signal=pal_signal,
            )

            # 7. Prepare next iteration context
            current_context = self._prepare_next_iteration(
                current_context,
                assessment,
                output,
            )

        # Generate final signals
        if termination_reason == TerminationReason.QUALITY_MET:
            # Final validation signal
            final_signal = PALReviewSignal.generate_final_validation_signal(
                changed_files=self.all_changed_files,
                quality_assessment=assessment,
                iteration_count=len(self.iteration_history),
                model=self.config.pal_model,
            )
            if self.iteration_history:
                self.iteration_history[-1].pal_review = final_signal

        elif termination_reason in (
            TerminationReason.OSCILLATION,
            TerminationReason.STAGNATION,
        ):
            # Debug signal for stuck loops
            debug_signal = PALReviewSignal.generate_debug_signal(
                iteration=len(self.iteration_history) - 1,
                termination_reason=termination_reason.value,
                score_history=self.score_history,
                model=self.config.pal_model,
            )
            if self.iteration_history:
                self.iteration_history[-1].pal_review = debug_signal

        return LoopResult(
            final_output=output,
            final_assessment=assessment,
            iteration_history=self.iteration_history,
            termination_reason=termination_reason,
            total_iterations=len(self.iteration_history),
            total_time=time.monotonic() - self._start_time,
        )

    def _check_timeout(self) -> bool:
        """Check if wall-clock timeout exceeded."""
        if self.config.timeout_seconds is None:
            return False
        elapsed = time.monotonic() - self._start_time
        return elapsed > self.config.timeout_seconds

    def _record_iteration(
        self,
        iteration: int,
        assessment: QualityAssessment,
        time_taken: float,
        success: bool,
        termination: str,
        changed_files: list[str],
        pal_signal: dict[str, Any] | None = None,
    ) -> None:
        """Record an iteration result."""
        input_quality = (
            self.score_history[-2] if len(self.score_history) >= 2 else 0.0
        )
        output_quality = assessment.overall_score

        self.iteration_history.append(
            IterationResult(
                iteration=iteration,
                input_quality=input_quality,
                output_quality=output_quality,
                improvements_applied=assessment.improvements_needed[:5],
                time_taken=time_taken,
                success=success,
                termination_reason=termination,
                pal_review=pal_signal,
                changed_files=changed_files,
            )
        )

    def _prepare_next_iteration(
        self,
        current_context: dict[str, Any],
        assessment: QualityAssessment,
        output: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Prepare context for the next iteration.

        Incorporates quality feedback and any PAL review results.

        Args:
            current_context: Current iteration context
            assessment: Quality assessment from this iteration
            output: Output from skill execution

        Returns:
            Updated context for next iteration
        """
        next_context = current_context.copy()

        # Add improvements needed
        next_context["improvements_needed"] = assessment.improvements_needed

        # Add iteration info
        next_context["iteration"] = len(self.iteration_history)
        next_context["previous_score"] = assessment.overall_score
        next_context["target_score"] = self.config.quality_threshold

        # Add changed files for context
        next_context["previous_changes"] = output.get("changes", [])

        # Incorporate PAL feedback if available
        if self.iteration_history and self.iteration_history[-1].pal_review:
            pal_result = self.iteration_history[-1].pal_review
            if pal_result.get("result"):
                next_context = incorporate_pal_feedback(
                    next_context,
                    pal_result["result"],
                )

        return next_context


def create_skill_invoker_signal(context: dict[str, Any]) -> dict[str, Any]:
    """
    Create a signal for Claude Code to execute a skill.

    This is a helper function that generates the signal structure
    that Claude Code processes to invoke the sc-implement skill.

    Args:
        context: Context for the skill execution

    Returns:
        Signal dict for Claude Code
    """
    return {
        "action": "execute_skill",
        "skill": "sc-implement",
        "parameters": {
            "task": context.get("task", ""),
            "improvements_needed": context.get("improvements_needed", []),
            "iteration": context.get("iteration", 0),
            "focus": "remediation" if context.get("iteration", 0) > 0 else "implementation",
        },
        "collect": ["changes", "tests", "lint", "changed_files"],
        "context": context,
    }
