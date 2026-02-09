#!/usr/bin/env python3
"""SuperClaude benchmark harness.

Runs curated pytest and CLI checks while recording execution time so the project
has a tangible performance signal instead of a placeholder script.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import textwrap
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class BenchmarkCase:
    """Single benchmark case to execute."""

    name: str
    command: Sequence[str]
    description: str
    env: Mapping[str, str] | None = None


@dataclass
class BenchmarkResult:
    name: str
    description: str
    duration_s: float
    success: bool
    returncode: int
    stdout: str
    stderr: str


def _pytest_case(name: str, target: str, description: str) -> BenchmarkCase:
    env = {
        **os.environ,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    return BenchmarkCase(
        name=name,
        command=("pytest", "-q", target),
        description=description,
        env=env,
    )


def _cli_case(name: str, command: Sequence[str], description: str) -> BenchmarkCase:
    return BenchmarkCase(name=name, command=command, description=description)


SUITES: Mapping[str, list[BenchmarkCase]] = {
    "smoke": [
        _cli_case(
            "cli-help",
            (sys.executable, "-m", "SuperClaude", "--help"),
            "Ensure the SuperClaude CLI responds to --help.",
        ),
        _pytest_case(
            "core-smoke",
            "tests/core/test_smoke.py",
            "Run core module smoke tests.",
        ),
    ],
    "integration": [
        _pytest_case(
            "core-tests",
            "tests/core/",
            "Exercise core module tests.",
        ),
        _pytest_case(
            "orchestrator-tests",
            "tests/orchestrator/",
            "Exercise orchestrator tests.",
        ),
    ],
    "full": [
        BenchmarkCase(
            name="quality-suite",
            command=("pytest", "-m", "not slow", "tests"),
            description="Run the primary pytest suite (excluding slow markers).",
            env={
                **os.environ,
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            },
        ),
        _cli_case(
            "benchmark-report",
            (sys.executable, "scripts/report_agent_usage.py"),
            "Generate the agent usage report to confirm telemetry parsing.",
        ),
    ],
}


def run_case(case: BenchmarkCase) -> BenchmarkResult:
    env: MutableMapping[str, str] = dict(os.environ)
    if case.env:
        env.update(case.env)

    start = perf_counter()
    completed = subprocess.run(
        case.command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = perf_counter() - start

    return BenchmarkResult(
        name=case.name,
        description=case.description,
        duration_s=duration,
        success=completed.returncode == 0,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _format_result(result: BenchmarkResult) -> str:
    status = "PASS" if result.success else "FAIL"
    return f"[{status:4}] {result.name:<20} {result.duration_s:6.2f}s — {result.description}"


def _print_details(result: BenchmarkResult) -> None:
    if result.stdout.strip():
        print(textwrap.indent(result.stdout.rstrip(), prefix="    >> "))
    if result.stderr.strip():
        print(textwrap.indent(result.stderr.rstrip(), prefix="    !! "))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SuperClaude benchmark harness")
    parser.add_argument(
        "--suite",
        choices=tuple(SUITES.keys()),
        default="smoke",
        help="Benchmark suite to execute (defaults to smoke).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print stdout/stderr from each benchmark case.",
    )
    args = parser.parse_args(argv)

    cases: Iterable[BenchmarkCase] = SUITES[args.suite]
    print(f"Running {args.suite} benchmark suite…")

    results = [run_case(case) for case in cases]
    for result in results:
        print(_format_result(result))
        if args.verbose:
            _print_details(result)

    success = all(result.success for result in results)
    total_time = sum(result.duration_s for result in results)
    print(f"Total time: {total_time:.2f}s")

    if not success:
        failing = [r for r in results if not r.success]
        print(f"\nFailures: {len(failing)}", file=sys.stderr)
        for result in failing:
            print(_format_result(result), file=sys.stderr)
            _print_details(result)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
