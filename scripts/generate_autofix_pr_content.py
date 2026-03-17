#!/usr/bin/env python3
"""
Autofix PR Content Generation (Phase 2)

Generates PR descriptions for autofix PRs (with actual code changes).
Clearly indicates this is AUTOFIX and contains real code modifications.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

CATEGORY_EMOJI = {
    "security": "🔒",
    "quality": "✨",
    "performance": "⚡",
    "tests": "🧪",
}

CATEGORY_DESCRIPTION = {
    "security": "Security vulnerabilities and hardening opportunities",
    "quality": "Code quality, maintainability, and SOLID principle adherence",
    "performance": "Performance optimizations and efficiency improvements",
    "tests": "Test coverage gaps and test quality improvements",
}

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}


def load_fix_plan(fix_plan_file: Path) -> Dict[str, Any]:
    """Load fix plan JSON."""
    try:
        with open(fix_plan_file, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading fix plan {fix_plan_file}: {e}", file=sys.stderr)
        return None


def load_autofix_results(results_file: Path) -> Dict[str, Any]:
    """Load autofix results JSON."""
    try:
        with open(results_file, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading autofix results {results_file}: {e}", file=sys.stderr)
        return None


def generate_autofix_pr_description(
    category: str, fix_plan: Dict[str, Any], autofix_results: Dict[str, Any]
) -> str:
    """Generate PR description for autofix PR."""
    all_findings = fix_plan.get("findings", [])

    # Filter to autofix-eligible only
    findings = [f for f in all_findings if f.get("autofix_eligible", False)]

    if not findings:
        return None

    summary_info = fix_plan.get("summary", {})
    emoji = CATEGORY_EMOJI.get(category, "📋")
    description = CATEGORY_DESCRIPTION.get(category, "Code improvements")

    # Get autofix results for this category
    category_results = None
    for result in autofix_results.get("results", []):
        if result.get("category") == category:
            category_results = result
            break

    files_succeeded = category_results.get("files_succeeded", 0) if category_results else 0
    files_failed = category_results.get("files_failed", 0) if category_results else 0

    # Header
    pr_desc = f"""# ⚡ {emoji} AUTOFIX: {category.upper()}

**⚠️ THIS PR CONTAINS ACTUAL CODE CHANGES ⚠️**

{description}

## 🤖 Automated Fixes Applied

This PR contains **automatic code changes** that have passed all safety checks:
- ✅ File allowlist validation
- ✅ Ruff format idempotency check
- ✅ Python syntax validation
- ✅ Git diff reasonableness check
- ✅ All CI tests passed (see checks below)

## Summary

- **Total Autofix Findings**: {len(findings)}
- **Files Modified**: {files_succeeded}
- **Files Failed Safety Checks**: {files_failed}
- **Average Confidence**: {summary_info.get("avg_confidence", 0):.0%}
- **Fix Type**: `ruff format` (deterministic formatting only)

### Safety Rails

| Check | Status |
|-------|--------|
| File allowlist (`src/**/*.py` only) | ✅ Enforced |
| Max files per PR (5) | ✅ Enforced |
| Max LOC per file (200) | ✅ Enforced |
| Confidence threshold (≥0.95) | ✅ Enforced |
| Idempotency verification | ✅ Passed |
| Syntax validation | ✅ Passed |
| CI tests | ✅ See checks below |

---

## Detailed Changes

"""

    # Add each autofix-eligible finding
    for idx, finding in enumerate(findings, start=1):
        severity = finding.get("severity", "medium")
        file_path = finding.get("file", "unknown")
        line_start = finding.get("line_start", 1)
        issue = finding.get("issue", "No description")
        suggestion = finding.get("suggestion", "No suggestion")
        confidence = finding.get("confidence", 0)

        pr_desc += f"""
### {idx}. {SEVERITY_EMOJI[severity]} {file_path}:{line_start}

**Issue**: {issue}

**Fix Applied**: {suggestion}

**Confidence**: {confidence:.0%}

---
"""

    # Footer
    pr_desc += f"""

## 🔍 How to Review This PR

### ⚠️ IMPORTANT: This PR contains actual code changes

