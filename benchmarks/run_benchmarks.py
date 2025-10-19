#!/usr/bin/env python3
"""
Lightweight benchmarking harness for SuperClaude.

The README references `python benchmarks/run_benchmarks.py` for validating the
stack. This script currently proxies to fast smoke tests so the command succeeds
while the dedicated performance suite is under construction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import subprocess
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_pytest(targets: Sequence[str]) -> int:
    """Execute pytest for the given targets relative to the repository root."""
    try:
        import pytest  # type: ignore
    except ImportError:
        cmd = ["pytest", "-q", *targets]
        completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
        return completed.returncode
    else:
        absolute_targets = [str(REPO_ROOT / target) for target in targets]
        return pytest.main(["-q", *absolute_targets])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SuperClaude benchmark harness (placeholder)."
    )
    parser.add_argument(
        "--suite",
        choices=("smoke", "integration", "full"),
        default="smoke",
        help="Benchmark suite to execute (defaults to the fast smoke tests).",
    )
    args = parser.parse_args(argv)

    if args.suite == "smoke":
        targets = ["tests/test_version.py"]
    elif args.suite == "integration":
        targets = ["tests/test_integration.py"]
    else:  # full
        targets = [
            "tests/test_version.py",
            "tests/test_integration.py",
        ]

    print(f"Running {args.suite} benchmark suite using pytest…")
    exit_code = run_pytest(targets)
    if exit_code == 0:
        print("✅ Benchmark harness completed without failures.")
    else:
        print("❌ Benchmark harness reported failures.", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
