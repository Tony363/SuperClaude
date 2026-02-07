"""
Agentic Loop Runner - Main entry point using Official Anthropic Agent SDK.

This module implements SuperClaude's iterative quality improvement loop:
1. Execute task via SDK query() with hooks
2. Collect evidence from hooks
3. Assess quality from evidence
4. Check termination conditions
5. Prepare improved context for next iteration
6. Repeat until quality threshold or max iterations

Usage:
    from SuperClaude.Orchestrator import run_agentic_loop

    result = await run_agentic_loop(
        task="Implement user authentication",
        max_iterations=3,
        quality_threshold=70.0,
    )
    print(f"Final score: {result.final_score}")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from .evidence import EvidenceCollector
from .events_hooks import EventsTracker, create_events_hooks, create_iteration_callback
from .hooks import create_sdk_hooks, merge_hooks
from .quality import QualityAssessment, QualityConfig, assess_quality

# Logger for this module
logger = logging.getLogger(__name__)


class TerminationReason(Enum):
    """Reasons for loop termination."""

    QUALITY_MET = "quality_threshold_met"
    MAX_ITERATIONS = "max_iterations_reached"
    OSCILLATION = "oscillation_detected"
    STAGNATION = "stagnation_detected"
    TIMEOUT = "timeout_exceeded"
    USER_CANCELLED = "user_cancelled"
    ERROR = "error"


@dataclass
class LoopConfig:
    """Configuration for the agentic loop."""

    # Iteration limits
    max_iterations: int = 3
    hard_max_iterations: int = 5  # Safety cap, cannot be overridden

    # Quality settings
    quality_threshold: float = 70.0
    min_improvement: float = 5.0  # Minimum score improvement to continue

    # Termination detection
    oscillation_window: int = 3
    stagnation_threshold: float = 2.0

    # Timeouts
    timeout_seconds: float | None = None
    iteration_timeout_seconds: float = 300.0  # 5 minutes per iteration

    # Model settings
    model: str = "sonnet"
    max_turns: int = 50

    # PAL integration
    pal_review_enabled: bool = False
    pal_model: str = "gpt-5"


@dataclass
class IterationResult:
    """Result of a single loop iteration."""

    iteration: int
    score: float
    improvements: list[str]
    evidence: dict[str, Any]
    duration_seconds: float
    messages_count: int


@dataclass
class LoopResult:
    """Final result of the agentic loop."""

    status: str  # "success" or "terminated"
    reason: TerminationReason
    final_score: float
    total_iterations: int
    iteration_history: list[IterationResult]
    total_duration_seconds: float
    evidence_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Whether the loop achieved its quality threshold."""
        return self.status == "success"


async def run_agentic_loop(
    task: str,
    config: LoopConfig | None = None,
    additional_hooks: dict[str, list[dict]] | None = None,
    on_iteration: Callable[[IterationResult], None] | None = None,
    events_tracker: EventsTracker | None = None,
    enable_events: bool = True,
) -> LoopResult:
    """
    Run SuperClaude's agentic loop using the Official Anthropic Agent SDK.

    This is the main entry point that orchestrates:
    1. Evidence collection via SDK hooks
    2. Quality assessment from evidence
    3. Termination condition checking
    4. Context preparation for next iteration

    Args:
        task: Task description for Claude to execute
        config: Loop configuration (uses defaults if None)
        additional_hooks: Extra hooks to merge with default hooks
        on_iteration: Callback after each iteration completes
        events_tracker: Optional EventsTracker for Zed panel integration
        enable_events: Whether to enable events.jsonl writing (default: True)

    Returns:
        LoopResult with final score and iteration history

    Example:
        result = await run_agentic_loop(
            task="Fix the authentication bug in auth.py",
            config=LoopConfig(max_iterations=3, quality_threshold=70.0),
        )
        print(f"Status: {result.status}, Score: {result.final_score}")
    """
    # Import SDK here to allow graceful handling if not installed
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
    except ImportError:
        raise ImportError(
            "Official Anthropic Agent SDK not installed. Install with: pip install claude-agent-sdk"
        )

    if config is None:
        config = LoopConfig()

    # Enforce hard max
    effective_max = min(config.max_iterations, config.hard_max_iterations)

    # Initialize evidence collector
    evidence = EvidenceCollector()
    sdk_hooks = create_sdk_hooks(evidence)

    # Initialize events tracker for Zed panel integration
    tracker = events_tracker
    if enable_events and tracker is None:
        tracker = EventsTracker()

    # Create and merge events hooks
    if enable_events and tracker is not None:
        events_hooks = create_events_hooks(evidence, tracker)
        sdk_hooks = merge_hooks(sdk_hooks, events_hooks)

        # Wrap on_iteration to also record events
        user_callback = on_iteration
        events_callback = create_iteration_callback(tracker)

        def combined_callback(result: IterationResult) -> None:
            events_callback(result)
            if user_callback:
                user_callback(result)

        on_iteration = combined_callback

    # Merge additional hooks if provided
    if additional_hooks:
        sdk_hooks = merge_hooks(sdk_hooks, additional_hooks)

    # Quality config
    quality_config = QualityConfig(quality_threshold=config.quality_threshold)

    # Loop state
    score_history: list[float] = []
    iteration_history: list[IterationResult] = []
    loop_start = datetime.now()

    termination_reason = TerminationReason.MAX_ITERATIONS

    for iteration in range(effective_max):
        iteration_start = datetime.now()
        logger.info(f"Starting iteration {iteration + 1}/{effective_max}")

        # Record iteration start for Zed panel
        if enable_events and tracker is not None:
            tracker.record_iteration_start(iteration, depth=0)

        # Reset evidence for this iteration
        evidence.reset()

        # Build prompt with context from previous iterations
        prompt = _build_iteration_prompt(task, iteration, iteration_history)

        # Execute via Official SDK with hooks
        messages = []
        try:
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    model=config.model,
                    max_turns=config.max_turns,
                    hooks=sdk_hooks,
                ),
            ):
                messages.append(message)
        except Exception as e:
            logger.error(f"SDK query failed: {e}")
            termination_reason = TerminationReason.ERROR
            break

        # Assess quality using evidence collected by hooks
        assessment = assess_quality(evidence, quality_config)
        score_history.append(assessment.score)

        # Record iteration result
        iteration_duration = (datetime.now() - iteration_start).total_seconds()
        iteration_result = IterationResult(
            iteration=iteration,
            score=assessment.score,
            improvements=assessment.improvements_needed,
            evidence=evidence.to_dict(),
            duration_seconds=iteration_duration,
            messages_count=len(messages),
        )
        iteration_history.append(iteration_result)

        logger.info(
            f"Iteration {iteration + 1} complete: "
            f"score={assessment.score:.1f}, passed={assessment.passed}"
        )

        # Call iteration callback if provided
        if on_iteration:
            on_iteration(iteration_result)

        # Check termination conditions
        if assessment.passed:
            termination_reason = TerminationReason.QUALITY_MET
            logger.info("Quality threshold met!")
            break

        if len(score_history) >= config.oscillation_window:
            if _is_oscillating(score_history[-config.oscillation_window :]):
                termination_reason = TerminationReason.OSCILLATION
                logger.warning("Oscillation detected, terminating loop")
                break

        if len(score_history) >= 2:
            if _is_stagnating(
                score_history[-2:], config.stagnation_threshold, config.min_improvement
            ):
                termination_reason = TerminationReason.STAGNATION
                logger.warning("Stagnation detected, terminating loop")
                break

        # Check timeout
        if config.timeout_seconds:
            elapsed = (datetime.now() - loop_start).total_seconds()
            if elapsed > config.timeout_seconds:
                termination_reason = TerminationReason.TIMEOUT
                logger.warning("Timeout exceeded")
                break

    # Build final result
    total_duration = (datetime.now() - loop_start).total_seconds()

    status = "success" if termination_reason == TerminationReason.QUALITY_MET else "terminated"

    # Record final state change for Zed panel
    if enable_events and tracker is not None:
        final_state = "completed" if status == "success" else "failed"
        tracker.record_state_change(
            old_state="running",
            new_state=final_state,
            reason=termination_reason.value,
        )
        tracker.flush()

    return LoopResult(
        status=status,
        reason=termination_reason,
        final_score=score_history[-1] if score_history else 0.0,
        total_iterations=len(iteration_history),
        iteration_history=iteration_history,
        total_duration_seconds=total_duration,
        evidence_summary=evidence.to_dict() if evidence else {},
    )


