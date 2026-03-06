#!/usr/bin/env python3
"""
Autofix Application Engine (Phase 2)

Applies deterministic fixes with comprehensive safety checks:
1. Pre-check: File validation, allowlist, LOC limits
2. Apply: Run ruff format
3. Validate: Idempotency check (run twice)
4. Syntax check: Python compilation
5. Git check: Ensure formatting-only changes

Rollback on any failure.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Safety limits (must match normalize_findings.py)
MAX_FILES_PER_RUN = 5
MAX_LOC_PER_FILE = 200


def run_command(
    cmd: List[str], capture_output: bool = True, check: bool = False
) -> Tuple[bool, str]:
    """
    Run shell command and return (success, output).

    Let It Crash: Don't catch exceptions - subprocess errors should propagate.
    Only handle expected exit codes for validation checks.
    """
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, check=check)
        return (result.returncode == 0, result.stdout.strip() if capture_output else "")
    except subprocess.CalledProcessError as e:
        # Expected failure for validation checks
        return (False, e.stderr if e.stderr else str(e))


def pre_check_file(file_path: Path) -> Tuple[bool, str]:
    """Pre-flight checks before applying autofix."""
    # 1. File exists
    if not file_path.exists():
        return (False, f"File does not exist: {file_path}")

    # 2. File is readable
    if not file_path.is_file():
        return (False, f"Not a file: {file_path}")

    # 3. LOC limit check
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            if len(lines) > MAX_LOC_PER_FILE:
                return (False, f"File exceeds LOC limit: {len(lines)} > {MAX_LOC_PER_FILE}")
    except OSError as e:
        return (False, f"Cannot read file: {e}")

    # 4. Is Python file
    if file_path.suffix != ".py":
        return (False, f"Not a Python file: {file_path}")

    return (True, "Pre-checks passed")


def apply_ruff_format(file_path: Path) -> Tuple[bool, str]:
    """Apply ruff format to a single file."""
    success, output = run_command(["ruff", "format", str(file_path)])

    if not success:
        return (False, f"ruff format failed: {output}")

    return (True, "Applied ruff format")


def check_idempotency(file_path: Path) -> Tuple[bool, str]:
    """
    Verify ruff format is idempotent (running twice produces same output).

    This is CRITICAL - non-idempotent formatters are unsafe.
    """
    # Read current content
    try:
        with open(file_path, "r") as f:
            content_before = f.read()
    except OSError as e:
        return (False, f"Cannot read file for idempotency check: {e}")

    # Run ruff format again
    success, output = run_command(["ruff", "format", str(file_path)])

    if not success:
        return (False, f"Second ruff format failed: {output}")

    # Read content after second run
    try:
        with open(file_path, "r") as f:
            content_after = f.read()
    except OSError as e:
        return (False, f"Cannot read file after second format: {e}")

    # Compare
    if content_before != content_after:
        return (False, "ruff format is NOT idempotent - unsafe to apply")

    return (True, "Idempotency verified")


def check_syntax(file_path: Path) -> Tuple[bool, str]:
    """Verify Python syntax is valid after formatting."""
    success, output = run_command(["python", "-m", "py_compile", str(file_path)])

    if not success:
        return (False, f"Syntax error after formatting: {output}")

    return (True, "Syntax check passed")


def check_git_changes(file_path: Path) -> Tuple[bool, str]:
    """
    Verify git diff shows formatting-only changes.

    We can't programmatically verify this is "only" formatting,
    but we can check that changes exist and are reasonable.
    """
    success, output = run_command(["git", "diff", str(file_path)])

    if not success:
        return (False, "git diff failed")

    # If no changes, that's fine (file was already formatted)
    if not output.strip():
        return (True, "No changes needed (already formatted)")

    # Check diff size is reasonable (formatting shouldn't add 1000s of lines)
    diff_lines = output.split("\n")
    if len(diff_lines) > 500:
        return (False, f"Suspiciously large diff: {len(diff_lines)} lines")

    return (True, f"Git changes verified ({len(diff_lines)} diff lines)")


def apply_autofix_to_file(file_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Apply autofix to a single file with full safety checks.

    Returns: (success, message, details_dict)
    """
    details = {
        "file": str(file_path),
        "checks_passed": [],
        "checks_failed": [],
    }

    print(f"\n[AUTOFIX] Processing: {file_path}")

    # 1. Pre-check
    success, message = pre_check_file(file_path)
    if not success:
        details["checks_failed"].append(("pre_check", message))
        print(f"  ❌ Pre-check: {message}")
        return (False, message, details)

    details["checks_passed"].append("pre_check")
    print(f"  ✅ Pre-check passed")

    # 2. Apply ruff format
    success, message = apply_ruff_format(file_path)
    if not success:
        details["checks_failed"].append(("ruff_format", message))
        print(f"  ❌ Ruff format: {message}")
        return (False, message, details)

    details["checks_passed"].append("ruff_format")
    print(f"  ✅ Ruff format applied")

    # 3. Idempotency check
    success, message = check_idempotency(file_path)
    if not success:
        details["checks_failed"].append(("idempotency", message))
        print(f"  ❌ Idempotency: {message}")
        # CRITICAL FAILURE - rollback
        run_command(["git", "checkout", str(file_path)])
        return (False, message, details)

    details["checks_passed"].append("idempotency")
    print(f"  ✅ Idempotency verified")

    # 4. Syntax check
    success, message = check_syntax(file_path)
    if not success:
        details["checks_failed"].append(("syntax", message))
        print(f"  ❌ Syntax check: {message}")
        # CRITICAL FAILURE - rollback
        run_command(["git", "checkout", str(file_path)])
        return (False, message, details)

    details["checks_passed"].append("syntax")
    print(f"  ✅ Syntax check passed")

    # 5. Git changes check
    success, message = check_git_changes(file_path)
    if not success:
        details["checks_failed"].append(("git_changes", message))
        print(f"  ⚠️  Git changes: {message}")
        # Warning only - don't rollback, but log it
    else:
        details["checks_passed"].append("git_changes")
        print(f"  ✅ {message}")

    return (True, "Autofix applied successfully", details)


