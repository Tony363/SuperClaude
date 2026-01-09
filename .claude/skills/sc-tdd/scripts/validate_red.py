#!/usr/bin/env python3
"""Red Phase Validator - Verify tests fail with semantic assertion.

Validates RED_PENDING → RED_CONFIRMED transition by:
1. Auto-selecting intent test file from git diff
2. Executing targeted test
3. Verifying SEMANTIC_FAIL outcome (assertion failure, not compile error)
4. Storing red signature in state

Exit Codes:
    0 - Red state valid (transition allowed)
    2 - Red state invalid (transition blocked)
    3 - Validation error (cannot determine)

NOTE: Uses `from __future__ import annotations` for Python 3.9 compatibility
with generic types (list[str]).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from framework_detector import FrameworkDetector
from tdd_state_machine import IntentTest, TDDPhase, TDDStateMachine
from test_runner import TestOutcome, TestRunner


def find_changed_test_files(scope_root: Path) -> list[str]:
    """Find changed test files using git diff.

    Args:
        scope_root: Repository root

    Returns:
        List of changed test file paths relative to scope_root
    """
    try:
        # Get changed files (staged + unstaged)
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"],
            cwd=scope_root,
            capture_output=True,
            text=True,
            check=True
        )

        changed_files = result.stdout.strip().split("\n")
        if not changed_files or changed_files == [""]:
            return []

        # Filter to test files
        test_patterns = [
            "test_",
            "_test.",
            ".test.",
            ".spec.",
            "/tests/",
            "/__tests__/"
        ]

        test_files = [
            f for f in changed_files
            if any(pattern in f for pattern in test_patterns)
        ]

        return test_files

    except subprocess.CalledProcessError:
        return []


def validate_red_state(scope_root: str, allow_snapshots: bool = False) -> dict:
    """Validate Red phase requirements.

    Args:
        scope_root: Scope root path
        allow_snapshots: Whether to allow snapshot tests

    Returns:
        Validation result dict
    """
    scope_path = Path(scope_root).resolve()

    # Load or initialize state
    sm = TDDStateMachine()
    state = sm.load_state(str(scope_path))

    if not state:
        return {
            "allowed": False,
            "phase": "UNKNOWN",
            "reasons": ["No TDD state found. Initialize with: python tdd_state_machine.py --init --scope-root <path>"],
            "warnings": [],
            "artifacts": {}
        }

    # Check current phase
    if state.current_phase != TDDPhase.RED_PENDING.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [f"Not in RED_PENDING phase (currently: {state.current_phase})"],
            "warnings": [],
            "artifacts": {}
        }

    # Detect framework if not already set
    if not state.framework:
        detector = FrameworkDetector(scope_path)
        framework_info = detector.detect()

        if not framework_info:
            return {
                "allowed": False,
                "phase": state.current_phase,
                "reasons": ["No testing framework detected. Specify with --framework flag."],
                "warnings": [],
                "artifacts": {}
            }

        state.framework = framework_info.name
        state.test_command = framework_info.test_command
        sm.save_state(state)

    # Find intent test file
    changed_tests = find_changed_test_files(scope_path)

    if not changed_tests:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": ["No changed test files found. Write a failing test first."],
            "warnings": ["Run: git status to see tracked files"],
            "artifacts": {}
        }

    if len(changed_tests) > 1:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                f"Multiple test files changed: {changed_tests}",
                "TDD requires one test file at a time. Specify with --intent-test-file flag."
            ],
            "warnings": [],
            "artifacts": {"changed_tests": changed_tests}
        }

    intent_test_file = changed_tests[0]

    # Execute test
    runner = TestRunner(allow_snapshots=allow_snapshots)
    cmd = runner.build_targeted_command(
        state.test_command,
        state.framework,
        str(scope_path / intent_test_file)
    )

    result = runner.run_command(
        cmd,
        str(scope_path),
        timeout_s=120,
        framework=state.framework
    )

    # Validate outcome
    if result.outcome == TestOutcome.SEMANTIC_FAIL.value:
        # Success! Store red signature
        state.intent_test = IntentTest(
            file=intent_test_file,
            name=None,  # File-level targeting in v1
            failure_type="semantic",
            excerpt_hash=result.excerpt_hash
        )

        # Transition to RED_CONFIRMED
        success, message = sm.transition(
            state,
            TDDPhase.RED_CONFIRMED,
            evidence=f"Test failed: {result.signals}"
        )

        return {
            "allowed": True,
            "phase": TDDPhase.RED_CONFIRMED.value,
            "reasons": [
                f"Intent test '{intent_test_file}' failed with semantic assertion",
                f"Signals: {', '.join(result.signals)}"
            ],
            "warnings": [],
            "artifacts": {
                "intent_test": {
                    "file": intent_test_file,
                    "failure_type": "semantic",
                    "excerpt_hash": result.excerpt_hash
                },
                "test_output": result.stdout[:2000],  # Truncated
                "exit_code": result.exit_code
            }
        }

    elif result.outcome == TestOutcome.NO_TESTS.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                f"No tests found in '{intent_test_file}'",
                "Test file exists but contains no executable tests.",
                f"Signals: {', '.join(result.signals)}"
            ],
            "warnings": ["Check test file syntax and framework configuration"],
            "artifacts": {
                "test_output": result.stdout[:2000],
                "signals": result.signals
            }
        }

    elif result.outcome == TestOutcome.NON_SEMANTIC_FAIL.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                "Test failed but NOT with semantic assertion",
                "Detected: compile error, import error, or syntax error",
                f"Signals: {', '.join(result.signals)}",
                "",
                "Fix the test to compile and run, then fail with assertion."
            ],
            "warnings": [],
            "artifacts": {
                "test_output": result.stdout[:2000],
                "stderr": result.stderr[:2000],
                "signals": result.signals
            }
        }

    elif result.outcome == TestOutcome.PASS.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                f"Test '{intent_test_file}' PASSED (expected failure)",
                "RED phase requires a failing test.",
                "Write an assertion that exposes missing functionality."
            ],
            "warnings": [],
            "artifacts": {
                "test_output": result.stdout[:2000],
                "signals": result.signals
            }
        }

    elif result.outcome == TestOutcome.TIMEOUT.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                f"Test execution timed out (>{result.timeout_s}s)",
                "Infinite loop or very slow test detected."
            ],
            "warnings": ["Optimize test or increase timeout"],
            "artifacts": {}
        }

    else:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [f"Unknown test outcome: {result.outcome}"],
            "warnings": [],
            "artifacts": {"test_output": result.stdout[:2000]}
        }


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Validate Red phase")
    parser.add_argument("--scope-root", required=True, help="Scope root directory")
    parser.add_argument("--allow-snapshots", action="store_true", help="Allow snapshot tests")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    result = validate_red_state(args.scope_root, args.allow_snapshots)

    print(json.dumps(result, indent=2))

    # Exit code
    sys.exit(0 if result["allowed"] else 2)


if __name__ == "__main__":
    main()
