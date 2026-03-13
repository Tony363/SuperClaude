#!/usr/bin/env python3
"""
Classify findings eligible for LLM-generated fixes (Phase 3).

Reads normalized fix plans and identifies findings that:
- Are NOT deterministic-fixable (not ruff_format or ruff_lint_fix)
- Match the llm_single_file fix type (conservative scope)
- Meet confidence threshold
- Target a single file in the allowlist
- Are within LOC limits

Outputs llm-fixable-findings.json for the Claude Code Action step.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from fix_type_registry import get_fix_type, infer_fix_type
from normalize_findings import is_file_allowed_for_autofix

# Conservative scope: only these issue patterns qualify for LLM fix
LLM_FIX_ISSUE_PATTERNS = [
    "unused variable",
    "dead code",
    "unreachable code",
    "type hint",
    "type annotation",
    "missing docstring",
    "simplify",
    "unnecessary complexity",
]

# Safety limits
MAX_LLM_FIXES_PER_RUN = 5
MAX_LOC_PER_LLM_FIX = 50  # Stricter than deterministic — LLM changes are riskier


def is_llm_fixable(finding: dict[str, Any]) -> bool:
    """
    Determine if a finding is eligible for LLM-generated fix.

    Must be:
    1. Not already handled by deterministic tools
    2. In an allowed category (quality, performance)
    3. Single-file, in allowlist
    4. Within LOC limit
    5. Matches conservative issue patterns
    """
    # Skip if already deterministic-fixable
    fix_type_name = infer_fix_type(
        suggestion=finding.get("suggestion", ""),
        explicit_fix_type=finding.get("fix_type", ""),
    )

    if fix_type_name in ("ruff_format", "ruff_lint_fix"):
        return False

    # Check llm_single_file eligibility
    llm_fix = get_fix_type("llm_single_file")
    if llm_fix is None:
        return False

    # Category check
    category = finding.get("category", "")
    if category not in llm_fix.categories:
        return False

    # Confidence check
    if finding.get("confidence", 0) < llm_fix.confidence_threshold:
        return False

    # File allowlist
    file_path = finding.get("file", "")
    if not file_path or not is_file_allowed_for_autofix(file_path):
        return False

    # LOC limit (stricter for LLM fixes)
    line_start = finding.get("line_start", 0)
    line_end = finding.get("line_end", line_start)
    loc_affected = max(line_end - line_start + 1, 1)
    if loc_affected > MAX_LOC_PER_LLM_FIX:
        return False

    # Must match conservative issue patterns
    issue_lower = finding.get("issue", "").lower()
    suggestion_lower = finding.get("suggestion", "").lower()
    combined = f"{issue_lower} {suggestion_lower}"

    if not any(pattern in combined for pattern in LLM_FIX_ISSUE_PATTERNS):
        return False

    return True


def classify_findings(fix_plans_dir: Path, max_fixes: int) -> dict[str, Any]:
    """
    Scan all fix plans and classify LLM-fixable findings.

    Returns structured output with prioritized findings.
    """
    llm_fixable = []

    for category in ("quality", "performance"):
        plan_file = fix_plans_dir / f"{category}.json"
        if not plan_file.exists():
            continue

        with open(plan_file) as f:
            plan = json.load(f)

        for finding in plan.get("findings", []):
            if is_llm_fixable(finding):
                finding["_source_category"] = category
                llm_fixable.append(finding)

    # Sort by severity (critical > high > medium > low) then confidence (desc)
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    llm_fixable.sort(
        key=lambda f: (
            severity_rank.get(f.get("severity", "low"), 99),
            -f.get("confidence", 0),
        )
    )

    # Apply limit
    selected = llm_fixable[:max_fixes]

    return {
        "total_candidates": len(llm_fixable),
        "selected": len(selected),
        "max_allowed": max_fixes,
        "findings": selected,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Classify findings eligible for LLM-generated fixes (Phase 3)"
    )
    parser.add_argument(
        "--fix-plans-dir",
        type=Path,
        required=True,
        help="Directory containing normalized fix plan JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("llm-fixable-findings.json"),
        help="Output file for LLM-fixable findings",
    )
    parser.add_argument(
        "--max-fixes",
        type=int,
        default=MAX_LLM_FIXES_PER_RUN,
        help=f"Max findings to select (default: {MAX_LLM_FIXES_PER_RUN})",
    )

    args = parser.parse_args()

    if not args.fix_plans_dir.exists():
        print(f"Error: Fix plans directory not found: {args.fix_plans_dir}", file=sys.stderr)
        sys.exit(1)

    result = classify_findings(args.fix_plans_dir, args.max_fixes)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"LLM-fixable findings: {result['selected']}/{result['total_candidates']} candidates")
    if result["selected"] > 0:
        for i, finding in enumerate(result["findings"], 1):
            print(
                f"  {i}. [{finding.get('severity')}] {finding.get('file')}:"
                f"{finding.get('line_start')} - {finding.get('issue', '')[:60]}"
            )
    else:
        print("  No findings eligible for LLM fix")

    # Exit with code indicating if there are fixable findings
    sys.exit(0 if result["selected"] > 0 else 2)


if __name__ == "__main__":
    main()
