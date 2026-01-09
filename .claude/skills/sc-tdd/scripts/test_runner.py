#!/usr/bin/env python3
"""Test Runner - Execute tests and classify outcomes.

NOTE: Uses `from __future__ import annotations` for Python 3.9 compatibility
with PEP 604 union syntax (int | str) and generic types (list[str]).

Executes test commands with timeout, parses framework-specific output,
and classifies outcomes as PASS, SEMANTIC_FAIL, NON_SEMANTIC_FAIL, or NO_TESTS.

Exit Codes:
    0 - Tests executed successfully (classification in output)
    3 - Execution error (timeout, command not found, etc.)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class TestOutcome(Enum):
    """Test execution outcome classifications."""

    PASS = "PASS"
    SEMANTIC_FAIL = "SEMANTIC_FAIL"
    NON_SEMANTIC_FAIL = "NON_SEMANTIC_FAIL"
    NO_TESTS = "NO_TESTS"
    TIMEOUT = "TIMEOUT"


@dataclass
class TestResult:
    """Normalized test execution result."""

    framework: str
    cmd: list[str]
    cwd: str
    timeout_s: int
    exit_code: int | str
    duration_ms: int
    stdout: str
    stderr: str
    outcome: str
    signals: list[str]
    excerpt_hash: str


class TestRunner:
    """Execute and classify test results."""

    # Classification patterns
    PYTEST_NO_TESTS = ["collected 0 items", "no tests ran"]
    PYTEST_NON_SEMANTIC = [
        "SyntaxError",
        "ImportError",
        "ModuleNotFoundError",
        "ERROR collecting",
        "usage: pytest",
        "INTERNALERROR>",
    ]
    PYTEST_SEMANTIC = [
        "E   AssertionError",
        "E   assert ",
        "E   Expected",
        ">       assert",
        "== FAILURES ==",
    ]

    JEST_NO_TESTS = ["No tests found", "No test files found"]
    JEST_NON_SEMANTIC = [
        "SyntaxError:",
        "Cannot find module",
        "Module not found",
        "TypeScript error",
        "Jest encountered an unexpected token",
    ]
    JEST_SEMANTIC = ["FAIL ", "●", "AssertionError", "Expected"]

    VITEST_NO_TESTS = JEST_NO_TESTS
    VITEST_NON_SEMANTIC = JEST_NON_SEMANTIC
    VITEST_SEMANTIC = JEST_SEMANTIC

    GO_NO_TESTS = ["[no test files]", "no test files"]
    GO_NON_SEMANTIC = ["build failed", "cannot find package", "found packages", "go: downloading"]
    GO_SEMANTIC = ["--- FAIL:", "FAIL\t"]

    CARGO_NO_TESTS = ["running 0 tests", "test result: ok. 0 passed; 0 failed"]
    CARGO_NON_SEMANTIC = [
        "error: could not compile",
        "error[E",
        "failed to run custom build command",
    ]
    CARGO_SEMANTIC = ["test result: FAILED", "... FAILED", "thread '", "panicked at"]

    def __init__(self, allow_snapshots: bool = False):
        """Initialize test runner.

        Args:
            allow_snapshots: Whether to treat snapshot mismatches as semantic failures
        """
        self.allow_snapshots = allow_snapshots

    def run_command(
        self, cmd: list[str], cwd: str | Path, timeout_s: int = 120, framework: str = "unknown"
    ) -> TestResult:
        """Execute test command with timeout.

        Args:
            cmd: Command argv list
            cwd: Working directory
            timeout_s: Timeout in seconds
            framework: Framework name for classification

        Returns:
            TestResult with classification
        """
        cwd = Path(cwd).resolve()
        start_time = time.time()

        try:
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_s)
            duration_ms = int((time.time() - start_time) * 1000)
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr

        except subprocess.TimeoutExpired as e:
            duration_ms = int(timeout_s * 1000)
            stdout = e.stdout.decode() if e.stdout else ""
            stderr = e.stderr.decode() if e.stderr else ""
            exit_code = "timeout"

        except Exception as e:
            return TestResult(
                framework=framework,
                cmd=cmd,
                cwd=str(cwd),
                timeout_s=timeout_s,
                exit_code=-1,
                duration_ms=0,
                stdout="",
                stderr=str(e),
                outcome=TestOutcome.NON_SEMANTIC_FAIL.value,
                signals=["execution_error"],
                excerpt_hash="",
            )

        # Classify outcome
        combined_output = stdout + "\n" + stderr
        outcome, signals = self._classify_outcome(combined_output, exit_code, framework)

        # Generate excerpt hash for state persistence
        excerpt = self._extract_excerpt(combined_output, 4000)
        excerpt_hash = hashlib.sha256(excerpt.encode()).hexdigest()[:16]

        return TestResult(
            framework=framework,
            cmd=cmd,
            cwd=str(cwd),
            timeout_s=timeout_s,
            exit_code=exit_code,
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
            outcome=outcome.value,
            signals=signals,
            excerpt_hash=excerpt_hash,
        )

    def _extract_excerpt(self, output: str, max_chars: int) -> str:
        """Extract excerpt for hashing (first + last portions).

        Args:
            output: Full output
            max_chars: Maximum characters to extract

        Returns:
            Excerpt string
        """
        if len(output) <= max_chars:
            return output

        # Take first and last portions
        portion = max_chars // 2
        return output[:portion] + "\n...\n" + output[-portion:]

    def _classify_outcome(
        self, output: str, exit_code: int | str, framework: str
    ) -> tuple[TestOutcome, list[str]]:
        """Classify test outcome based on output.

        Args:
            output: Combined stdout + stderr
            exit_code: Process exit code
            framework: Framework name

        Returns:
            (TestOutcome, signals list)
        """
        if exit_code == "timeout":
            return TestOutcome.TIMEOUT, ["timeout"]

        signals = []

        # Framework-specific classification
        if framework == "pytest":
            return self._classify_pytest(output, exit_code, signals)
        elif framework in ["jest", "vitest"]:
            return self._classify_jest_vitest(output, exit_code, signals, framework)
        elif framework == "go":
            return self._classify_go(output, exit_code, signals)
        elif framework == "cargo":
            return self._classify_cargo(output, exit_code, signals)
        else:
            # Generic classification
            if exit_code == 0:
                return TestOutcome.PASS, ["exit_0"]
            else:
                return TestOutcome.NON_SEMANTIC_FAIL, ["unknown_framework", "non_zero_exit"]

    def _classify_pytest(
        self, output: str, exit_code: int, signals: list[str]
    ) -> tuple[TestOutcome, list[str]]:
        """Classify pytest output."""
        # Check for NO_TESTS
        for pattern in self.PYTEST_NO_TESTS:
            if pattern in output:
                signals.append(f"pytest:no_tests:{pattern}")
                return TestOutcome.NO_TESTS, signals

        # Check for NON_SEMANTIC failures
        for pattern in self.PYTEST_NON_SEMANTIC:
            if pattern in output:
                signals.append(f"pytest:non_semantic:{pattern}")
                return TestOutcome.NON_SEMANTIC_FAIL, signals

        # Check for SEMANTIC failures
        has_failed = "FAILED" in output
        has_semantic_marker = any(pattern in output for pattern in self.PYTEST_SEMANTIC)

        if has_failed and has_semantic_marker:
            signals.append("pytest:semantic_fail")
            return TestOutcome.SEMANTIC_FAIL, signals

        # Passed (exit code 0 expected)
        if exit_code == 0:
            signals.append("pytest:pass")
            return TestOutcome.PASS, signals

        # Ambiguous failure
        signals.append("pytest:ambiguous_fail")
        return TestOutcome.NON_SEMANTIC_FAIL, signals

    def _classify_jest_vitest(
        self, output: str, exit_code: int, signals: list[str], framework: str
    ) -> tuple[TestOutcome, list[str]]:
        """Classify jest/vitest output."""
        prefix = framework

        # Snapshot handling (block by default unless allow_snapshots)
        if "Snapshot" in output and ("obsolete" in output or "mismatch" in output):
            if not self.allow_snapshots:
                signals.append(f"{prefix}:snapshot_blocked")
                return TestOutcome.NON_SEMANTIC_FAIL, signals
            else:
                signals.append(f"{prefix}:snapshot_semantic")
                # Continue to semantic classification

        # Check for NO_TESTS
        for pattern in self.JEST_NO_TESTS:
            if pattern in output:
                signals.append(f"{prefix}:no_tests")
                return TestOutcome.NO_TESTS, signals

        # Check for NON_SEMANTIC failures
        for pattern in self.JEST_NON_SEMANTIC:
            if pattern in output:
                signals.append(f"{prefix}:non_semantic:{pattern}")
                return TestOutcome.NON_SEMANTIC_FAIL, signals

        # Check for SEMANTIC failures
        has_fail = "FAIL " in output
        has_semantic_marker = any(pattern in output for pattern in self.JEST_SEMANTIC)

        if has_fail and has_semantic_marker:
            signals.append(f"{prefix}:semantic_fail")
            return TestOutcome.SEMANTIC_FAIL, signals

        # Passed
        if exit_code == 0:
            signals.append(f"{prefix}:pass")
            return TestOutcome.PASS, signals

        # Ambiguous
        signals.append(f"{prefix}:ambiguous_fail")
        return TestOutcome.NON_SEMANTIC_FAIL, signals

    def _classify_go(
        self, output: str, exit_code: int, signals: list[str]
    ) -> tuple[TestOutcome, list[str]]:
        """Classify go test output."""
        # Check for NO_TESTS
        for pattern in self.GO_NO_TESTS:
            if pattern in output:
                signals.append("go:no_tests")
                return TestOutcome.NO_TESTS, signals

        # Check for NON_SEMANTIC failures
        for pattern in self.GO_NON_SEMANTIC:
            if pattern in output:
                signals.append(f"go:non_semantic:{pattern}")
                return TestOutcome.NON_SEMANTIC_FAIL, signals

        # Check for SEMANTIC failures
        has_fail = any(pattern in output for pattern in self.GO_SEMANTIC)
        if has_fail:
            signals.append("go:semantic_fail")
            return TestOutcome.SEMANTIC_FAIL, signals

        # Passed
        if exit_code == 0:
            signals.append("go:pass")
            return TestOutcome.PASS, signals

        # Ambiguous
        signals.append("go:ambiguous_fail")
        return TestOutcome.NON_SEMANTIC_FAIL, signals

    def _classify_cargo(
        self, output: str, exit_code: int, signals: list[str]
    ) -> tuple[TestOutcome, list[str]]:
        """Classify cargo test output."""
        # Check for NO_TESTS
        for pattern in self.CARGO_NO_TESTS:
            if pattern in output:
                signals.append("cargo:no_tests")
                return TestOutcome.NO_TESTS, signals

        # Check for NON_SEMANTIC failures
        for pattern in self.CARGO_NON_SEMANTIC:
            if pattern in output:
                signals.append(f"cargo:non_semantic:{pattern}")
                return TestOutcome.NON_SEMANTIC_FAIL, signals

        # Check for SEMANTIC failures
        has_fail = any(pattern in output for pattern in self.CARGO_SEMANTIC)
        if has_fail:
            signals.append("cargo:semantic_fail")
            return TestOutcome.SEMANTIC_FAIL, signals

        # Passed
        if exit_code == 0:
            signals.append("cargo:pass")
            return TestOutcome.PASS, signals

        # Ambiguous
        signals.append("cargo:ambiguous_fail")
        return TestOutcome.NON_SEMANTIC_FAIL, signals

    def build_targeted_command(
        self, base_command: str, framework: str, test_file: Optional[str] = None
    ) -> list[str]:
        """Build targeted test command.

        Args:
            base_command: Base test command (e.g., "pytest", "npm test")
            framework: Framework name
            test_file: Optional test file to target

        Returns:
            Command argv list
        """
        cmd = base_command.split()

        if not test_file:
            return cmd

        # Framework-specific targeting
        if framework == "pytest":
            cmd.append(test_file)
        elif framework == "jest":
            # Ensure we use jest directly, not npm test
            if "npm" in cmd or "yarn" in cmd:
                cmd = ["jest", test_file]
            else:
                cmd.append(test_file)
        elif framework == "vitest":
            if "npm" in cmd or "yarn" in cmd:
                cmd = ["vitest", "run", test_file]
            else:
                cmd.append(test_file)
        elif framework == "go":
            # Go: file→package mapping complex, keep package-level
            pass
        elif framework == "cargo":
            # Cargo: file→crate mapping complex, keep crate-level
            pass

        return cmd


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Execute tests and classify outcome")
    parser.add_argument("--command", required=True, help="Base test command")
    parser.add_argument("--framework", required=True, help="Framework name")
    parser.add_argument("--cwd", required=True, help="Working directory")
    parser.add_argument("--test-file", help="Optional test file to target")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds")
    parser.add_argument("--allow-snapshots", action="store_true", help="Allow snapshot tests")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    runner = TestRunner(allow_snapshots=args.allow_snapshots)

    # Build command
    cmd = runner.build_targeted_command(args.command, args.framework, args.test_file)

    # Execute
    result = runner.run_command(cmd, args.cwd, timeout_s=args.timeout, framework=args.framework)

    # Output
    output = asdict(result)
    print(json.dumps(output, indent=2))

    # Exit code based on outcome
    if result.outcome == TestOutcome.PASS.value:
        sys.exit(0)
    else:
        sys.exit(0)  # Always exit 0 for successful execution (classification in JSON)


if __name__ == "__main__":
    main()