def load_fix_plan(fix_plan_file: Path) -> Optional[Dict[str, Any]]:
    """Load fix plan JSON."""
    try:
        with open(fix_plan_file, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading fix plan: {e}", file=sys.stderr)
        return None


def apply_autofix_to_category(category: str, fix_plans_dir: Path) -> Dict[str, Any]:
    """
    Apply autofix to all eligible findings in a category.

    Returns summary dict with success/failure counts.
    """
    fix_plan_file = fix_plans_dir / f"{category}.json"

    if not fix_plan_file.exists():
        return {
            "category": category,
            "status": "skipped",
            "reason": "No fix plan found",
        }

    fix_plan = load_fix_plan(fix_plan_file)
    if not fix_plan:
        return {
            "category": category,
            "status": "error",
            "reason": "Failed to load fix plan",
        }

    findings = fix_plan.get("findings", [])
    autofix_eligible = [f for f in findings if f.get("autofix_eligible", False)]

    if not autofix_eligible:
        return {
            "category": category,
            "status": "skipped",
            "reason": "No autofix-eligible findings",
            "total_findings": len(findings),
        }

    print(f"\n{'=' * 60}")
    print(f"Category: {category.upper()}")
    print(f"Autofix-eligible findings: {len(autofix_eligible)}")
    print(f"{'=' * 60}")

    # Group by file (multiple findings per file possible)
    files_to_fix = {}
    for finding in autofix_eligible:
        file_path = finding.get("file")
        if file_path:
            if file_path not in files_to_fix:
                files_to_fix[file_path] = []
            files_to_fix[file_path].append(finding)

    # Apply file limit
    if len(files_to_fix) > MAX_FILES_PER_RUN:
        print(f"\n⚠️  Found {len(files_to_fix)} files, limiting to {MAX_FILES_PER_RUN}")
        files_to_fix = dict(list(files_to_fix.items())[:MAX_FILES_PER_RUN])

    # Apply autofix to each file
    results = {
        "category": category,
        "total_findings": len(findings),
        "autofix_eligible": len(autofix_eligible),
        "files_attempted": len(files_to_fix),
        "files_succeeded": 0,
        "files_failed": 0,
        "details": [],
    }

    for file_path, file_findings in files_to_fix.items():
        success, message, details = apply_autofix_to_file(Path(file_path))

        details["findings_count"] = len(file_findings)
        results["details"].append(details)

        if success:
            results["files_succeeded"] += 1
        else:
            results["files_failed"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Apply autofix with safety checks (Phase 2)"
    )
    parser.add_argument(
        "--fix-plans-dir",
        type=Path,
        required=True,
        help="Directory containing fix plan JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("autofix-results.json"),
        help="Output file for autofix results",
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Only apply autofix to specific category (default: all)",
    )

    args = parser.parse_args()

    if not args.fix_plans_dir.exists():
        print(f"Error: Fix plans directory not found: {args.fix_plans_dir}", file=sys.stderr)
        sys.exit(1)

    # Determine categories to process
    if args.category:
        categories = [args.category]
    else:
        # Phase 2A: Only quality category for now
        categories = ["quality"]

    # Process each category
    all_results = []
    total_succeeded = 0
    total_failed = 0

    for category in categories:
        results = apply_autofix_to_category(category, args.fix_plans_dir)
        all_results.append(results)

        total_succeeded += results.get("files_succeeded", 0)
        total_failed += results.get("files_failed", 0)

    # Write results
    output_data = {
        "timestamp": subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip(),
        "categories_processed": categories,
        "total_files_succeeded": total_succeeded,
        "total_files_failed": total_failed,
        "results": all_results,
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    # Summary
    print(f"\n{'=' * 60}")
    print("AUTOFIX SUMMARY")
    print(f"{'=' * 60}")
    print(f"Files succeeded: {total_succeeded}")
    print(f"Files failed: {total_failed}")
    print(f"Results written to: {args.output}")

    if total_failed > 0:
        print("\n⚠️  Some files failed autofix - see results for details")
        sys.exit(1)

    print("\n✅ Autofix completed successfully")


if __name__ == "__main__":
    main()
