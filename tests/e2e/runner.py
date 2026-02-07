#!/usr/bin/env python3
"""E2E Application Generation Test Runner.

This module executes end-to-end tests that verify SuperClaude can generate
complete, working applications from prompts. It invokes Claude CLI, runs
language-specific validators, and reports pass/fail results.

Usage:
    python tests/e2e/runner.py                          # Run all apps, 1 run each
    python tests/e2e/runner.py --app python-cli-calculator  # Single app
    python tests/e2e/runner.py --runs 3                 # 3 runs per app
    python tests/e2e/runner.py --dry-run                # Show what would run
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add project root to path for imports when running as script
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import yaml


@dataclass
class E2ETestResult:
    """Result of a single E2E test run."""

    app_name: str
    run_number: int
    passed: bool
    reason: str
    generation_time_seconds: float = 0.0
    validation_time_seconds: float = 0.0
    total_time_seconds: float = 0.0
    validation_steps: list[dict[str, Any]] = field(default_factory=list)
    workdir: str | None = None
    error: str | None = None


@dataclass
class E2ETestSummary:
    """Summary of all E2E test runs for an app."""

    app_name: str
    runs: list[E2ETestResult]
    threshold: float
    passed: bool = False

    @property
    def pass_rate(self) -> float:
        if not self.runs:
            return 0.0
        return sum(1 for r in self.runs if r.passed) / len(self.runs)

    def __post_init__(self):
        self.passed = self.pass_rate >= self.threshold


def load_e2e_config(config_path: Path) -> dict[str, Any]:
    """Load E2E test configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_validator(language: str):
    """Get the appropriate validator for a language."""
    from tests.e2e.validators import NodeValidator, PythonValidator, RustValidator

    validators = {
        "python": PythonValidator,
        "node": NodeValidator,
        "rust": RustValidator,
    }

    validator_class = validators.get(language)
    if not validator_class:
        raise ValueError(f"No validator for language: {language}")

    return validator_class()


def run_claude_generation(
    prompt: str,
    workdir: Path,
    timeout: int = 300,
) -> tuple[bool, str, float]:
    """Run Claude CLI to generate application code.

    Args:
        prompt: The generation prompt
        workdir: Directory where code should be generated
        timeout: Maximum time in seconds

    Returns:
        Tuple of (success, message, duration_seconds)
    """
    start_time = time.time()

    # Build the full prompt with workspace context
    full_prompt = f"""You are generating code in the directory: {workdir}

IMPORTANT: Create ALL files directly in this directory or subdirectories as specified.
Do NOT create any wrapper directories. The files should be at the root level unless
the prompt specifies a subdirectory structure.

{prompt}

After creating all files, provide a brief summary of what was created."""

    cmd = [
        "claude",
        "-p",
        full_prompt,
        "--allowedTools",
        "Bash,Read,Write,Edit",
        "--output-format",
        "text",
        "--max-turns",
        "20",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(workdir),
        )

        duration = time.time() - start_time
        output = result.stdout.strip()

        if result.returncode == 0 and output:
            return True, "Generation completed", duration

        # Check if any files were created despite error
        created_files = list(workdir.iterdir())
        if created_files:
            return True, f"Generation completed with {len(created_files)} items", duration

        return False, f"Generation failed: {result.stderr[:500]}", duration

    except subprocess.TimeoutExpired:
        return False, "Generation timed out", time.time() - start_time
    except FileNotFoundError:
        return (
            False,
            "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code",
            0,
        )
    except Exception as e:
        return False, f"Generation error: {e}", time.time() - start_time


