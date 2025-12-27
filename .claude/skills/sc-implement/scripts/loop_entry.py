#!/usr/bin/env python3
"""
Loop Entry Point for SuperClaude Skills.

This script is invoked by Claude Code when the --loop flag is detected
on /sc:implement commands. It initializes and runs the loop orchestrator.

Usage:
    python loop_entry.py '{"task": "...", "max_iterations": 3, "pal_review": true}'

Input (JSON):
    {
        "task": "Implement user authentication API",
        "max_iterations": 3,
        "quality_threshold": 70.0,
        "pal_review": true,
        "pal_model": "gpt-5"
    }

Output (JSON):
    {
        "loop_completed": true,
        "iterations": 2,
        "termination_reason": "quality_threshold_met",
        "final_score": 85.0,
        "passed": true,
        "history": [...]
    }

The script works as a signal generator - Claude Code processes the
output and invokes the appropriate skills for each iteration.
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add core to path
sys.path.insert(0, str(Path(__file__).parents[4]))

try:
    from core.loop_orchestrator import LoopOrchestrator, create_skill_invoker_signal
    from core.types import LoopConfig
except ImportError:
    # Fallback for when core module is not available
    # This provides a graceful degradation
    LoopOrchestrator = None
    LoopConfig = None
    create_skill_invoker_signal = None


def parse_context(raw_context: str) -> dict[str, Any]:
    """Parse JSON context from command line argument."""
    try:
        return json.loads(raw_context)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}


def build_config(context: dict[str, Any]) -> "LoopConfig":
    """Build LoopConfig from context dict."""
    if LoopConfig is None:
        raise RuntimeError("core module not available")

    return LoopConfig(
        max_iterations=context.get("max_iterations", 3),
        quality_threshold=context.get("quality_threshold", 70.0),
        min_improvement=context.get("min_improvement", 5.0),
        pal_review_enabled=context.get("pal_review", True),
        pal_model=context.get("pal_model", "gpt-5"),
        timeout_seconds=context.get("timeout_seconds"),
    )


def create_mock_skill_invoker(context: dict[str, Any]):
    """
    Create a mock skill invoker for signal generation.

    In actual use, Claude Code processes the signals and invokes
    the skills. This mock returns the signal structure that Claude
    Code should process.

    Args:
        context: Task context

    Returns:
        Callable that returns skill invocation signals
    """
    iteration = [0]  # Mutable counter for closure

    def invoker(ctx: dict[str, Any]) -> dict[str, Any]:
        current_iter = iteration[0]
        iteration[0] += 1

        # Return signal for Claude Code to process
        return {
            "signal": "invoke_skill",
            "iteration": current_iter,
            "skill": "sc-implement",
            "context": ctx,
            "instruction": (
                f"Execute iteration {current_iter + 1}: "
                f"Implement with focus on: {ctx.get('improvements_needed', ['initial implementation'])}"
            ),
            # These would be filled by actual skill execution:
            "changes": [],
            "tests": {"ran": False},
            "lint": {"ran": False},
            "changed_files": [],
        }

    return invoker


def run_loop(context: dict[str, Any]) -> dict[str, Any]:
    """
    Run the agentic loop with given context.

    Args:
        context: Loop configuration and task context

    Returns:
        Loop result as dict
    """
    if LoopOrchestrator is None:
        return {
            "error": "core module not available",
            "fallback": True,
            "signal": create_signal_only_response(context),
        }

    config = build_config(context)
    orchestrator = LoopOrchestrator(config)

    # Create skill invoker (Claude Code will process signals)
    skill_invoker = create_mock_skill_invoker(context)

    # Run the loop
    result = orchestrator.run(context, skill_invoker)

    return result.to_dict()


def create_signal_only_response(context: dict[str, Any]) -> dict[str, Any]:
    """
    Create a signal-only response when core module unavailable.

    This allows Claude Code to still process the loop request
    even if the Python orchestrator can't be loaded.

    Args:
        context: Task context

    Returns:
        Signal structure for Claude Code
    """
    return {
        "action": "execute_loop",
        "max_iterations": context.get("max_iterations", 3),
        "quality_threshold": context.get("quality_threshold", 70.0),
        "pal_review": context.get("pal_review", True),
        "instruction": (
            "Execute agentic loop manually:\n"
            "1. Run sc-implement skill\n"
            "2. Assess quality (target: 70+)\n"
            "3. If below threshold, identify improvements and repeat\n"
            "4. Stop after 5 iterations max or when threshold met\n"
            "5. Use PAL MCP codereview between iterations"
        ),
        "safety": {
            "hard_max_iterations": 5,
            "detect_oscillation": True,
            "detect_stagnation": True,
        },
    }


def main():
    """Main entry point for script execution."""
    if len(sys.argv) < 2:
        # No context provided - return usage info
        print(
            json.dumps(
                {
                    "error": "No context provided",
                    "usage": 'python loop_entry.py \'{"task": "...", "max_iterations": 3}\'',
                    "signal": create_signal_only_response({}),
                },
                indent=2,
            )
        )
        sys.exit(1)

    # Parse context
    context = parse_context(sys.argv[1])

    if "error" in context:
        print(json.dumps(context, indent=2))
        sys.exit(1)

    # Run the loop
    result = run_loop(context)

    # Output result for Claude Code to process
    print(json.dumps(result, indent=2))

    # Exit with appropriate code
    if result.get("passed") or result.get("loop_completed"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
