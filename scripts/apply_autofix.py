#!/usr/bin/env python3
"""
Autofix Application Engine (Phase 2)

Applies deterministic fixes with comprehensive safety checks:
1. Pre-check: File validation, allowlist, LOC limits
2. Apply: Run fix handler dispatched from fix-type registry
3. Validate: Multi-pass idempotency check
4. Syntax check: Python compilation
5. Git check: Ensure reasonable changes

Rollback on any failure.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import allowlist checker from normalize_findings
sys.path.insert(0, str(Path(__file__).parent))
from fix_type_registry import FixType, get_fix_type
from normalize_findings import is_file_allowed_for_autofix

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

    # 3. Allowlist check (SECURITY: must come before any file operations)
    if not is_file_allowed_for_autofix(str(file_path)):
        return (False, f"File not in autofix allowlist: {file_path}")

    # 4. Path traversal check (SECURITY: prevent ../../../ attacks)
    try:
        file_path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return (False, f"File outside repository: {file_path}")

    # 5. LOC limit check
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
            if len(lines) > MAX_LOC_PER_FILE:
                return (False, f"File exceeds LOC limit: {len(lines)} > {MAX_LOC_PER_FILE}")
    except OSError as e:
        return (False, f"Cannot read file: {e}")

    # 6. Is Python file
    if file_path.suffix != ".py":
        return (False, f"Not a Python file: {file_path}")

    return (True, "Pre-checks passed")


def build_fix_command(fix_type: FixType, file_path: Path) -> List[str]:
    """Build the shell command for a fix type, substituting placeholders."""
    cmd_str = fix_type.tool_command.replace("{file}", str(file_path))

    if fix_type.ruff_select_codes and "{codes}" in cmd_str:
        codes = ",".join(fix_type.ruff_select_codes)
        cmd_str = cmd_str.replace("{codes}", codes)

    return cmd_str.split()


def apply_fix(file_path: Path, fix_type_name: str) -> Tuple[bool, str]:
    """Apply a fix from the registry to a single file."""
    fix_type = get_fix_type(fix_type_name)
    if fix_type is None:
        return (False, f"Unknown fix type: {fix_type_name}")

    cmd = build_fix_command(fix_type, file_path)
    success, output = run_command(cmd)

    if not success:
        return (False, f"{fix_type_name} failed: {output}")

    return (True, f"Applied {fix_type_name}")


def check_idempotency(file_path: Path, fix_type_name: str = "ruff_format") -> Tuple[bool, str]:
    """
    Verify fix is idempotent via multi-pass stabilization.

    For deterministic tools (max_passes=1): run twice, compare.
    For lint fixers (max_passes>1): run up to max_passes until output stabilizes.

    This is CRITICAL - non-idempotent fixes are unsafe.
    """
    fix_type = get_fix_type(fix_type_name)
    max_passes = fix_type.max_passes if fix_type else 1

    for pass_num in range(max_passes):
        try:
            with open(file_path, "r") as f:
                content_before = f.read()
        except OSError as e:
            return (False, f"Cannot read file for idempotency check: {e}")

        success, output = apply_fix(file_path, fix_type_name)
        if not success:
            return (False, f"Pass {pass_num + 1} failed: {output}")

        try:
            with open(file_path, "r") as f:
                content_after = f.read()
        except OSError as e:
            return (False, f"Cannot read file after pass {pass_num + 1}: {e}")

        if content_before == content_after:
            return (True, f"Idempotency verified (stabilized after {pass_num + 1} pass(es))")

    return (False, f"{fix_type_name} is NOT idempotent after {max_passes} passes - unsafe to apply")


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
    success, output = run_command(["git", "diff", "--", str(file_path)])

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


def apply_autofix_to_file(
    file_path: Path, fix_type_name: str = "ruff_format"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Apply autofix to a single file with full safety checks.

    The fix_type_name dispatches to the appropriate handler from the registry.
    Returns: (success, message, details_dict)
    """
    details = {
        "file": str(file_path),
        "fix_type": fix_type_name,
        "checks_passed": [],
        "checks_failed": [],
    }

    print(f"\n[AUTOFIX] Processing: {file_path} (fix_type={fix_type_name})")

    # 1. Pre-check
    success, message = pre_check_file(file_path)
    if not success:
        details["checks_failed"].append(("pre_check", message))
        print(f"  FAIL Pre-check: {message}")
        return (False, message, details)

    details["checks_passed"].append("pre_check")
    print("  OK Pre-check passed")

    # 2. Apply fix (dispatched from registry)
    success, message = apply_fix(file_path, fix_type_name)
    if not success:
        details["checks_failed"].append((fix_type_name, message))
        print(f"  FAIL {fix_type_name}: {message}")
        return (False, message, details)

    details["checks_passed"].append(fix_type_name)
    print(f"  OK {fix_type_name} applied")

    # 3. Idempotency check (multi-pass for lint fixes)
    success, message = check_idempotency(file_path, fix_type_name)
    if not success:
        details["checks_failed"].append(("idempotency", message))
        print(f"  FAIL Idempotency: {message}")
        # CRITICAL FAILURE - rollback
        run_command(["git", "restore", "--source=HEAD", "--", str(file_path)])
        return (False, message, details)

    details["checks_passed"].append("idempotency")
    print("  OK Idempotency verified")

    # 4. Syntax check
    success, message = check_syntax(file_path)
    if not success:
        details["checks_failed"].append(("syntax", message))
        print(f"  FAIL Syntax check: {message}")
        # CRITICAL FAILURE - rollback
        run_command(["git", "restore", "--source=HEAD", "--", str(file_path)])
        return (False, message, details)

    details["checks_passed"].append("syntax")
    print("  OK Syntax check passed")

    # 5. Git changes check
    success, message = check_git_changes(file_path)
    if not success:
        details["checks_failed"].append(("git_changes", message))
        print(f"  WARN Git changes: {message}")
        # Warning only - don't rollback, but log it
    else:
        details["checks_passed"].append("git_changes")
        print(f"  OK {message}")

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
        # Use the resolved fix type from normalization, default to ruff_format
        fix_type_name = file_findings[0].get("_resolved_fix_type", "ruff_format")
        success, message, details = apply_autofix_to_file(Path(file_path), fix_type_name)

        details["findings_count"] = len(file_findings)
        results["details"].append(details)

        if success:
            results["files_succeeded"] += 1
        else:
            results["files_failed"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="Apply autofix with safety checks (Phase 2)")
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
