#!/usr/bin/env python3
"""
Check PR status via GitHub CLI.

Polls PR check status and returns structured results for the fix loop.
Uses `gh pr checks` to query GitHub Actions status.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any


class CheckState(str, Enum):
    """GitHub check states."""

    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAITING = "waiting"
    REQUESTED = "requested"


class CheckConclusion(str, Enum):
    """GitHub check conclusions."""

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"
    STALE = "stale"
    STARTUP_FAILURE = "startup_failure"


@dataclass
class CheckResult:
    """Result of a single CI check."""

    name: str
    state: str
    conclusion: str | None
    url: str | None

    @property
    def is_passed(self) -> bool:
        """Check if this check passed."""
        return self.conclusion == CheckConclusion.SUCCESS.value

    @property
    def is_failed(self) -> bool:
        """Check if this check failed."""
        return self.conclusion in (
            CheckConclusion.FAILURE.value,
            CheckConclusion.TIMED_OUT.value,
            CheckConclusion.STARTUP_FAILURE.value,
        )

    @property
    def is_pending(self) -> bool:
        """Check if this check is still running."""
        return self.state in (
            CheckState.PENDING.value,
            CheckState.QUEUED.value,
            CheckState.IN_PROGRESS.value,
            CheckState.WAITING.value,
            CheckState.REQUESTED.value,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "state": self.state,
            "conclusion": self.conclusion,
            "url": self.url,
            "is_passed": self.is_passed,
            "is_failed": self.is_failed,
            "is_pending": self.is_pending,
        }


@dataclass
class PRCheckStatus:
    """Overall PR check status."""

    pr_number: int
    checks: list[CheckResult]
    all_passed: bool
    any_failed: bool
    any_pending: bool
    passed_count: int
    failed_count: int
    pending_count: int
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        status = "passed" if self.all_passed else "failed" if self.any_failed else "pending"
        return {
            "pr_number": self.pr_number,
            "status": status,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "any_failed": self.any_failed,
            "any_pending": self.any_pending,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "pending_count": self.pending_count,
            "error": self.error,
        }


def run_gh_command(args: list[str]) -> tuple[str, str, int]:
    """Run a gh CLI command and return stdout, stderr, returncode."""
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except FileNotFoundError:
        return "", "gh CLI not found. Install from https://cli.github.com/", 1


def get_pr_checks(pr_number: int, repo: str | None = None) -> PRCheckStatus:
    """
    Get check status for a PR.

    Args:
        pr_number: The PR number to check
        repo: Optional repo in owner/repo format (uses current repo if not specified)

    Returns:
        PRCheckStatus with all check results
    """
    args = ["pr", "checks", str(pr_number), "--json", "name,state,conclusion,detailsUrl"]
    if repo:
        args.extend(["--repo", repo])

    stdout, stderr, returncode = run_gh_command(args)

    if returncode != 0:
        return PRCheckStatus(
            pr_number=pr_number,
            checks=[],
            all_passed=False,
            any_failed=False,
            any_pending=False,
            passed_count=0,
            failed_count=0,
            pending_count=0,
            error=stderr.strip() or "Failed to get PR checks",
        )

    try:
        checks_data = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError as e:
        return PRCheckStatus(
            pr_number=pr_number,
            checks=[],
            all_passed=False,
            any_failed=False,
            any_pending=False,
            passed_count=0,
            failed_count=0,
            pending_count=0,
            error=f"Failed to parse gh output: {e}",
        )

    checks = [
        CheckResult(
            name=c.get("name", "unknown"),
            state=c.get("state", "unknown"),
            conclusion=c.get("conclusion"),
            url=c.get("detailsUrl"),
        )
        for c in checks_data
    ]

    passed = [c for c in checks if c.is_passed]
    failed = [c for c in checks if c.is_failed]
    pending = [c for c in checks if c.is_pending]

    return PRCheckStatus(
        pr_number=pr_number,
        checks=checks,
        all_passed=len(checks) > 0 and len(passed) == len(checks),
        any_failed=len(failed) > 0,
        any_pending=len(pending) > 0,
        passed_count=len(passed),
        failed_count=len(failed),
        pending_count=len(pending),
    )


def poll_pr_checks(
    pr_number: int,
    repo: str | None = None,
    poll_interval: int = 30,
    timeout: int = 600,
    initial_wait: int = 10,
) -> PRCheckStatus:
    """
    Poll PR checks until all complete or timeout.

    Args:
        pr_number: The PR number to check
        repo: Optional repo in owner/repo format
        poll_interval: Seconds between polls (default: 30)
        timeout: Max seconds to wait (default: 600 = 10 min)
        initial_wait: Seconds to wait before first check (default: 10)

    Returns:
        Final PRCheckStatus after polling completes
    """
    # Initial wait to let CI start
    if initial_wait > 0:
        time.sleep(initial_wait)

    start_time = time.time()

    while True:
        status = get_pr_checks(pr_number, repo)

        # Exit on error
        if status.error:
            return status

        # Exit if no pending checks
        if not status.any_pending:
            return status

        # Check timeout
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            status.error = f"Timeout after {timeout}s waiting for checks to complete"
            return status

        # Wait and poll again
        time.sleep(poll_interval)


def get_failed_checks(status: PRCheckStatus) -> list[CheckResult]:
    """Extract only failed checks from status."""
    return [c for c in status.checks if c.is_failed]


def format_status_summary(status: PRCheckStatus) -> str:
    """Format a human-readable status summary."""
    lines = [f"PR #{status.pr_number} Check Status:"]

    if status.error:
        lines.append(f"  Error: {status.error}")
        return "\n".join(lines)

    if status.all_passed:
        lines.append(f"  All {status.passed_count} checks passed!")
    else:
        lines.append(f"  Passed: {status.passed_count}")
        lines.append(f"  Failed: {status.failed_count}")
        lines.append(f"  Pending: {status.pending_count}")

        if status.any_failed:
            lines.append("\n  Failed checks:")
            for check in status.checks:
                if check.is_failed:
                    lines.append(f"    - {check.name}")
                    if check.url:
                        lines.append(f"      URL: {check.url}")

    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check PR status via GitHub CLI")
    parser.add_argument("pr_number", type=int, help="PR number to check")
    parser.add_argument("--repo", help="Repository in owner/repo format")
    parser.add_argument("--poll", action="store_true", help="Poll until checks complete")
    parser.add_argument("--poll-interval", type=int, default=30, help="Poll interval in seconds")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.poll:
        status = poll_pr_checks(
            args.pr_number,
            args.repo,
            args.poll_interval,
            args.timeout,
        )
    else:
        status = get_pr_checks(args.pr_number, args.repo)

    if args.json:
        print(json.dumps(status.to_dict(), indent=2))
    else:
        print(format_status_summary(status))

    # Exit code: 0 if all passed, 1 if any failed, 2 if error
    if status.error:
        return 2
    if status.any_failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
