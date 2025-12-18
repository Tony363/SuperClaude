#!/usr/bin/env python3
"""
Evidence Gate Script for SuperClaude Skills.

Enforces evidence requirements for commands that require proof of work.
Ported from SuperClaude/Commands/command_executor.py evidence gating logic.

Usage:
    python evidence_gate.py '{"command": "implement", "changes": [...], "tests": {...}}'

Input (JSON):
    {
        "command": "implement",
        "requires_evidence": true,
        "changes": [
            {"file": "src/component.tsx", "type": "modified", "diff_lines": 45},
            {"file": "src/component.test.tsx", "type": "added", "diff_lines": 30}
        ],
        "tests": {
            "ran": true,
            "passed": 15,
            "failed": 0,
            "coverage": 85.5
        },
        "lint": {
            "ran": true,
            "errors": 0,
            "warnings": 2
        }
    }

Output (JSON):
    {
        "passed": true,
        "score": 95.0,
        "status": "production_ready",
        "missing": [],
        "evidence_summary": {...}
    }
"""

import json
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class EvidenceThresholds:
    """Thresholds for evidence quality assessment."""

    production_ready: float = 90.0
    acceptable: float = 70.0
    needs_review: float = 50.0
    min_changes_for_evidence: int = 1
    min_test_coverage: float = 60.0


THRESHOLDS = EvidenceThresholds()


def calculate_evidence_score(
    evidence: dict[str, Any],
) -> tuple[float, list[str], dict[str, Any]]:
    """
    Calculate evidence quality score.

    Scoring components:
    - File changes present: 30 points
    - Tests executed: 25 points
    - Tests passing: 20 points
    - Lint clean: 15 points
    - Coverage adequate: 10 points

    Returns:
        Tuple of (score, missing_items, summary)
    """
    score = 0.0
    missing = []
    summary = {}

    changes = evidence.get("changes", [])
    tests = evidence.get("tests", {})
    lint = evidence.get("lint", {})
    requires_evidence = evidence.get("requires_evidence", True)

    # 1. File changes (30 points)
    if changes:
        change_count = len(changes)
        total_diff_lines = sum(c.get("diff_lines", 0) for c in changes)
        score += 30.0
        summary["changes"] = {
            "files_modified": change_count,
            "total_diff_lines": total_diff_lines,
            "types": list(set(c.get("type", "unknown") for c in changes)),
        }
    elif requires_evidence:
        missing.append("No file changes detected - evidence required")

    # 2. Tests executed (25 points)
    if tests.get("ran"):
        score += 25.0
        summary["tests_executed"] = True
    elif requires_evidence:
        missing.append("Tests not executed - run tests to verify changes")

    # 3. Tests passing (20 points)
    if tests.get("ran"):
        passed = tests.get("passed", 0)
        failed = tests.get("failed", 0)
        total = passed + failed

        if total > 0:
            pass_rate = passed / total
            if pass_rate == 1.0:
                score += 20.0
                summary["test_status"] = "all_passing"
            elif pass_rate >= 0.9:
                score += 15.0
                summary["test_status"] = "mostly_passing"
                missing.append(f"{failed} test(s) failing")
            elif pass_rate >= 0.7:
                score += 10.0
                summary["test_status"] = "some_failing"
                missing.append(f"{failed} test(s) failing - review required")
            else:
                summary["test_status"] = "many_failing"
                missing.append(f"{failed} test(s) failing - significant issues")

        summary["tests"] = {"passed": passed, "failed": failed, "total": total}

    # 4. Lint clean (15 points)
    if lint.get("ran"):
        errors = lint.get("errors", 0)
        warnings = lint.get("warnings", 0)

        if errors == 0 and warnings == 0:
            score += 15.0
            summary["lint_status"] = "clean"
        elif errors == 0:
            score += 12.0
            summary["lint_status"] = "warnings_only"
        elif errors <= 3:
            score += 5.0
            summary["lint_status"] = "minor_errors"
            missing.append(f"{errors} lint error(s) to fix")
        else:
            summary["lint_status"] = "errors"
            missing.append(f"{errors} lint error(s) - requires attention")

        summary["lint"] = {"errors": errors, "warnings": warnings}

    # 5. Test coverage (10 points)
    if tests.get("ran"):
        coverage = tests.get("coverage", 0)
        if coverage >= 80:
            score += 10.0
            summary["coverage_status"] = "excellent"
        elif coverage >= THRESHOLDS.min_test_coverage:
            score += 7.0
            summary["coverage_status"] = "adequate"
        elif coverage > 0:
            score += 3.0
            summary["coverage_status"] = "low"
            missing.append(
                f"Test coverage {coverage}% below threshold ({THRESHOLDS.min_test_coverage}%)"
            )
        else:
            summary["coverage_status"] = "none"

        summary["coverage"] = coverage

    return score, missing, summary


def determine_status(score: float) -> str:
    """Determine status based on score."""
    if score >= THRESHOLDS.production_ready:
        return "production_ready"
    elif score >= THRESHOLDS.acceptable:
        return "acceptable"
    elif score >= THRESHOLDS.needs_review:
        return "needs_review"
    else:
        return "insufficient"


def evaluate_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate evidence and determine if it passes the gate.

    Args:
        evidence: Evidence data including changes, tests, lint results

    Returns:
        Evaluation result with pass/fail, score, status, and details
    """
    command = evidence.get("command", "unknown")
    requires_evidence = evidence.get("requires_evidence", True)

    # Commands that don't require evidence always pass
    if not requires_evidence:
        return {
            "passed": True,
            "score": 100.0,
            "status": "not_required",
            "missing": [],
            "evidence_summary": {"note": "Evidence not required for this command"},
        }

    score, missing, summary = calculate_evidence_score(evidence)
    status = determine_status(score)

    # Pass if acceptable or better
    passed = score >= THRESHOLDS.acceptable

    # Add command context
    summary["command"] = command
    summary["requires_evidence"] = requires_evidence

    return {
        "passed": passed,
        "score": round(score, 1),
        "status": status,
        "missing": missing,
        "evidence_summary": summary,
        "thresholds": {
            "production_ready": THRESHOLDS.production_ready,
            "acceptable": THRESHOLDS.acceptable,
            "needs_review": THRESHOLDS.needs_review,
        },
    }


def main():
    """Main entry point for script execution."""
    if len(sys.argv) < 2:
        print(
            json.dumps({"error": "No evidence provided. Pass JSON as first argument."})
        )
        sys.exit(1)

    try:
        evidence = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    result = evaluate_evidence(evidence)
    print(json.dumps(result, indent=2))

    # Exit with error code if evidence gate failed
    if not result["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
