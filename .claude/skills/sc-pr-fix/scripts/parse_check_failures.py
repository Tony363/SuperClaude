#!/usr/bin/env python3
"""
Parse CI failure logs to extract actionable errors.

Supports multiple CI output formats:
- ESLint/TSLint
- pytest
- ruff/flake8
- Jest/Vitest
- Generic error patterns
- GitHub Actions annotations
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    """Types of CI failures."""

    LINT = "lint"
    TEST = "test"
    BUILD = "build"
    SECURITY = "security"
    TYPE_CHECK = "type_check"
    FORMAT = "format"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Risk level of fixing an error."""

    LOW = "low"  # Auto-fixable, no logic changes
    MEDIUM = "medium"  # May require review
    HIGH = "high"  # Core logic, security, requires careful review


@dataclass
class ParsedError:
    """A single parsed error from CI logs."""

    file: str
    line: int | None
    column: int | None
    rule: str | None
    message: str
    severity: str
    fixable: bool
    suggested_fix: str | None
    risk_level: RiskLevel

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity,
            "fixable": self.fixable,
            "suggested_fix": self.suggested_fix,
            "risk_level": self.risk_level.value,
        }


@dataclass
class ParsedFailure:
    """Parsed result from CI failure logs."""

    check_name: str
    failure_type: FailureType
    errors: list[ParsedError] = field(default_factory=list)
    summary: str = ""
    raw_log_excerpt: str = ""
    confidence: str = "medium"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "check_name": self.check_name,
            "failure_type": self.failure_type.value,
            "errors": [e.to_dict() for e in self.errors],
            "summary": self.summary,
            "raw_log_excerpt": self.raw_log_excerpt[:2000],  # Limit excerpt size
            "confidence": self.confidence,
            "error": self.error,
        }


def run_gh_command(args: list[str]) -> tuple[str, str, int]:
    """Run a gh CLI command and return stdout, stderr, returncode."""
    try:
        result = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except FileNotFoundError:
        return "", "gh CLI not found", 1


def get_run_logs(run_url: str) -> tuple[str, str | None]:
    """
    Fetch failed job logs from a GitHub Actions run.

    Args:
        run_url: URL to the GitHub Actions run (e.g., https://github.com/owner/repo/actions/runs/123)

    Returns:
        Tuple of (logs, error_message)
    """
    # Extract run ID from URL
    match = re.search(r"/runs/(\d+)", run_url)
    if not match:
        return "", f"Could not extract run ID from URL: {run_url}"

    run_id = match.group(1)

    # Get failed logs using gh CLI
    stdout, stderr, returncode = run_gh_command(["run", "view", run_id, "--log-failed"])

    if returncode != 0:
        # Try getting all logs if --log-failed fails
        stdout, stderr, returncode = run_gh_command(["run", "view", run_id, "--log"])
        if returncode != 0:
            return "", stderr.strip() or "Failed to fetch run logs"

    return stdout, None


def detect_failure_type(check_name: str, logs: str) -> FailureType:
    """Detect the type of failure from check name and logs."""
    name_lower = check_name.lower()

    if any(x in name_lower for x in ["lint", "eslint", "ruff", "flake8", "pylint"]):
        return FailureType.LINT
    if any(x in name_lower for x in ["test", "pytest", "jest", "vitest", "mocha"]):
        return FailureType.TEST
    if any(x in name_lower for x in ["build", "compile", "tsc"]):
        return FailureType.BUILD
    if any(x in name_lower for x in ["security", "snyk", "codeql", "semgrep"]):
        return FailureType.SECURITY
    if any(x in name_lower for x in ["type", "mypy", "pyright", "typescript"]):
        return FailureType.TYPE_CHECK
    if any(x in name_lower for x in ["format", "prettier", "black"]):
        return FailureType.FORMAT

    # Check logs for clues
    if "eslint" in logs.lower() or "ruff" in logs.lower():
        return FailureType.LINT
    if "pytest" in logs.lower() or "FAILED" in logs:
        return FailureType.TEST

    return FailureType.UNKNOWN