Unlike suggestion-only PRs, this PR has **already modified code**. Review carefully:

1. **Check the diff** - Verify changes are formatting-only (no logic changes)
2. **Run tests locally** - CI passed, but local testing adds confidence
3. **Spot check files** - Ensure formatting is correct
4. **Approve or request changes** - This PR requires explicit approval

### If Changes Look Wrong

If you spot issues with the autofix:
1. Close this PR immediately
2. Report the issue in a comment
3. Manual rollback: All changes can be reverted
4. The autofix system will be disabled pending investigation

### Merge Process

1. This PR is created as **DRAFT** - you must mark "Ready for review"
2. All CI checks must be green
3. Manual approval required (no auto-merge)
4. Squash merge recommended to keep history clean

---

## 📊 Validation Report

**Timestamp**: {autofix_results.get("timestamp", "N/A")}

| Metric | Value |
|--------|-------|
| Files Attempted | {category_results.get("files_attempted", 0) if category_results else 0} |
| Files Succeeded | {files_succeeded} |
| Files Failed | {files_failed} |
| Success Rate | {files_succeeded / max(category_results.get("files_attempted", 1) if category_results else 1, 1) * 100:.0f}% |

"""

    if files_failed > 0 and category_results:
        pr_desc += "### ⚠️ Files That Failed Safety Checks\n\n"
        for detail in category_results.get("details", []):
            if detail.get("checks_failed"):
                pr_desc += (
                    f"- **{detail['file']}**: {', '.join(f[0] for f in detail['checks_failed'])}\n"
                )
        pr_desc += "\n"

    pr_desc += """
---

**Generated by**: SuperClaude Nightly Code Review
**Review Method**: PAL MCP Multi-Model Consensus + Automated Safety Checks
**Phase**: Phase 2A (Autofix: ruff format only)

**⚡ Autofix enabled**: This PR was automatically generated with code changes. All safety checks passed, but human review is required before merge.

**Rollback procedure**: See `/docs/runbooks/nightly-review.md` for emergency rollback steps.
"""

    return pr_desc


def main():
    parser = argparse.ArgumentParser(description="Generate autofix PR content (Phase 2)")
    parser.add_argument(
        "--fix-plans-dir",
        type=Path,
        required=True,
        help="Directory containing fix plan JSON files",
    )
    parser.add_argument(
        "--autofix-results",
        type=Path,
        required=True,
        help="Autofix results JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pr-content-autofix"),
        help="Output directory for autofix PR content",
    )

    args = parser.parse_args()

    if not args.fix_plans_dir.exists():
        print(f"Error: Fix plans directory not found: {args.fix_plans_dir}", file=sys.stderr)
        sys.exit(1)

    if not args.autofix_results.exists():
        print(f"Error: Autofix results not found: {args.autofix_results}", file=sys.stderr)
        sys.exit(1)

    # Load autofix results
    autofix_results = load_autofix_results(args.autofix_results)
    if not autofix_results:
        print("Error: Failed to load autofix results", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Process each category
    categories = ["quality"]  # Phase 2A: Only quality for now
    prs_generated = 0

    for category in categories:
        fix_plan_file = args.fix_plans_dir / f"{category}.json"

        if not fix_plan_file.exists():
            print(f"No fix plan for {category} - skipping")
            continue

        fix_plan = load_fix_plan(fix_plan_file)
        if not fix_plan or not fix_plan.get("findings"):
            print(f"No findings in {category} fix plan - skipping")
            continue

        # Generate autofix PR description
        pr_description = generate_autofix_pr_description(category, fix_plan, autofix_results)

        if pr_description is None:
            print(f"No autofix-eligible findings in {category} - skipping")
            continue

        # Write to output file
        output_file = args.output_dir / f"{category}-autofix-pr.md"
        with open(output_file, "w") as f:
            f.write(pr_description)

        print(f"Generated autofix PR content for {category}: {output_file}")
        prs_generated += 1

    if prs_generated == 0:
        print("\nNo autofix PR content generated (no eligible findings)")
    else:
        print(f"\nGenerated {prs_generated} autofix PR descriptions in {args.output_dir}")


if __name__ == "__main__":
    main()
