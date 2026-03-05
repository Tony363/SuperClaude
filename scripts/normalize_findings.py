#!/usr/bin/env python3
"""
Finding Normalization & Categorization

Converts PAL consensus findings into actionable, categorized fix plans.
Filters by confidence threshold and actionability.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


CONFIDENCE_THRESHOLD = 0.7
SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def load_findings(findings_file: Path) -> List[Dict[str, Any]]:
    """Load review findings JSON."""
    try:
        with open(findings_file, "r") as f:
            data = json.load(f)
            return data.get("findings", [])
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading findings file: {e}", file=sys.stderr)
        sys.exit(1)


def filter_actionable(findings: List[Dict[str, Any]], confidence_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """Filter findings by confidence threshold and actionability."""
    return [
        f for f in findings
        if f.get("confidence", 0) >= confidence_threshold
        and f.get("actionable", False)
    ]


def group_by_category(findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group findings by category."""
    by_category = {
        "security": [],
        "quality": [],
        "performance": [],
        "tests": [],
    }

    for finding in findings:
        category = finding.get("category", "quality")
        if category in by_category:
            by_category[category].append(finding)

    return by_category


def rank_by_priority(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort findings by severity (critical first) and confidence (higher first)."""
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_RANK.get(f.get("severity", "low"), 99),
            -f.get("confidence", 0)  # Negative for descending order
        )
    )


def generate_fix_plan(
    category: str,
    findings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate fix plan for a category."""
    if not findings:
        return None

    # Rank by priority
    ranked = rank_by_priority(findings)

    # Count by severity
    severity_counts = {
        "critical": sum(1 for f in ranked if f.get("severity") == "critical"),
        "high": sum(1 for f in ranked if f.get("severity") == "high"),
        "medium": sum(1 for f in ranked if f.get("severity") == "medium"),
        "low": sum(1 for f in ranked if f.get("severity") == "low"),
    }

    return {
        "category": category,
        "total_findings": len(ranked),
        "severity_counts": severity_counts,
        "findings": ranked,
        "summary": {
            "top_severity": ranked[0].get("severity") if ranked else "none",
            "files_affected": len(set(f.get("file") for f in ranked)),
            "avg_confidence": sum(f.get("confidence", 0) for f in ranked) / len(ranked),
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normalize and categorize code review findings"
    )
    parser.add_argument(
        "--findings",
        type=Path,
        required=True,
        help="Review findings JSON file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("fix-plans"),
        help="Output directory for fix plans"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help="Minimum confidence threshold"
    )

    args = parser.parse_args()

    # Load findings
    all_findings = load_findings(args.findings)
    print(f"Loaded {len(all_findings)} findings")

    # Filter by actionability and confidence
    actionable = filter_actionable(all_findings, args.confidence_threshold)
    print(f"Actionable findings (confidence >= {args.confidence_threshold}): {len(actionable)}")

    filtered_count = len(all_findings) - len(actionable)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} low-confidence or non-actionable findings")

    # Group by category
    by_category = group_by_category(actionable)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Generate fix plans per category
    plans_created = 0
    for category, findings in by_category.items():
        if not findings:
            continue

        fix_plan = generate_fix_plan(category, findings)
        if fix_plan:
            output_file = args.output_dir / f"{category}.json"
            with open(output_file, "w") as f:
                json.dump(fix_plan, f, indent=2)

            print(f"\n{category.upper()}: {len(findings)} findings")
            print(f"  Critical: {fix_plan['severity_counts']['critical']}")
            print(f"  High: {fix_plan['severity_counts']['high']}")
            print(f"  Medium: {fix_plan['severity_counts']['medium']}")
            print(f"  Low: {fix_plan['severity_counts']['low']}")
            print(f"  Output: {output_file}")

            plans_created += 1

    if plans_created == 0:
        print("\nNo actionable findings to create fix plans")
    else:
        print(f"\nCreated {plans_created} fix plans in {args.output_dir}")


if __name__ == "__main__":
    main()
