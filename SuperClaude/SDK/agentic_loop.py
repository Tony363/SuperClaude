"""
SDK Agentic Loop for iterative quality improvement.

This module provides a thin wrapper around QualityScorer.agentic_loop()
specifically for SDK executions. It handles:
- SDK-specific improver function creation
- Evidence extraction and quality scoring
- Repair prompt generation from improvement hints

The loop reuses the existing stop policies (max iterations, oscillation,
stagnation detection) from QualityScorer rather than duplicating them.

Example:
    from SuperClaude.SDK.agentic_loop import run_sdk_loop

    final_record, assessment, history = await run_sdk_loop(
        executor=sdk_executor,
        task="Fix the bug in auth.py",
        context={"cwd": "/project", "requires_evidence": True},
        scorer=quality_scorer,
    )
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..Quality.quality_scorer import (
        IterationResult,
        QualityAssessment,
        QualityScorer,
    )
    from .executor import SDKExecutionResult, SDKExecutor

logger = logging.getLogger(__name__)


def create_sdk_improver(
    executor: SDKExecutor,
    original_task: str,
    base_context: dict[str, Any],
) -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    """
    Create an improver function for SDK executions.

    The improver function is compatible with QualityScorer.agentic_loop()
    and handles re-executing via SDK with repair hints.

    Args:
        executor: SDKExecutor instance for re-execution.
        original_task: The original task string.
        base_context: Base context for execution (cwd, flags, etc).

    Returns:
        Improver function: (output, context) -> improved_output
    """

    def improver(output: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Re-execute SDK with repair hints from quality assessment.

        Args:
            output: Previous SDK execution record.
            context: Context with quality_assessment and improvements_needed.

        Returns:
            New SDK execution record.
        """
        # Extract improvement hints from context
        improvements = context.get("improvements_needed", [])
        quality_assessment = context.get("quality_assessment")

        # Build enhanced task with repair hints
        enhanced_task = build_repair_prompt(
            original_task=original_task,
            improvements=improvements,
            previous_score=quality_assessment.overall_score if quality_assessment else 0,
            iteration=context.get("iteration", 0),
        )

        # Execute via SDK (sync wrapper for async executor)
        # Use asyncio.run only if not already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - need to use run_in_executor
            # This shouldn't happen in normal flow, but handle gracefully
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _execute_sdk_async(executor, enhanced_task, base_context),
                )
                result = future.result()
        except RuntimeError:
            # No running loop - safe to use asyncio.run
            result = asyncio.run(
                _execute_sdk_async(executor, enhanced_task, base_context)
            )

        return result.to_record()

    return improver


async def _execute_sdk_async(
    executor: SDKExecutor,
    task: str,
    context: dict[str, Any],
) -> SDKExecutionResult:
    """
    Execute SDK asynchronously with the given task.

    This is a helper for the improver function to call the async executor.

    Args:
        executor: SDKExecutor instance.
        task: Enhanced task with repair hints.
        context: Execution context.

    Returns:
        SDKExecutionResult from execution.
    """
    # Build a minimal CommandContext-like object for the executor
    # The executor needs context.command.name at minimum
    from ..Commands.execution.context import CommandContext

    # Create a mock command context with the enhanced task
    # In practice, the facade would provide a real context
    class MockCommand:
        def __init__(self, name: str, task: str):
            self.name = name
            self.arguments = [task]
            self.parameters = {}
            self.flags = {}

    mock_command = MockCommand(
        name=context.get("command_name", "iterate"),
        task=task,
    )

    # Create minimal context
    exec_context = type(
        "Context",
        (),
        {
            "command": mock_command,
            "session_id": context.get("session_id", "sdk-loop"),
            "cwd": context.get("cwd", "."),
            "requires_evidence": context.get("requires_evidence", False),
        },
    )()

    # Execute via SDK
    return await executor.execute(exec_context, force_sdk=True)