def run_single_test(
    app_name: str,
    app_config: dict[str, Any],
    run_number: int,
    base_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
    keep_workdir: bool = False,
) -> E2ETestResult:
    """Run a single E2E test for an application.

    Args:
        app_name: Name of the application being tested
        app_config: Configuration for this app from e2e_apps.yaml
        run_number: Which run this is (1, 2, 3, etc.)
        base_dir: SuperClaude root directory
        output_dir: Directory for test artifacts
        dry_run: If True, don't actually run tests
        keep_workdir: If True, keep workdir even on success

    Returns:
        E2ETestResult with pass/fail status and details
    """
    start_time = time.time()
    language = app_config.get("language", "python")
    prompt = app_config.get("prompt", "")
    timeout = app_config.get("timeout_seconds", 300)

    print(f"\n{'=' * 60}")
    print(f"Running: {app_name} (run {run_number})")
    print(f"Language: {language}")
    print(f"Timeout: {timeout}s")

    if dry_run:
        print("[DRY RUN] Would execute test here")
        return E2ETestResult(
            app_name=app_name,
            run_number=run_number,
            passed=True,
            reason="DRY RUN",
            total_time_seconds=0,
        )

    # Create isolated temp directory for this test
    workdir = Path(tempfile.mkdtemp(prefix=f"e2e_test_{app_name}_"))
    print(f"Workdir: {workdir}")

    try:
        # Step 1: Generate the application
        print("\n[1/2] Generating application...")
        gen_success, gen_message, gen_time = run_claude_generation(
            prompt, workdir, timeout
        )
        print(f"      {gen_message} ({gen_time:.1f}s)")

        if not gen_success:
            return E2ETestResult(
                app_name=app_name,
                run_number=run_number,
                passed=False,
                reason=f"Generation failed: {gen_message}",
                generation_time_seconds=gen_time,
                total_time_seconds=time.time() - start_time,
                workdir=str(workdir),
            )

        # Step 2: Validate the generated application
        print("\n[2/2] Validating application...")
        validator = get_validator(language)

        # Add app_name to config for reporting
        config_with_name = {**app_config, "app_name": app_name}
        report = validator.validate(workdir, config_with_name)

        validation_time = report.total_duration_seconds
        print(f"      {report.summary} ({validation_time:.1f}s)")

        # Convert validation steps to serializable format
        validation_steps = [
            {
                "step": step.step,
                "passed": step.passed,
                "message": step.message,
                "duration": step.duration_seconds,
            }
            for step in report.steps
        ]

        result = E2ETestResult(
            app_name=app_name,
            run_number=run_number,
            passed=report.passed,
            reason=report.summary,
            generation_time_seconds=gen_time,
            validation_time_seconds=validation_time,
            total_time_seconds=time.time() - start_time,
            validation_steps=validation_steps,
            workdir=str(workdir) if not report.passed or keep_workdir else None,
            error=report.error,
        )

        # Cleanup on success (unless keep_workdir is True)
        settings = app_config.get("settings", {})
        cleanup_on_success = settings.get("cleanup_on_success", True) and not keep_workdir
        cleanup_on_failure = settings.get("cleanup_on_failure", False)

        if report.passed and cleanup_on_success:
            validator.cleanup(workdir)
            shutil.rmtree(workdir, ignore_errors=True)
            result.workdir = None
        elif not report.passed and cleanup_on_failure:
            validator.cleanup(workdir)
            shutil.rmtree(workdir, ignore_errors=True)
            result.workdir = None

        return result

    except Exception as e:
        return E2ETestResult(
            app_name=app_name,
            run_number=run_number,
            passed=False,
            reason=f"Test error: {e}",
            total_time_seconds=time.time() - start_time,
            workdir=str(workdir),
            error=str(e),
        )


def save_result(result: E2ETestResult, output_dir: Path) -> None:
    """Save a test result to disk."""
    result_dir = output_dir / f"result-{result.app_name}-run{result.run_number}"
    result_dir.mkdir(parents=True, exist_ok=True)

    result_file = result_dir / "e2e-result.json"
    result_data = {
        "app_name": result.app_name,
        "run": result.run_number,
        "passed": result.passed,
        "reason": result.reason,
        "generation_time_seconds": result.generation_time_seconds,
        "validation_time_seconds": result.validation_time_seconds,
        "total_time_seconds": result.total_time_seconds,
        "validation_steps": result.validation_steps,
        "workdir": result.workdir,
        "error": result.error,
    }

    result_file.write_text(json.dumps(result_data, indent=2))


