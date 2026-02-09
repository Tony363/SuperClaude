#!/usr/bin/env python3
"""Compute pass rates for E2E application generation tests.

Aggregates results from individual test runs and computes pass rates per app.

Usage:
    python scripts/compute_e2e_pass_rates.py --input artifacts/e2e/
    python scripts/compute_e2e_pass_rates.py --input artifacts/e2e/ --format markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_results(input_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all E2E test results from input directory.

    Args:
        input_dir: Directory containing result-* subdirectories

    Returns:
        Dict mapping app names to list of results
    """
    results: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for result_dir in input_dir.glob("result-*"):
        if not result_dir.is_dir():
            continue

        result_file = result_dir / "e2e-result.json"
        if not result_file.exists():
            continue

        try:
            data = json.loads(result_file.read_text())
            app_name = data.get("app_name", "unknown")
            results[app_name].append(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to parse {result_file}: {e}", file=sys.stderr)

    return dict(results)


def compute_pass_rates(
    results: dict[str, list[dict[str, Any]]],
    threshold: float,
) -> dict[str, dict[str, Any]]:
    """Compute pass rates for each app.

    Args:
        results: Dict mapping app names to list of results
        threshold: Minimum pass rate to consider the app as passing

    Returns:
        Dict with pass rate information per app
    """
    pass_rates = {}

    for app_name, runs in results.items():
        total = len(runs)
        passed = sum(1 for r in runs if r.get("passed", False))
        rate = passed / total if total > 0 else 0.0

        # Compute average times
        gen_times = [r.get("generation_time_seconds", 0) for r in runs]
        val_times = [r.get("validation_time_seconds", 0) for r in runs]
        total_times = [r.get("total_time_seconds", 0) for r in runs]

        pass_rates[app_name] = {
            "total_runs": total,
            "passed_runs": passed,
            "pass_rate": rate,
            "threshold": threshold,
            "met_threshold": rate >= threshold,
            "avg_generation_time": sum(gen_times) / len(gen_times) if gen_times else 0,
            "avg_validation_time": sum(val_times) / len(val_times) if val_times else 0,
            "avg_total_time": sum(total_times) / len(total_times) if total_times else 0,
        }

    return pass_rates


def format_console(pass_rates: dict[str, dict[str, Any]]) -> str:
    """Format results for console output."""
    lines = []
    lines.append("=" * 60)
    lines.append("E2E Application Generation Test Results")
    lines.append("=" * 60)
    lines.append("")

    all_passed = True

    for app_name, data in sorted(pass_rates.items()):
        status = "PASS" if data["met_threshold"] else "FAIL"
        passed = data["passed_runs"]
        total = data["total_runs"]
        rate = data["pass_rate"] * 100
        threshold = data["threshold"] * 100

        lines.append(f"{app_name}:")
        lines.append(f"  Status: {status}")
        lines.append(f"  Pass rate: {passed}/{total} ({rate:.0f}%)")
        lines.append(f"  Threshold: {threshold:.0f}%")
        lines.append(f"  Avg generation time: {data['avg_generation_time']:.1f}s")
        lines.append(f"  Avg validation time: {data['avg_validation_time']:.1f}s")
        lines.append("")

        if not data["met_threshold"]:
            all_passed = False

    lines.append("=" * 60)
    overall = "PASSED" if all_passed else "FAILED"
    lines.append(f"Overall: {overall}")
    lines.append("=" * 60)

    return "\n".join(lines)


def format_markdown(pass_rates: dict[str, dict[str, Any]]) -> str:
    """Format results as markdown table."""
    lines = []
    lines.append("# E2E Application Generation Test Results")
    lines.append("")
    lines.append("| App | Status | Pass Rate | Threshold | Avg Time |")
    lines.append("|-----|--------|-----------|-----------|----------|")

    all_passed = True

    for app_name, data in sorted(pass_rates.items()):
        status = ":white_check_mark:" if data["met_threshold"] else ":x:"
        passed = data["passed_runs"]
        total = data["total_runs"]
        rate = data["pass_rate"] * 100
        threshold = data["threshold"] * 100
        avg_time = data["avg_total_time"]

        lines.append(
            f"| {app_name} | {status} | {passed}/{total} ({rate:.0f}%) | {threshold:.0f}% | {avg_time:.1f}s |"
        )

        if not data["met_threshold"]:
            all_passed = False

    lines.append("")

    if all_passed:
        lines.append("**Overall: :white_check_mark: PASSED**")
    else:
        lines.append("**Overall: :x: FAILED**")

    return "\n".join(lines)


def format_json(pass_rates: dict[str, dict[str, Any]]) -> str:
    """Format results as JSON."""
    all_passed = all(data["met_threshold"] for data in pass_rates.values())

    output = {
        "apps": pass_rates,
        "all_passed": all_passed,
        "summary": {
            "total_apps": len(pass_rates),
            "passed_apps": sum(1 for d in pass_rates.values() if d["met_threshold"]),
        },
    }

    return json.dumps(output, indent=2)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compute E2E test pass rates")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts/e2e"),
        help="Input directory containing result files",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.67,
        help="Pass rate threshold (default: 0.67)",
    )
    parser.add_argument(
        "--format",
        choices=["console", "markdown", "json"],
        default="console",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input directory not found: {args.input}", file=sys.stderr)
        return 1

    # Load and process results
    results = load_results(args.input)

    if not results:
        print("Warning: No results found", file=sys.stderr)
        return 1

    pass_rates = compute_pass_rates(results, args.threshold)

    # Format output
    formatters = {
        "console": format_console,
        "markdown": format_markdown,
        "json": format_json,
    }

    output = formatters[args.format](pass_rates)

    # Write output
    if args.output:
        args.output.write_text(output)
    else:
        print(output)

    # Return exit code based on results
    all_passed = all(data["met_threshold"] for data in pass_rates.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