def parse_eslint_errors(logs: str) -> list[ParsedError]:
    """Parse ESLint-style errors from logs."""
    errors = []

    # Pattern: /path/to/file.ts:42:15: error Message (rule-name)
    # Or: /path/to/file.ts
    #       42:15  error  Message  rule-name
    pattern1 = re.compile(r"([^\s:]+):(\d+):(\d+):\s*(error|warning)\s+(.+?)\s+\(([^)]+)\)")
    pattern2 = re.compile(r"^\s*(\d+):(\d+)\s+(error|warning)\s+(.+?)\s{2,}(\S+)\s*$", re.MULTILINE)
    file_pattern = re.compile(r"^(/[^\s:]+\.\w+)$", re.MULTILINE)

    # Try pattern 1
    for match in pattern1.finditer(logs):
        errors.append(
            ParsedError(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                rule=match.group(6),
                message=match.group(5).strip(),
                severity=match.group(4),
                fixable=True,
                suggested_fix=f"Fix {match.group(6)} rule violation",
                risk_level=RiskLevel.LOW,
            )
        )

    # Try pattern 2 with file context
    current_file = None
    for line in logs.split("\n"):
        file_match = file_pattern.match(line)
        if file_match:
            current_file = file_match.group(1)
            continue

        if current_file:
            match = pattern2.match(line)
            if match:
                errors.append(
                    ParsedError(
                        file=current_file,
                        line=int(match.group(1)),
                        column=int(match.group(2)),
                        rule=match.group(5),
                        message=match.group(4).strip(),
                        severity=match.group(3),
                        fixable=True,
                        suggested_fix=f"Fix {match.group(5)} rule violation",
                        risk_level=RiskLevel.LOW,
                    )
                )

    return errors


def parse_ruff_errors(logs: str) -> list[ParsedError]:
    """Parse ruff/flake8 style errors from logs."""
    errors = []

    # Pattern: path/to/file.py:42:15: E501 Line too long
    pattern = re.compile(r"([^\s:]+\.py):(\d+):(\d+):\s*([A-Z]\d+)\s+(.+)")

    for match in pattern.finditer(logs):
        rule = match.group(4)
        errors.append(
            ParsedError(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                rule=rule,
                message=match.group(5).strip(),
                severity="error",
                fixable=rule.startswith(("E", "W", "F", "I")),  # Most are auto-fixable
                suggested_fix=f"Run `ruff check --fix` or fix {rule} manually",
                risk_level=RiskLevel.LOW,
            )
        )

    return errors


def parse_pytest_errors(logs: str) -> list[ParsedError]:
    """Parse pytest errors from logs."""
    errors = []

    # Pattern: FAILED tests/test_file.py::test_name - AssertionError
    failed_pattern = re.compile(r"FAILED\s+([^\s:]+)::(\S+)\s*[-:]\s*(.+)")

    # Also look for assertion errors with file:line
    assertion_pattern = re.compile(r"([^\s:]+\.py):(\d+):\s*(AssertionError|assert\s+.+)")

    for match in failed_pattern.finditer(logs):
        errors.append(
            ParsedError(
                file=match.group(1),
                line=None,
                column=None,
                rule=None,
                message=f"Test {match.group(2)} failed: {match.group(3)}",
                severity="error",
                fixable=False,
                suggested_fix="Review test logic and fix assertion",
                risk_level=RiskLevel.MEDIUM,
            )
        )

    for match in assertion_pattern.finditer(logs):
        errors.append(
            ParsedError(
                file=match.group(1),
                line=int(match.group(2)),
                column=None,
                rule=None,
                message=match.group(3),
                severity="error",
                fixable=False,
                suggested_fix="Review assertion and fix test or implementation",
                risk_level=RiskLevel.MEDIUM,
            )
        )

    return errors


def parse_jest_errors(logs: str) -> list[ParsedError]:
    """Parse Jest/Vitest errors from logs."""
    errors = []

    # Pattern: FAIL src/component.test.ts
    #   ● test name
    fail_pattern = re.compile(r"FAIL\s+([^\s]+)")
    test_pattern = re.compile(r"●\s+(.+)")

    # Look for expect assertions
    expect_pattern = re.compile(r"at\s+([^\s:]+):(\d+):(\d+)")

    current_file = None
    for line in logs.split("\n"):
        fail_match = fail_pattern.search(line)
        if fail_match:
            current_file = fail_match.group(1)
            continue

        test_match = test_pattern.search(line)
        if test_match and current_file:
            errors.append(
                ParsedError(
                    file=current_file,
                    line=None,
                    column=None,
                    rule=None,
                    message=f"Test failed: {test_match.group(1)}",
                    severity="error",
                    fixable=False,
                    suggested_fix="Review test expectations",
                    risk_level=RiskLevel.MEDIUM,
                )
            )

    return errors


def parse_typescript_errors(logs: str) -> list[ParsedError]:
    """Parse TypeScript compilation errors."""
    errors = []

    # Pattern: src/file.ts(42,15): error TS2345: Argument of type...
    pattern = re.compile(r"([^\s(]+)\((\d+),(\d+)\):\s*error\s+(TS\d+):\s*(.+)")

    for match in pattern.finditer(logs):
        errors.append(
            ParsedError(
                file=match.group(1),
                line=int(match.group(2)),
                column=int(match.group(3)),
                rule=match.group(4),
                message=match.group(5).strip(),
                severity="error",
                fixable=False,
                suggested_fix="Fix type error",
                risk_level=RiskLevel.MEDIUM,
            )
        )

    return errors