def print_summary(summaries: list[E2ETestSummary]) -> None:
    """Print a summary of all test results."""
    print(f"\n{'=' * 60}")
    print("E2E TEST SUMMARY")
    print(f"{'=' * 60}\n")

    all_passed = True
    for summary in summaries:
        status = "PASS" if summary.passed else "FAIL"
        passed_runs = sum(1 for r in summary.runs if r.passed)
        total_runs = len(summary.runs)
        rate = summary.pass_rate * 100

        print(f"{summary.app_name}:")
        print(f"  Status: {status}")
        print(f"  Pass rate: {passed_runs}/{total_runs} ({rate:.0f}%)")
        print(f"  Threshold: {summary.threshold * 100:.0f}%")
        print()

        if not summary.passed:
            all_passed = False

    overall = "PASSED" if all_passed else "FAILED"
    print(f"Overall: {overall}")
    print(f"{'=' * 60}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run E2E application generation tests")
    parser.add_argument(
        "--app",
        type=str,
        default=None,
        help="Specific app to test (default: all)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs per app (default: 1)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Pass rate threshold (default: from config)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/e2e"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("evals/e2e_apps.yaml"),
        help="Test configuration file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be run without executing",
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Keep working directories even on success",
    )

    args = parser.parse_args()

    # Determine base directory
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent.parent  # SuperClaude root

    config_path = base_dir / args.config
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    # Load configuration
    config = load_e2e_config(config_path)
    apps = config.get("apps", {})
    settings = config.get("settings", {})

    if args.app:
        if args.app not in apps:
            print(f"Error: App '{args.app}' not found in config")
            print(f"Available apps: {', '.join(apps.keys())}")
            return 1
        apps = {args.app: apps[args.app]}

    # Setup output directory
    output_dir = base_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print("E2E Application Generation Tests")
    print(f"{'=' * 60}")
    print(f"Apps: {len(apps)}")
    print(f"Runs per app: {args.runs}")
    print(f"Total tests: {len(apps) * args.runs}")
    print(f"Output directory: {output_dir}")
    print(f"Dry run: {args.dry_run}")

    # Run tests
    summaries: list[E2ETestSummary] = []

    for app_name, app_config in apps.items():
        # Merge global settings into app config
        merged_config = {**settings, **app_config}

        # Determine threshold
        threshold = args.threshold
        if threshold is None:
            app_type = app_config.get("type", "standard")
            thresholds = settings.get("thresholds", {})
            threshold = app_config.get(
                "threshold", thresholds.get(app_type, settings.get("default_threshold", 0.67))
            )

        results: list[E2ETestResult] = []

        for run in range(1, args.runs + 1):
            result = run_single_test(
                app_name,
                merged_config,
                run,
                base_dir,
                output_dir,
                args.dry_run,
                args.keep_workdir,
            )
            results.append(result)
            save_result(result, output_dir)

            status = "PASS" if result.passed else "FAIL"
            print(f"\nResult: {status} - {result.reason}")

        summary = E2ETestSummary(
            app_name=app_name,
            runs=results,
            threshold=threshold,
        )
        summaries.append(summary)

    # Print final summary
    print_summary(summaries)

    # Save aggregated results
    aggregated = {
        "summaries": [
            {
                "app_name": s.app_name,
                "pass_rate": s.pass_rate,
                "threshold": s.threshold,
                "passed": s.passed,
                "runs": len(s.runs),
            }
            for s in summaries
        ],
        "all_passed": all(s.passed for s in summaries),
    }
    (output_dir / "aggregated-results.json").write_text(json.dumps(aggregated, indent=2))

    return 0 if all(s.passed for s in summaries) else 1


if __name__ == "__main__":
    sys.exit(main())
