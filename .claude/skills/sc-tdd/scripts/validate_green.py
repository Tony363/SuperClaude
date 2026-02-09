#!/usr/bin/env python3
"""Green Phase Validator - Verify tests pass and full suite green.

Validates GREEN_PENDING → GREEN_CONFIRMED transition by:
1. Re-running intent test (must pass)
2. Verifying same test that was red is now green
3. Running full test suite (must pass)

Exit Codes:
    0 - Green state valid (transition allowed)
    2 - Green state invalid (transition blocked)
    3 - Validation error (cannot determine)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tdd_state_machine import TDDPhase, TDDStateMachine
from test_runner import TestOutcome, TestRunner


def validate_green_state(scope_root: str, skip_full_suite: bool = False) -> dict:
    """Validate Green phase requirements.

    Args:
        scope_root: Scope root path
        skip_full_suite: Skip full suite execution (fast mode)

    Returns:
        Validation result dict
    """
    scope_path = Path(scope_root).resolve()

    # Load state
    sm = TDDStateMachine()
    state = sm.load_state(str(scope_path))

    if not state:
        return {
            "allowed": False,
            "phase": "UNKNOWN",
            "reasons": ["No TDD state found"],
            "warnings": [],
            "artifacts": {},
        }

    # Check current phase
    if state.current_phase != TDDPhase.GREEN_PENDING.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [f"Not in GREEN_PENDING phase (currently: {state.current_phase})"],
            "warnings": [],
            "artifacts": {},
        }

    # Check we have intent test from Red phase
    if not state.intent_test:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": ["No intent test found. Must complete RED phase first."],
            "warnings": [],
            "artifacts": {},
        }

    # Verify we have framework
    if not state.framework or not state.test_command:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": ["Framework not configured. Re-run validation."],
            "warnings": [],
            "artifacts": {},
        }

    runner = TestRunner()

    # Step 1: Re-run intent test (targeted)
    intent_test_path = str(scope_path / state.intent_test.file)
    targeted_cmd = runner.build_targeted_command(
        state.test_command, state.framework, intent_test_path
    )

    targeted_result = runner.run_command(
        targeted_cmd, str(scope_path), timeout_s=120, framework=state.framework
    )

    # Must pass
    if targeted_result.outcome != TestOutcome.PASS.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                f"Intent test '{state.intent_test.file}' still FAILING",
                f"Outcome: {targeted_result.outcome}",
                f"Signals: {', '.join(targeted_result.signals)}",
                "",
                "Implementation did not make the test pass.",
            ],
            "warnings": [],
            "artifacts": {
                "intent_test_output": targeted_result.stdout[:2000],
                "outcome": targeted_result.outcome,
                "signals": targeted_result.signals,
            },
        }

    # Step 2: Run full suite (unless skipped)
    if skip_full_suite:
        # Fast mode: trust targeted test, defer full suite
        sm.transition(
            state, TDDPhase.GREEN_CONFIRMED, evidence="Intent test passed (full suite deferred)"
        )

        return {
            "allowed": True,
            "phase": TDDPhase.GREEN_CONFIRMED.value,
            "reasons": [
                f"Intent test '{state.intent_test.file}' now PASSES",
                "Full suite execution deferred (fast mode)",
            ],
            "warnings": ["Run full suite before completing feature"],
            "artifacts": {
                "intent_test_output": targeted_result.stdout[:1000],
                "duration_ms": targeted_result.duration_ms,
            },
        }

    # Run full suite
    full_cmd = runner.build_targeted_command(
        state.test_command,
        state.framework,
        test_file=None,  # No targeting = full suite
    )

    full_result = runner.run_command(
        full_cmd,
        str(scope_path),
        timeout_s=300,  # Longer timeout for full suite
        framework=state.framework,
    )

    # Check outcome
    if full_result.outcome == TestOutcome.PASS.value:
        # Success! Transition to GREEN_CONFIRMED
        success, message = sm.transition(
            state,
            TDDPhase.GREEN_CONFIRMED,
            evidence=f"Intent test + full suite passed ({full_result.duration_ms}ms)",
        )

        return {
            "allowed": True,
            "phase": TDDPhase.GREEN_CONFIRMED.value,
            "reasons": [
                f"Intent test '{state.intent_test.file}' now PASSES",
                f"Full test suite PASSES ({full_result.duration_ms}ms)",
                "No regressions detected",
            ],
            "warnings": [],
            "artifacts": {
                "intent_test_output": targeted_result.stdout[:1000],
                "full_suite_duration_ms": full_result.duration_ms,
                "full_suite_signals": full_result.signals,
            },
        }

    elif full_result.outcome == TestOutcome.TIMEOUT.value:
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                f"Full test suite timed out (>{full_result.timeout_s}s)",
                "Suite may be too slow or have infinite loops",
            ],
            "warnings": [
                "Consider using --skip-full-suite for faster cycles",
                "Run full suite only at feature completion",
            ],
            "artifacts": {"timeout_s": full_result.timeout_s},
        }

    else:
        # Suite failed - regression detected
        return {
            "allowed": False,
            "phase": state.current_phase,
            "reasons": [
                "Full test suite FAILED - REGRESSION DETECTED",
                f"Outcome: {full_result.outcome}",
                f"Signals: {', '.join(full_result.signals)}",
                "",
                "Your implementation broke existing tests.",
            ],
            "warnings": ["Fix regressions before proceeding"],
            "artifacts": {
                "full_suite_output": full_result.stdout[:2000],
                "full_suite_stderr": full_result.stderr[:1000],
                "outcome": full_result.outcome,
                "signals": full_result.signals,
            },
        }


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Validate Green phase")
    parser.add_argument("--scope-root", required=True, help="Scope root directory")
    parser.add_argument(
        "--skip-full-suite", action="store_true", help="Skip full suite (fast mode)"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    result = validate_green_state(args.scope_root, args.skip_full_suite)

    print(json.dumps(result, indent=2))

    # Exit code
    sys.exit(0 if result["allowed"] else 2)


if __name__ == "__main__":
    main()
