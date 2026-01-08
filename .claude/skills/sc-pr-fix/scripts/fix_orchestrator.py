#!/usr/bin/env python3
"""
Fix orchestrator for PR CI failures.

Coordinates the iterative fix loop with:
- Safety mechanisms (max iterations, stagnation detection)
- Interactive prompts for user confirmation
- Integration with PAL MCP for complex fixes
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from check_pr_status import CheckResult, PRCheckStatus, get_pr_checks
from parse_check_failures import (
    FailureType,
    ParsedError,
    ParsedFailure,
    RiskLevel,
    parse_failure_logs,
)


class TerminationReason(str, Enum):
    """Reasons for terminating the fix loop."""

    ALL_PASSED = "all_passed"
    MAX_ATTEMPTS = "max_attempts"
    STAGNATION = "stagnation"
    OSCILLATION = "oscillation"
    USER_ABORT = "user_abort"
    ERROR = "error"


class FixAction(str, Enum):
    """User actions during fix loop."""

    APPLY = "apply"
    SKIP = "skip"
    VIEW_LOG = "view_log"
    DEBUG_PAL = "debug_pal"
    QUIT = "quit"


@dataclass
class FixAttempt:
    """Record of a single fix attempt."""

    iteration: int
    check_name: str
    errors_count: int
    fix_type: str  # auto or manual
    files_changed: list[str]
    user_approved: bool
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "iteration": self.iteration,
            "check_name": self.check_name,
            "errors_count": self.errors_count,
            "fix_type": self.fix_type,
            "files_changed": self.files_changed,
            "user_approved": self.user_approved,
            "success": self.success,
            "timestamp": self.timestamp,
        }


@dataclass
class FixLoopState:
    """State of the fix loop."""

    pr_number: int
    repo: str | None
    max_attempts: int
    auto_fix: bool
    current_iteration: int = 0
    fixes_applied: list[FixAttempt] = field(default_factory=list)
    error_history: list[str] = field(default_factory=list)
    skipped_checks: list[str] = field(default_factory=list)
    termination_reason: TerminationReason | None = None
    final_status: PRCheckStatus | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "pr_number": self.pr_number,
            "repo": self.repo,
            "max_attempts": self.max_attempts,
            "auto_fix": self.auto_fix,
            "current_iteration": self.current_iteration,
            "fixes_applied": [f.to_dict() for f in self.fixes_applied],
            "error_history": self.error_history,
            "skipped_checks": self.skipped_checks,
            "termination_reason": self.termination_reason.value if self.termination_reason else None,
            "final_status": self.final_status.to_dict() if self.final_status else None,
        }


# Constants
HARD_MAX_ITERATIONS = 5
STAGNATION_THRESHOLD = 3


def detect_stagnation(error_history: list[str], threshold: int = STAGNATION_THRESHOLD) -> bool:
    """
    Detect if the same error has occurred too many times.

    Args:
        error_history: List of error signatures from each iteration
        threshold: Number of times same error = stagnation

    Returns:
        True if stagnation detected
    """
    if len(error_history) < threshold:
        return False

    # Check if last N errors are the same
    recent = error_history[-threshold:]
    return len(set(recent)) == 1


def detect_oscillation(error_history: list[str], window: int = 4) -> bool:
    """
    Detect if errors are oscillating (fix-revert-fix pattern).

    Args:
        error_history: List of error signatures
        window: Window size to check for oscillation

    Returns:
        True if oscillation detected
    """
    if len(error_history) < window:
        return False

    recent = error_history[-window:]
    # Check for A-B-A-B pattern
    if len(set(recent)) == 2:
        pattern = recent[0:2]
        expected = pattern * (window // 2)
        return recent == expected[: len(recent)]

    return False


def get_error_signature(failures: list[ParsedFailure]) -> str:
    """Generate a signature for the current error state."""
    if not failures:
        return "no_errors"

    errors = []
    for failure in failures:
        for error in failure.errors:
            errors.append(f"{error.file}:{error.line}:{error.rule or error.message[:50]}")

    errors.sort()
    return "|".join(errors[:10])  # Limit signature size


def should_auto_fix(failure: ParsedFailure, errors: list[ParsedError]) -> bool:
    """
    Determine if errors can be auto-fixed without user confirmation.

    Auto-fix is allowed for:
    - LOW risk level errors
    - LINT and FORMAT failure types
    - All errors marked as fixable
    """
    if failure.failure_type not in (FailureType.LINT, FailureType.FORMAT):
        return False

    return all(e.risk_level == RiskLevel.LOW and e.fixable for e in errors)


def format_prompt(
    failure: ParsedFailure,
    iteration: int,
    max_attempts: int,
) -> str:
    """Format the interactive prompt for user."""
    lines = [
        "=" * 80,
        f"CI Check Failed: {failure.check_name}".ljust(60) + f"Attempt {iteration} of {max_attempts}".rjust(20),
        "=" * 80,
        "",
        "Error Summary:",
    ]

    for error in failure.errors[:5]:  # Show first 5 errors
        loc = f"  - {error.file}"
        if error.line:
            loc += f":{error.line}"
        if error.column:
            loc += f":{error.column}"
        loc += f" - {error.message}"
        if error.rule:
            loc += f" ({error.rule})"
        lines.append(loc)

    if len(failure.errors) > 5:
        lines.append(f"  ... and {len(failure.errors) - 5} more errors")

    lines.append("")

    if failure.errors and failure.errors[0].suggested_fix:
        lines.append("Proposed Fix:")
        for i, error in enumerate(failure.errors[:3], 1):
            if error.suggested_fix:
                lines.append(f"  {i}. {error.suggested_fix}")
        lines.append("")

    # Risk level
    risk_levels = [e.risk_level for e in failure.errors]
    highest_risk = max(risk_levels, key=lambda r: ["low", "medium", "high"].index(r.value), default=RiskLevel.LOW)
    risk_desc = {
        RiskLevel.LOW: "LOW (auto-fixable lint errors)",
        RiskLevel.MEDIUM: "MEDIUM (may require review)",
        RiskLevel.HIGH: "HIGH (core logic changes)",
    }
    lines.append(f"Risk Level: {risk_desc.get(highest_risk, highest_risk.value)}")
    lines.append("")
    lines.append("-" * 80)

    # Options based on risk level
    if highest_risk == RiskLevel.HIGH:
        lines.append("[A]pply fix  [S]kip check  [V]iew full log  [D]ebug with PAL  [Q]uit")
    else:
        lines.append("[A]pply fix  [S]kip check  [V]iew full log  [Q]uit")

    lines.append("> ")

    return "\n".join(lines)


def parse_user_input(user_input: str) -> FixAction:
    """Parse user input to a fix action."""
    user_input = user_input.strip().lower()

    if user_input in ("a", "apply", "yes", "y"):
        return FixAction.APPLY
    if user_input in ("s", "skip"):
        return FixAction.SKIP
    if user_input in ("v", "view", "log"):
        return FixAction.VIEW_LOG
    if user_input in ("d", "debug", "pal"):
        return FixAction.DEBUG_PAL
    if user_input in ("q", "quit", "exit", "abort"):
        return FixAction.QUIT

    return FixAction.APPLY  # Default to apply


def generate_fix_signal(
    state: FixLoopState,
    failure: ParsedFailure,
    action: FixAction,
) -> dict[str, Any]:
    """
    Generate a signal for Claude Code to process.

    This is the interface between the orchestrator and Claude Code.
    Claude Code will read this signal and perform the actual fix.
    """
    return {
        "type": "fix_signal",
        "action": action.value,
        "iteration": state.current_iteration,
        "check_name": failure.check_name,
        "failure_type": failure.failure_type.value,
        "errors": [e.to_dict() for e in failure.errors],
        "files_to_fix": list(set(e.file for e in failure.errors)),
        "suggested_fixes": [e.suggested_fix for e in failure.errors if e.suggested_fix],
        "use_pal_debug": action == FixAction.DEBUG_PAL,
        "state": {
            "pr_number": state.pr_number,
            "current_iteration": state.current_iteration,
            "max_attempts": state.max_attempts,
            "error_history_length": len(state.error_history),
        },
    }


def run_fix_loop(
    pr_number: int,
    repo: str | None = None,
    max_attempts: int = HARD_MAX_ITERATIONS,
    auto_fix: bool = False,
    poll_interval: int = 30,
) -> FixLoopState:
    """
    Run the fix loop until all checks pass or termination condition met.

    This is a generator-style function that yields signals for Claude Code
    to process. In actual use, Claude Code orchestrates this loop.

    Args:
        pr_number: PR number to monitor
        repo: Optional repo in owner/repo format
        max_attempts: Maximum fix iterations (capped at HARD_MAX_ITERATIONS)
        auto_fix: Whether to auto-apply low-risk fixes
        poll_interval: Seconds between CI status polls

    Returns:
        Final FixLoopState
    """
    # Enforce hard cap
    max_attempts = min(max_attempts, HARD_MAX_ITERATIONS)

    state = FixLoopState(
        pr_number=pr_number,
        repo=repo,
        max_attempts=max_attempts,
        auto_fix=auto_fix,
    )

    while state.current_iteration < max_attempts:
        state.current_iteration += 1

        # Get current PR status
        status = get_pr_checks(pr_number, repo)

        if status.error:
            state.termination_reason = TerminationReason.ERROR
            state.final_status = status
            break

        # Check if all passed
        if status.all_passed:
            state.termination_reason = TerminationReason.ALL_PASSED
            state.final_status = status
            break

        # Check if any failed
        if not status.any_failed:
            # Still pending, would need to wait
            # In real use, Claude Code handles polling
            continue

        # Get failed checks
        failed_checks = [c for c in status.checks if c.is_failed]

        # Parse failures
        failures = []
        for check in failed_checks:
            if check.name in state.skipped_checks:
                continue
            failure = parse_failure_logs(check.name, check.url)
            if failure.errors:
                failures.append(failure)

        if not failures:
            # No parseable failures
            state.termination_reason = TerminationReason.ERROR
            state.final_status = status
            break

        # Get error signature for stagnation detection
        signature = get_error_signature(failures)
        state.error_history.append(signature)

        # Check termination conditions
        if detect_stagnation(state.error_history):
            state.termination_reason = TerminationReason.STAGNATION
            state.final_status = status
            break

        if detect_oscillation(state.error_history):
            state.termination_reason = TerminationReason.OSCILLATION
            state.final_status = status
            break

        # Process each failure
        # In real use, this is where Claude Code takes over
        # This is just the signal generation
        for failure in failures:
            # Check if auto-fix is applicable
            if auto_fix and should_auto_fix(failure, failure.errors):
                # Generate auto-fix signal
                signal = generate_fix_signal(state, failure, FixAction.APPLY)
                signal["auto_applied"] = True
                # In real use, Claude Code would process this signal
                # and perform the fix
            else:
                # Generate prompt signal for user interaction
                prompt = format_prompt(failure, state.current_iteration, max_attempts)
                signal = generate_fix_signal(state, failure, FixAction.APPLY)
                signal["prompt"] = prompt
                signal["requires_user_input"] = True

            # Record attempt (in real use, this is updated after Claude Code applies fix)
            attempt = FixAttempt(
                iteration=state.current_iteration,
                check_name=failure.check_name,
                errors_count=len(failure.errors),
                fix_type="auto" if auto_fix and should_auto_fix(failure, failure.errors) else "manual",
                files_changed=list(set(e.file for e in failure.errors)),
                user_approved=True,  # Would be set by user input
                success=False,  # Would be set after fix verification
            )
            state.fixes_applied.append(attempt)

    # If we exited due to max attempts
    if state.termination_reason is None:
        state.termination_reason = TerminationReason.MAX_ATTEMPTS
        state.final_status = get_pr_checks(pr_number, repo)

    return state


def format_final_summary(state: FixLoopState) -> str:
    """Format final summary of the fix loop."""
    lines = [
        "=" * 80,
        "PR Fix Loop Complete",
        "=" * 80,
        "",
        f"PR: #{state.pr_number}",
        f"Iterations: {state.current_iteration}/{state.max_attempts}",
        f"Termination: {state.termination_reason.value if state.termination_reason else 'unknown'}",
        "",
    ]

    if state.termination_reason == TerminationReason.ALL_PASSED:
        lines.append("All CI checks passed! PR is ready for review.")
    elif state.termination_reason == TerminationReason.MAX_ATTEMPTS:
        lines.append("Max fix attempts reached. Manual intervention required.")
    elif state.termination_reason == TerminationReason.STAGNATION:
        lines.append("Same error persists after multiple attempts. Aborting.")
    elif state.termination_reason == TerminationReason.OSCILLATION:
        lines.append("Fix-revert pattern detected. Aborting to prevent infinite loop.")
    elif state.termination_reason == TerminationReason.USER_ABORT:
        lines.append("Fix loop aborted by user.")
    elif state.termination_reason == TerminationReason.ERROR:
        lines.append("Error occurred during fix loop.")

    if state.fixes_applied:
        lines.append("")
        lines.append(f"Fixes Applied: {len(state.fixes_applied)}")
        for fix in state.fixes_applied:
            lines.append(f"  - {fix.check_name}: {fix.errors_count} error(s) in {len(fix.files_changed)} file(s)")

    if state.skipped_checks:
        lines.append("")
        lines.append(f"Skipped Checks: {', '.join(state.skipped_checks)}")

    if state.final_status:
        lines.append("")
        lines.append("Final Status:")
        lines.append(f"  Passed: {state.final_status.passed_count}")
        lines.append(f"  Failed: {state.final_status.failed_count}")
        lines.append(f"  Pending: {state.final_status.pending_count}")

    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrate PR fix loop")
    parser.add_argument("pr_number", type=int, help="PR number to fix")
    parser.add_argument("--repo", help="Repository in owner/repo format")
    parser.add_argument("--max-attempts", type=int, default=5, help="Max fix iterations")
    parser.add_argument("--auto-fix", action="store_true", help="Auto-apply low-risk fixes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    state = run_fix_loop(
        args.pr_number,
        args.repo,
        args.max_attempts,
        args.auto_fix,
    )

    if args.json:
        print(json.dumps(state.to_dict(), indent=2))
    else:
        print(format_final_summary(state))

    # Exit codes
    if state.termination_reason == TerminationReason.ALL_PASSED:
        return 0
    if state.termination_reason == TerminationReason.USER_ABORT:
        return 130  # Standard interrupt code
    return 1


if __name__ == "__main__":
    sys.exit(main())