def _build_iteration_prompt(
    task: str,
    iteration: int,
    history: list[IterationResult],
) -> str:
    """
    Build prompt for an iteration with context from previous iterations.

    Args:
        task: Original task description
        iteration: Current iteration number (0-indexed)
        history: Results from previous iterations

    Returns:
        Prompt string with context
    """
    prompt = task

    if iteration > 0 and history:
        last = history[-1]
        prompt += "\n\n---\n"
        prompt += f"This is iteration {iteration + 1}. "
        prompt += f"Previous iteration scored {last.score:.1f}/100.\n"

        if last.improvements:
            prompt += "\nPrioritize these improvements:\n"
            for i, improvement in enumerate(last.improvements[:3], 1):
                prompt += f"{i}. {improvement}\n"

        # Add evidence context
        if last.evidence.get("tests_run"):
            passed = last.evidence.get("tests_passed", 0)
            failed = last.evidence.get("tests_failed", 0)
            prompt += f"\nTest status: {passed} passed, {failed} failed\n"

    return prompt


def _is_oscillating(scores: list[float], threshold: float = 5.0) -> bool:
    """
    Detect if scores are oscillating (up/down/up pattern).

    Args:
        scores: Recent score history (at least 3 values)
        threshold: Minimum delta to count as a direction change

    Returns:
        True if oscillating pattern detected
    """
    if len(scores) < 3:
        return False

    deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]

    # Check for alternating positive/negative deltas
    alternating = 0
    for i in range(len(deltas) - 1):
        if (deltas[i] > threshold and deltas[i + 1] < -threshold) or (
            deltas[i] < -threshold and deltas[i + 1] > threshold
        ):
            alternating += 1

    return alternating >= 1


def _is_stagnating(
    scores: list[float],
    variance_threshold: float,
    min_improvement: float,
) -> bool:
    """
    Detect if scores are stagnating (no meaningful improvement).

    Args:
        scores: Recent score history (at least 2 values)
        variance_threshold: Max variance to count as stagnant
        min_improvement: Minimum improvement needed

    Returns:
        True if stagnating
    """
    if len(scores) < 2:
        return False

    # Check if improvement is below threshold
    delta = scores[-1] - scores[-2]
    if delta < min_improvement:
        return True

    # Check variance
    variance = max(scores) - min(scores)
    return variance < variance_threshold


# Synchronous wrapper for non-async contexts
def run_agentic_loop_sync(
    task: str,
    config: LoopConfig | None = None,
    additional_hooks: dict[str, list[dict]] | None = None,
) -> LoopResult:
    """
    Synchronous wrapper for run_agentic_loop.

    Use this when you can't use async/await.
    """
    return asyncio.run(run_agentic_loop(task, config, additional_hooks))
