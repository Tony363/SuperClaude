#!/usr/bin/env python3
"""
Compute pass rates from stochastic test runs.

This script aggregates individual test run results and computes
pass rates per agent. It's designed to be run in GitHub Actions
after all matrix jobs complete.

Usage:
    python scripts/compute_pass_rates.py --input artifacts/ --threshold 0.8
    python scripts/compute_pass_rates.py --input artifacts/ --output $GITHUB_STEP_SUMMARY
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def find_result_files(input_dir: Path) -> list[Path]:
    """Find all result JSON files in the artifacts directory.

    Handles GitHub Actions artifact structure where each artifact
    is in its own subdirectory.
    """
    result_files = []

    # Direct files (local testing)
    result_files.extend(input_dir.glob("*.json"))

    # Nested in artifact subdirectories (GitHub Actions)
    for subdir in input_dir.iterdir():
        if subdir.is_dir():
            result_files.extend(subdir.glob("*.json"))

    return sorted(result_files)


def load_results(input_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Load all result files and group by agent."""
    agent_results: dict[str, list[dict[str, Any]]] = defaultdict(list)

    result_files = find_result_files(input_dir)

    for result_file in result_files:
        try:
            data = json.loads(result_file.read_text())
            agent = data.get("agent", "unknown")
            agent_results[agent].append(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not parse {result_file}: {e}", file=sys.stderr)

    return dict(agent_results)


def compute_pass_rates(
    agent_results: dict[str, list[dict[str, Any]]],
    threshold: float = 0.8,
) -> tuple[dict[str, dict[str, Any]], bool]:
    """Compute pass rates for each agent.

    Returns:
        Tuple of (results dict, all_passed bool)
    """
    results = {}
    all_passed = True

    for agent, runs in sorted(agent_results.items()):
        # Sort runs by run number if available
        runs_sorted = sorted(runs, key=lambda r: r.get("run", 0))

        passes = sum(1 for r in runs_sorted if r.get("passed", False))
        total = len(runs_sorted)
        pass_rate = passes / total if total > 0 else 0.0
        passed = pass_rate >= threshold

        results[agent] = {
            "passes": passes,
            "total": total,
            "pass_rate": pass_rate,
            "threshold": threshold,
            "passed": passed,
            "runs": [
                {
                    "run": r.get("run", i + 1),
                    "passed": r.get("passed", False),
                    "score": r.get("score"),
                }
                for i, r in enumerate(runs_sorted)
            ],
        }

        if not passed:
            all_passed = False

    return results, all_passed


def format_console_output(
    results: dict[str, dict[str, Any]],
    threshold: float,
) -> str:
    """Format results for console output."""
    lines = [
        f"Stochastic Evaluation Results ({int(threshold * 100)}% threshold)",
        "=" * 55,
        "",
    ]

    for agent, data in results.items():
        lines.append(f"{agent}:")
        for run in data["runs"]:
            status = "\u2705" if run["passed"] else "\u274c"
            score_str = f" (score: {run['score']})" if run.get("score") else ""
            lines.append(f"  Run {run['run']}: {status}{score_str}")

        status = "\u2705 MEETS THRESHOLD" if data["passed"] else "\u274c BELOW THRESHOLD"
        lines.append(
            f"  Result: {data['passes']}/{data['total']} "
            f"({data['pass_rate']:.0%}) {status}"
        )
        lines.append("")

    return "\n".join(lines)


def format_markdown_output(
    results: dict[str, dict[str, Any]],
    threshold: float,
) -> str:
    """Format results as GitHub-flavored markdown."""
    lines = [
        f"# Stochastic Evaluation Results",
        "",
        f"**Threshold**: {int(threshold * 100)}% ({int(threshold * 5)}/5 runs)",
        "",
        "## Summary",
        "",
        "| Agent | Pass Rate | Status |",
        "|-------|-----------|--------|",
    ]

    for agent, data in results.items():
        status = "\u2705" if data["passed"] else "\u274c"
        lines.append(
            f"| {agent} | {data['passes']}/{data['total']} ({data['pass_rate']:.0%}) | {status} |"
        )

    lines.extend(["", "## Details", ""])

    for agent, data in results.items():
        status = "\u2705" if data["passed"] else "\u274c"
        lines.append(f"### {agent} {status}")
        lines.append("")

        for run in data["runs"]:
            run_status = "\u2705" if run["passed"] else "\u274c"
            score_str = f" (score: {run['score']})" if run.get("score") else ""
            lines.append(f"- Run {run['run']}: {run_status}{score_str}")

        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compute pass rates from stochastic test runs"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts"),
        help="Directory containing result JSON files",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Pass rate threshold (default: 0.8 = 80%%)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (use $GITHUB_STEP_SUMMARY for Actions)",
    )
    parser.add_argument(
        "--format",
        choices=["console", "markdown", "json"],
        default="console",
        help="Output format",
    )

    args = parser.parse_args()

    # Load results
    if not args.input.exists():
        print(f"Error: Input directory '{args.input}' does not exist", file=sys.stderr)
        return 1

    agent_results = load_results(args.input)

    if not agent_results:
        print("Error: No result files found", file=sys.stderr)
        return 1

    # Compute pass rates
    results, all_passed = compute_pass_rates(agent_results, args.threshold)

    # Format output
    if args.format == "json":
        output = json.dumps(
            {
                "threshold": args.threshold,
                "all_passed": all_passed,
                "agents": results,
            },
            indent=2,
        )
    elif args.format == "markdown":
        output = format_markdown_output(results, args.threshold)
    else:
        output = format_console_output(results, args.threshold)

    # Write output
    if args.output:
        output_path = Path(args.output)
        # Append to file (for GITHUB_STEP_SUMMARY)
        with open(output_path, "a") as f:
            f.write(output)
            f.write("\n")
        print(f"Results written to {output_path}")
    else:
        print(output)

    # Exit code based on pass/fail
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
