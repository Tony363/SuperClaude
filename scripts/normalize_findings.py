#!/usr/bin/env python3
"""
Finding Normalization & Categorization

Converts PAL consensus findings into actionable, categorized fix plans.
Filters by confidence threshold and actionability.
"""

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from fix_type_registry import get_fix_type, infer_fix_type

CONFIDENCE_THRESHOLD = 0.7
SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

# Phase 2: File allowlist for autofix (strict)
AUTOFIX_ALLOWLIST_PATTERNS = [
    "src/**/*.py",  # Application code only
]

AUTOFIX_DENYLIST_PATTERNS = [
    "tests/**",  # No test modifications
    "docs/**",  # No documentation
    ".github/**",  # No workflow files
    "scripts/**",  # No automation scripts
    "*.toml",  # No config files
    "*.yaml",
    "*.yml",
    "*.json",
]

# Phase 2: Autofix limits (conservative)
AUTOFIX_MAX_LOC_PER_FINDING = 200
AUTOFIX_MAX_FILES_PER_CATEGORY = 5


def load_findings(findings_file: Path) -> List[Dict[str, Any]]:
    """Load review findings JSON."""
    try:
        with open(findings_file, "r") as f:
            data = json.load(f)
            return data.get("findings", [])
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading findings file: {e}", file=sys.stderr)
        sys.exit(1)


def filter_actionable(
    findings: List[Dict[str, Any]], confidence_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Filter findings by confidence threshold and actionability."""
    return [
        f
        for f in findings
        if f.get("confidence", 0) >= confidence_threshold and f.get("actionable", False)
    ]


def is_file_allowed_for_autofix(file_path: str) -> bool:
    """Check if file is allowed for autofix based on allowlist/denylist."""
    file_obj = Path(file_path)

    # Check denylist first (higher priority)
    for pattern in AUTOFIX_DENYLIST_PATTERNS:
        if fnmatch.fnmatch(str(file_obj), pattern) or fnmatch.fnmatch(file_path, pattern):
            return False

    # Check allowlist
    for pattern in AUTOFIX_ALLOWLIST_PATTERNS:
        if fnmatch.fnmatch(str(file_obj), pattern) or fnmatch.fnmatch(file_path, pattern):
            return True

    return False


def is_finding_autofix_eligible(finding: Dict[str, Any]) -> bool:
    """
    Determine if a finding is eligible for autofix (Phase 2).

    Criteria are driven by the fix-type registry (scripts/fix_type_registry.py):
    - Fix type: must be a known, registered type
    - Category: must match the fix type's allowed categories
    - Confidence: must meet the fix type's threshold
    - File: must match allowlist and not match denylist
    - LOC impact: <= configured limit
    """
    # Infer fix type from explicit field or suggestion text
    fix_type_name = infer_fix_type(
        suggestion=finding.get("suggestion", ""),
        explicit_fix_type=finding.get("fix_type", ""),
    )

    if fix_type_name is None:
        return False

    fix_type = get_fix_type(fix_type_name)
    if fix_type is None:
        return False

    # Store resolved fix_type for downstream use by apply_autofix
    finding["_resolved_fix_type"] = fix_type_name

    # Category check (from registry)
    category = finding.get("category", "")
    if category not in fix_type.categories:
        return False

    # Confidence check (from registry)
    if finding.get("confidence", 0) < fix_type.confidence_threshold:
        return False

    # File allowlist check
    file_path = finding.get("file", "")
    if not is_file_allowed_for_autofix(file_path):
        return False

    # LOC limit (estimate from line range)
    line_start = finding.get("line_start", 0)
    line_end = finding.get("line_end", 0)
    loc_affected = line_end - line_start + 1

    if loc_affected > AUTOFIX_MAX_LOC_PER_FINDING:
        return False

    return True


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
            -f.get("confidence", 0),  # Negative for descending order
        ),
    )


def generate_fix_plan(category: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate fix plan for a category with Phase 2 autofix eligibility."""
    if not findings:
        return None

    # Rank by priority
    ranked = rank_by_priority(findings)

    # Phase 2: Mark autofix eligibility
    autofix_eligible_count = 0
    autofix_eligible_files = set()

    for finding in ranked:
        is_autofix = is_finding_autofix_eligible(finding)
        finding["autofix_eligible"] = is_autofix

        if is_autofix:
            autofix_eligible_count += 1
            autofix_eligible_files.add(finding.get("file"))

    # Apply per-category file limit for autofix
    if len(autofix_eligible_files) > AUTOFIX_MAX_FILES_PER_CATEGORY:
        # Keep only top priority findings within file limit
        files_kept = set()
        for finding in ranked:
            if finding.get("autofix_eligible"):
                file_path = finding.get("file")
                if file_path in files_kept or len(files_kept) >= AUTOFIX_MAX_FILES_PER_CATEGORY:
                    finding["autofix_eligible"] = False
                    autofix_eligible_count -= 1
                else:
                    files_kept.add(file_path)

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
            "autofix_eligible": autofix_eligible_count,  # Phase 2
            "autofix_files": len(autofix_eligible_files),  # Phase 2
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Normalize and categorize code review findings")
    parser.add_argument("--findings", type=Path, required=True, help="Review findings JSON file")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("fix-plans"), help="Output directory for fix plans"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help="Minimum confidence threshold",
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
    total_autofix_eligible = 0

    for category, findings in by_category.items():
        if not findings:
            continue

        fix_plan = generate_fix_plan(category, findings)
        if fix_plan:
            output_file = args.output_dir / f"{category}.json"
            with open(output_file, "w") as f:
                json.dump(fix_plan, f, indent=2)

            autofix_count = fix_plan["summary"].get("autofix_eligible", 0)
            autofix_files = fix_plan["summary"].get("autofix_files", 0)
            total_autofix_eligible += autofix_count

            print(f"\n{category.upper()}: {len(findings)} findings")
            print(f"  Critical: {fix_plan['severity_counts']['critical']}")
            print(f"  High: {fix_plan['severity_counts']['high']}")
            print(f"  Medium: {fix_plan['severity_counts']['medium']}")
            print(f"  Low: {fix_plan['severity_counts']['low']}")
            if autofix_count > 0:
                print(f"  Autofix eligible: {autofix_count} findings in {autofix_files} files")
            print(f"  Output: {output_file}")

            plans_created += 1

    if plans_created == 0:
        print("\nNo actionable findings to create fix plans")
    else:
        print(f"\nCreated {plans_created} fix plans in {args.output_dir}")
        if total_autofix_eligible > 0:
            print(f"Phase 2: {total_autofix_eligible} findings eligible for autofix")


if __name__ == "__main__":
    main()