def build_repair_prompt(
    original_task: str,
    improvements: list[str],
    previous_score: float = 0.0,
    iteration: int = 0,
) -> str:
    """
    Build an enhanced task prompt with repair hints.

    Args:
        original_task: The original task description.
        improvements: List of improvement suggestions from quality assessment.
        previous_score: Score from previous iteration.
        iteration: Current iteration number.

    Returns:
        Enhanced task string with repair context.
    """
    if not improvements:
        return original_task

    # Build repair context
    parts = [original_task]

    parts.append("\n\n---")
    parts.append(f"\n## Iteration {iteration + 1} Improvements Required")
    parts.append(f"\nPrevious quality score: {previous_score:.1f}/100")
    parts.append("\nPlease address the following issues:\n")

    for i, improvement in enumerate(improvements[:5], 1):  # Top 5 improvements
        parts.append(f"{i}. {improvement}")

    parts.append(
        "\n\nFocus on concrete changes that demonstrate progress. "
        "Show file modifications, test results, or command outputs as evidence."
    )

    return "\n".join(parts)


async def run_sdk_loop(
    executor: SDKExecutor,
    task: str,
    context: dict[str, Any],
    scorer: QualityScorer,
    max_iterations: int | None = None,
    min_improvement: float | None = None,
) -> tuple[dict[str, Any], QualityAssessment, list[IterationResult]]:
    """
    Run SDK execution with iterative quality improvement.

    This is the main entry point for SDK agentic loop execution.
    It wraps QualityScorer.agentic_loop() with SDK-specific handling.

    Args:
        executor: SDKExecutor for SDK execution.
        task: Task to execute.
        context: Execution context (cwd, flags, expectations).
        scorer: QualityScorer for evaluation.
        max_iterations: Maximum iterations (default: scorer's MAX_ITERATIONS).
        min_improvement: Minimum improvement to continue (default: scorer's MIN_IMPROVEMENT).

    Returns:
        Tuple of (final_record, final_assessment, iteration_history)
    """
    # Execute initial SDK run
    initial_result = await _execute_sdk_async(executor, task, context)
    initial_record = initial_result.to_record()

    # If SDK failed and requested fallback, return immediately
    if initial_result.should_fallback:
        # Create a minimal assessment for failed execution
        assessment = scorer.evaluate_sdk_execution(
            record=initial_record,
            context=context,
            iteration=0,
        )
        return initial_record, assessment, []

    # Create improver function
    improver = create_sdk_improver(
        executor=executor,
        original_task=task,
        base_context=context,
    )

    # Wrap scorer evaluation for SDK records
    original_evaluate = scorer.evaluate

    def sdk_evaluate(output: Any, ctx: dict[str, Any], **kwargs: Any) -> Any:
        """Override evaluate to use SDK-specific evaluation."""
        if isinstance(output, dict) and "evidence" in output:
            return scorer.evaluate_sdk_execution(output, ctx, **kwargs)
        return original_evaluate(output, ctx, **kwargs)

    # Temporarily swap evaluator
    scorer.evaluate = sdk_evaluate  # type: ignore[method-assign]

    try:
        # Run the agentic loop
        final_record, final_assessment, history = scorer.agentic_loop(
            initial_output=initial_record,
            context=context,
            improver_func=improver,
            max_iterations=max_iterations,
            min_improvement=min_improvement,
        )
    finally:
        # Restore original evaluator
        scorer.evaluate = original_evaluate  # type: ignore[method-assign]

    return final_record, final_assessment, history


def create_sdk_loop_context(
    command_name: str,
    task: str,
    cwd: str | None = None,
    requires_evidence: bool = False,
    expects_file_changes: bool = False,
    expects_tests: bool = False,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a context dictionary for SDK loop execution.

    Helper function to build the context with proper expectations.

    Args:
        command_name: Name of the command being executed.
        task: Task description.
        cwd: Working directory.
        requires_evidence: Whether evidence is required.
        expects_file_changes: Whether file modifications are expected.
        expects_tests: Whether test execution is expected.
        session_id: Optional session ID.

    Returns:
        Context dictionary for run_sdk_loop().
    """
    return {
        "command_name": command_name,
        "original_task": task,
        "cwd": cwd or ".",
        "requires_evidence": requires_evidence,
        "expects_file_changes": expects_file_changes,
        "expects_tests": expects_tests,
        "expects_execution_evidence": requires_evidence,
        "session_id": session_id,
    }
