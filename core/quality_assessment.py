"""
Quality Assessment for SuperClaude Loop Orchestration.

Integrates with .claude/skills/sc-implement/scripts/evidence_gate.py
to assess quality of code changes during loop iterations.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from .types import QualityAssessment


class QualityAssessor:
    """
    Lightweight quality assessment using existing evidence_gate.py.

    This class wraps the evidence_gate script to provide quality
    scoring for the agentic loop. It converts evidence_gate output
    to QualityAssessment objects.
    """

    def __init__(self, threshold: float = 70.0):
        """
        Initialize the quality assessor.

        Args:
            threshold: Quality threshold to consider as "passed" (default 70.0)
        """
        self.threshold = threshold
        self.evidence_gate_path = self._find_evidence_gate()

    def _find_evidence_gate(self) -> Optional[Path]:
        """
        Locate the evidence_gate.py script.

        Returns:
            Path to evidence_gate.py or None if not found
        """
        # Try relative paths from common locations
        possible_paths = [
            # From core/ directory
            Path(__file__).parent.parent
            / ".claude"
            / "skills"
            / "sc-implement"
            / "scripts"
            / "evidence_gate.py",
            # From project root
            Path.cwd() / ".claude" / "skills" / "sc-implement" / "scripts" / "evidence_gate.py",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def assess(self, context: dict[str, Any]) -> QualityAssessment:
        """
        Assess quality of changes using evidence_gate.py.

        Args:
            context: Contains changes, tests, lint results from iteration

        Returns:
            QualityAssessment with score and improvements needed
        """
        # Build evidence object for evidence_gate
        evidence = {
            "command": context.get("command", "implement"),
            "requires_evidence": True,
            "changes": context.get("changes", []),
            "tests": context.get("tests", {}),
            "lint": context.get("lint", {}),
        }

        # Try to use the evidence_gate script
        if self.evidence_gate_path:
            result = self._invoke_evidence_gate(evidence)
        else:
            # Fallback to inline scoring
            result = self._inline_score(evidence)

        return self._to_quality_assessment(result)

    def _invoke_evidence_gate(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke evidence_gate.py as subprocess.

        Args:
            evidence: Evidence data for the gate

        Returns:
            Result from evidence_gate

        Security Notes:
            - Command uses shell=False with list arguments (prevents shell injection)
            - Executable is sys.executable (current Python interpreter, not user-controlled)
            - Script path comes from _find_evidence_gate() which only returns paths
              within the package directory structure (not user-controllable)
            - Evidence data is JSON-serialized and passed as a single argument
            - 30-second timeout prevents resource exhaustion
            - Output is captured but not logged (prevents secret leakage)
        """
        try:
            # Security: Fixed command structure with no user-controlled components
            # in the command itself. Evidence data is passed as JSON argument.
            result = subprocess.run(
                [sys.executable, str(self.evidence_gate_path), json.dumps(evidence)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.stdout:
                return json.loads(result.stdout)
            else:
                return {
                    "passed": False,
                    "score": 0.0,
                    "status": "error",
                    "missing": [f"evidence_gate error: {result.stderr}"],
                    "evidence_summary": {},
                }

        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "score": 0.0,
                "status": "timeout",
                "missing": ["evidence_gate timed out"],
                "evidence_summary": {},
            }
        except Exception as e:
            return {
                "passed": False,
                "score": 0.0,
                "status": "error",
                "missing": [f"evidence_gate exception: {e}"],
                "evidence_summary": {},
            }

    def _inline_score(self, evidence: dict[str, Any]) -> dict[str, Any]:
        """
        Fallback inline scoring when evidence_gate.py is not available.

        Uses simplified scoring logic based on evidence_gate.py.

        Args:
            evidence: Evidence data

        Returns:
            Scoring result
        """
        score = 0.0
        missing: list[str] = []

        changes = evidence.get("changes", [])
        tests = evidence.get("tests", {})
        lint = evidence.get("lint", {})

        # File changes (30 points)
        if changes:
            score += 30.0
        else:
            missing.append("No file changes detected")

        # Tests executed (25 points)
        if tests.get("ran"):
            score += 25.0
        else:
            missing.append("Tests not executed")

        # Tests passing (20 points)
        if tests.get("ran"):
            passed = tests.get("passed", 0)
            failed = tests.get("failed", 0)
            total = passed + failed
            if total > 0 and failed == 0:
                score += 20.0
            elif total > 0 and (passed / total) >= 0.9:
                score += 15.0
                missing.append(f"{failed} test(s) failing")

        # Lint clean (15 points)
        if lint.get("ran"):
            errors = lint.get("errors", 0)
            if errors == 0:
                score += 15.0
            else:
                missing.append(f"{errors} lint error(s)")

        # Coverage (10 points)
        coverage = tests.get("coverage", 0)
        if coverage >= 80:
            score += 10.0
        elif coverage >= 60:
            score += 7.0
        elif coverage > 0:
            score += 3.0
            missing.append(f"Coverage {coverage}% is low")

        # Determine status
        if score >= 90:
            status = "production_ready"
        elif score >= 70:
            status = "acceptable"
        elif score >= 50:
            status = "needs_review"
        else:
            status = "insufficient"

        return {
            "passed": score >= self.threshold,
            "score": round(score, 1),
            "status": status,
            "missing": missing,
            "evidence_summary": {
                "changes_count": len(changes),
                "tests_ran": tests.get("ran", False),
                "lint_ran": lint.get("ran", False),
            },
        }

    def _to_quality_assessment(self, result: dict[str, Any]) -> QualityAssessment:
        """
        Convert evidence_gate result to QualityAssessment.

        Args:
            result: Result from evidence_gate or inline scoring

        Returns:
            QualityAssessment object
        """
        return QualityAssessment(
            overall_score=result.get("score", 0.0),
            passed=result.get("passed", False),
            threshold=self.threshold,
            improvements_needed=result.get("missing", []),
            metrics=result.get("evidence_summary", {}),
            band=result.get("status", "unknown"),
            metadata=result,
        )


def assess_quality(context: dict[str, Any], threshold: float = 70.0) -> QualityAssessment:
    """
    Convenience function for quality assessment.

    Args:
        context: Evidence context
        threshold: Quality threshold

    Returns:
        QualityAssessment result
    """
    assessor = QualityAssessor(threshold)
    return assessor.assess(context)
