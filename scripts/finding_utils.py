#!/usr/bin/env python3
"""
Finding Utilities: validation, deduplication, and schema for review findings.

Extracted from run_consensus_review.py (which was dead code -- the workflow
uses Claude Code Action directly for MCP calls).
"""

from typing import Any, Dict, List

# Finding schema (for validation)
FINDING_SCHEMA = {
    "type": "object",
    "required": [
        "category",
        "severity",
        "file",
        "line_start",
        "issue",
        "suggestion",
        "confidence",
        "actionable",
    ],
    "properties": {
        "category": {"enum": ["security", "quality", "performance", "tests"]},
        "severity": {"enum": ["critical", "high", "medium", "low"]},
        "file": {"type": "string"},
        "line_start": {"type": "integer", "minimum": 1},
        "line_end": {"type": "integer", "minimum": 1},
        "issue": {"type": "string"},
        "suggestion": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "actionable": {"type": "boolean"},
    },
}


def validate_finding(finding: Dict[str, Any]) -> bool:
    """Validate finding against schema."""
    try:
        # Check required fields
        required = [
            "category",
            "severity",
            "file",
            "line_start",
            "issue",
            "suggestion",
            "confidence",
            "actionable",
        ]
        for field in required:
            if field not in finding:
                return False

        # Check enum values
        if finding["category"] not in ["security", "quality", "performance", "tests"]:
            return False
        if finding["severity"] not in ["critical", "high", "medium", "low"]:
            return False

        # Check types
        if not isinstance(finding["line_start"], int) or finding["line_start"] < 1:
            return False
        if not isinstance(finding["confidence"], (int, float)) or not (
            0 <= finding["confidence"] <= 1
        ):
            return False
        if not isinstance(finding["actionable"], bool):
            return False

        return True
    except (KeyError, TypeError):
        return False


def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove overlapping findings (same file + line range)."""
    seen = set()
    deduplicated = []

    for finding in findings:
        # Create unique key: file + line_start + line_end (or line_start if no line_end)
        line_end = finding.get("line_end", finding["line_start"])
        key = (finding["file"], finding["line_start"], line_end)

        if key not in seen:
            seen.add(key)
            deduplicated.append(finding)

    return deduplicated