def parse_generic_errors(logs: str) -> list[ParsedError]:
    """Parse generic error patterns as fallback."""
    errors = []

    # Generic patterns
    patterns = [
        # file:line:col: error: message
        re.compile(r"([^\s:]+):(\d+):(\d+):\s*(?:error|Error):\s*(.+)"),
        # file:line: error: message
        re.compile(r"([^\s:]+):(\d+):\s*(?:error|Error):\s*(.+)"),
        # Error: message at file:line
        re.compile(r"(?:Error|error):\s*(.+?)\s+at\s+([^\s:]+):(\d+)"),
    ]

    for pattern in patterns:
        for match in pattern.finditer(logs):
            groups = match.groups()
            if len(groups) == 4:
                file, line, col, msg = groups
                errors.append(
                    ParsedError(
                        file=file,
                        line=int(line),
                        column=int(col),
                        rule=None,
                        message=msg.strip(),
                        severity="error",
                        fixable=False,
                        suggested_fix=None,
                        risk_level=RiskLevel.MEDIUM,
                    )
                )
            elif len(groups) == 3:
                if groups[0].endswith((".py", ".ts", ".js", ".tsx", ".jsx")):
                    file, line, msg = groups
                    col = None
                else:
                    msg, file, line = groups
                    col = None
                errors.append(
                    ParsedError(
                        file=file,
                        line=int(line),
                        column=int(col) if col else None,
                        rule=None,
                        message=msg.strip(),
                        severity="error",
                        fixable=False,
                        suggested_fix=None,
                        risk_level=RiskLevel.MEDIUM,
                    )
                )

    return errors


def parse_failure_logs(
    check_name: str,
    run_url: str | None = None,
    logs: str | None = None,
) -> ParsedFailure:
    """
    Parse CI failure logs to extract actionable errors.

    Args:
        check_name: Name of the failed check
        run_url: URL to the GitHub Actions run (optional if logs provided)
        logs: Raw log content (optional if run_url provided)

    Returns:
        ParsedFailure with extracted errors
    """
    # Fetch logs if not provided
    if logs is None:
        if run_url is None:
            return ParsedFailure(
                check_name=check_name,
                failure_type=FailureType.UNKNOWN,
                error="No run_url or logs provided",
            )
        logs, error = get_run_logs(run_url)
        if error:
            return ParsedFailure(
                check_name=check_name,
                failure_type=FailureType.UNKNOWN,
                error=error,
            )

    # Detect failure type
    failure_type = detect_failure_type(check_name, logs)

    # Parse based on failure type
    errors: list[ParsedError] = []

    if failure_type == FailureType.LINT:
        errors.extend(parse_eslint_errors(logs))
        errors.extend(parse_ruff_errors(logs))
    elif failure_type == FailureType.TEST:
        errors.extend(parse_pytest_errors(logs))
        errors.extend(parse_jest_errors(logs))
    elif failure_type in (FailureType.BUILD, FailureType.TYPE_CHECK):
        errors.extend(parse_typescript_errors(logs))

    # Always try generic parsing as fallback
    if not errors:
        errors.extend(parse_generic_errors(logs))

    # Deduplicate errors
    seen = set()
    unique_errors = []
    for e in errors:
        key = (e.file, e.line, e.message)
        if key not in seen:
            seen.add(key)
            unique_errors.append(e)

    # Generate summary
    if unique_errors:
        summary = f"{len(unique_errors)} error(s) in {len(set(e.file for e in unique_errors))} file(s)"
    else:
        summary = "Could not parse specific errors from logs"

    # Determine confidence
    confidence = "high" if unique_errors else "low"

    return ParsedFailure(
        check_name=check_name,
        failure_type=failure_type,
        errors=unique_errors,
        summary=summary,
        raw_log_excerpt=logs[:2000] if logs else "",
        confidence=confidence,
    )


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse CI failure logs")
    parser.add_argument("check_name", help="Name of the failed check")
    parser.add_argument("--url", help="GitHub Actions run URL")
    parser.add_argument("--logs-file", help="File containing raw logs")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    logs = None
    if args.logs_file:
        with open(args.logs_file) as f:
            logs = f.read()

    result = parse_failure_logs(args.check_name, args.url, logs)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Check: {result.check_name}")
        print(f"Type: {result.failure_type.value}")
        print(f"Summary: {result.summary}")
        print(f"Confidence: {result.confidence}")
        if result.error:
            print(f"Error: {result.error}")
        if result.errors:
            print("\nErrors:")
            for e in result.errors:
                loc = f"{e.file}:{e.line}" if e.line else e.file
                print(f"  - {loc}: {e.message}")
                if e.suggested_fix:
                    print(f"    Fix: {e.suggested_fix}")

    return 0 if not result.error else 1


if __name__ == "__main__":
    sys.exit(main())
