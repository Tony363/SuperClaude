"""
PAL MCP Integration for SuperClaude Loop Orchestration.

Generates signals for PAL MCP tools to be invoked within
loop iterations, not just after loop completion.

This enables:
- Per-iteration code review via mcp__pal__codereview
- Debugging assistance via mcp__pal__debug when stuck
- Consensus building via mcp__pal__consensus for architecture
"""

from typing import Any

from .types import QualityAssessment


class PALReviewSignal:
    """
    Generate signals for PAL MCP invocation within loop iterations.

    This class creates structured signals that Claude Code can
    process and act upon, invoking the appropriate PAL MCP tools.
    """

    # PAL MCP tool names
    TOOL_CODEREVIEW = "mcp__pal__codereview"
    TOOL_DEBUG = "mcp__pal__debug"
    TOOL_THINKDEEP = "mcp__pal__thinkdeep"
    TOOL_CONSENSUS = "mcp__pal__consensus"

    @staticmethod
    def generate_review_signal(
        iteration: int,
        changed_files: list[str],
        quality_assessment: QualityAssessment,
        model: str = "gpt-5",
        review_type: str = "auto",
    ) -> dict[str, Any]:
        """
        Generate a PAL review signal for Claude Code to process.

        Args:
            iteration: Current iteration number (0-based)
            changed_files: List of files modified in this iteration
            quality_assessment: Current quality assessment
            model: Model to use for PAL review
            review_type: Type of review (quick/full/security/auto)

        Returns:
            Signal dict for Claude Code to process
        """
        # Auto-determine review type based on iteration and score
        if review_type == "auto":
            if quality_assessment.overall_score < 50:
                review_type = "full"
            elif iteration < 2:
                review_type = "quick"
            else:
                review_type = "full"

        return {
            "action_required": True,
            "tool": PALReviewSignal.TOOL_CODEREVIEW,
            "iteration": iteration,
            "instruction": (
                f"Loop iteration {iteration + 1}: Review the changed files "
                f"to identify improvements before next iteration."
            ),
            "files": changed_files,
            "model": model,
            "review_type": review_type,
            "context": {
                "current_score": quality_assessment.overall_score,
                "target_score": quality_assessment.threshold,
                "quality_band": quality_assessment.band,
                "improvements_needed": quality_assessment.improvements_needed[:5],
            },
            "parameters": {
                "step": f"Review changes from loop iteration {iteration + 1}",
                "step_number": 1,
                "total_steps": 2,
                "next_step_required": True,
                "findings": "",
                "relevant_files": changed_files,
            },
        }

    @staticmethod
    def generate_debug_signal(
        iteration: int,
        termination_reason: str,
        score_history: list[float],
        model: str = "gpt-5",
    ) -> dict[str, Any]:
        """
        Generate a PAL debug signal when loop is stuck.

        Used when oscillation or stagnation is detected to
        diagnose why improvements aren't converging.

        Args:
            iteration: Current iteration number
            termination_reason: Why the loop is stopping
            score_history: History of quality scores
            model: Model to use for debugging

        Returns:
            Signal dict for Claude Code to process
        """
        return {
            "action_required": True,
            "tool": PALReviewSignal.TOOL_DEBUG,
            "iteration": iteration,
            "instruction": (
                f"Loop terminated due to {termination_reason}. "
                f"Diagnose why improvements aren't converging."
            ),
            "model": model,
            "context": {
                "termination_reason": termination_reason,
                "score_history": score_history,
                "pattern": _detect_pattern(score_history),
            },
            "parameters": {
                "step": f"Diagnose {termination_reason} in improvement loop",
                "step_number": 1,
                "total_steps": 1,
                "next_step_required": False,
                "findings": "",
                "hypothesis": f"Loop stuck due to {termination_reason}",
            },
        }

    @staticmethod
    def generate_final_validation_signal(
        changed_files: list[str],
        quality_assessment: QualityAssessment,
        iteration_count: int,
        model: str = "gpt-5",
    ) -> dict[str, Any]:
        """
        Generate a final validation signal when quality threshold is met.

        Performs comprehensive review before marking as complete.

        Args:
            changed_files: All files modified during loop
            quality_assessment: Final quality assessment
            iteration_count: Total iterations completed
            model: Model to use for validation

        Returns:
            Signal dict for Claude Code to process
        """
        return {
            "action_required": True,
            "tool": PALReviewSignal.TOOL_CODEREVIEW,
            "iteration": iteration_count - 1,
            "instruction": (
                f"Quality threshold met after {iteration_count} iteration(s). "
                f"Perform final validation before completion."
            ),
            "files": changed_files,
            "model": model,
            "review_type": "full",
            "is_final": True,
            "context": {
                "final_score": quality_assessment.overall_score,
                "threshold": quality_assessment.threshold,
                "quality_band": quality_assessment.band,
                "total_iterations": iteration_count,
            },
            "parameters": {
                "step": "Final validation of completed loop",
                "step_number": 2,
                "total_steps": 2,
                "next_step_required": False,
                "findings": f"Quality score: {quality_assessment.overall_score}",
                "relevant_files": changed_files,
            },
        }


def _detect_pattern(score_history: list[float]) -> str:
    """
    Detect the pattern in score history for debugging.

    Args:
        score_history: List of quality scores

    Returns:
        Pattern description
    """
    if len(score_history) < 2:
        return "insufficient_data"

    # Check for oscillation
    directions = []
    for i in range(1, len(score_history)):
        diff = score_history[i] - score_history[i - 1]
        if abs(diff) > 2.0:
            directions.append("up" if diff > 0 else "down")

    if len(directions) >= 2:
        alternating = all(
            directions[i] != directions[i + 1]
            for i in range(len(directions) - 1)
        )
        if alternating:
            return "oscillating"

    # Check for stagnation
    recent = score_history[-3:] if len(score_history) >= 3 else score_history
    if max(recent) - min(recent) < 2.0:
        return "stagnating"

    # Check for declining
    if len(score_history) >= 2 and score_history[-1] < score_history[0]:
        return "declining"

    # Check for improving
    if len(score_history) >= 2 and score_history[-1] > score_history[0]:
        return "improving"

    return "mixed"


def incorporate_pal_feedback(
    context: dict[str, Any],
    pal_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge PAL review feedback into next iteration context.

    Args:
        context: Current iteration context
        pal_result: Results from PAL MCP review

    Returns:
        Updated context with incorporated feedback
    """
    issues = pal_result.get("issues_found", [])

    # Prioritize issues by severity
    critical = [i for i in issues if i.get("severity") == "critical"]
    high = [i for i in issues if i.get("severity") == "high"]
    medium = [i for i in issues if i.get("severity") == "medium"]

    improvements = context.get("improvements_needed", [])

    # Prepend critical/high issues
    for issue in critical + high:
        description = issue.get("description", "")
        if description and description not in improvements:
            improvements.insert(0, description)

    # Append medium issues
    for issue in medium:
        description = issue.get("description", "")
        if description and description not in improvements:
            improvements.append(description)

    # Keep top 10 improvements
    context["improvements_needed"] = improvements[:10]
    context["pal_feedback"] = pal_result

    return context
