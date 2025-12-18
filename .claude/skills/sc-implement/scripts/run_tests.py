#!/usr/bin/env python3
"""
Test Runner Script for SuperClaude Skills.

Executes project tests and returns structured results.
Ported from SuperClaude/Commands/command_executor.py test execution logic.

Usage:
    python run_tests.py '{"target": "src/", "type": "unit", "coverage": true}'

Input (JSON):
    {
        "target": "src/components",    # Optional: specific target
        "type": "unit",                # unit, integration, e2e, all
        "coverage": true,              # Generate coverage report
        "verbose": false,              # Verbose output
        "watch": false,                # Watch mode (not recommended for scripts)
        "framework": "auto"            # auto, pytest, jest, vitest, mocha
    }

Output (JSON):
    {
        "success": true,
        "framework": "pytest",
        "results": {
            "passed": 42,
            "failed": 0,
            "skipped": 3,
            "total": 45,
            "duration_seconds": 12.5
        },
        "coverage": {
            "line_rate": 85.5,
            "branch_rate": 72.3,
            "uncovered_files": ["src/utils/legacy.py"]
        },
        "errors": [],
        "output_summary": "..."
    }
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def detect_test_framework(project_root: Path) -> str:
    """
    Auto-detect the test framework based on project files.

    Returns:
        Framework name: pytest, jest, vitest, mocha, or unknown
    """
    # Check for Python test frameworks
    if (project_root / "pyproject.toml").exists():
        content = (project_root / "pyproject.toml").read_text()
        if "pytest" in content:
            return "pytest"

    if (project_root / "pytest.ini").exists() or (project_root / "conftest.py").exists():
        return "pytest"

    if (project_root / "setup.py").exists():
        return "pytest"  # Assume pytest for Python projects

    # Check for JavaScript test frameworks
    if (project_root / "package.json").exists():
        content = (project_root / "package.json").read_text()
        if "vitest" in content:
            return "vitest"
        if "jest" in content:
            return "jest"
        if "mocha" in content:
            return "mocha"

    # Check for specific config files
    if (project_root / "vitest.config.ts").exists() or (project_root / "vitest.config.js").exists():
        return "vitest"

    if (project_root / "jest.config.js").exists() or (project_root / "jest.config.ts").exists():
        return "jest"

    return "unknown"


def build_pytest_command(config: dict[str, Any]) -> list[str]:
    """Build pytest command with options."""
    cmd = ["python", "-m", "pytest"]

    target = config.get("target", "")
    if target:
        cmd.append(target)

    if config.get("coverage"):
        cmd.extend(["--cov", "--cov-report=json"])

    if config.get("verbose"):
        cmd.append("-v")

    test_type = config.get("type", "all")
    if test_type == "unit":
        cmd.extend(["-m", "not integration and not e2e"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "e2e":
        cmd.extend(["-m", "e2e"])

    # JSON output for parsing
    cmd.append("--tb=short")

    return cmd


def build_jest_command(config: dict[str, Any]) -> list[str]:
    """Build Jest command with options."""
    cmd = ["npx", "jest"]

    target = config.get("target", "")
    if target:
        cmd.append(target)

    if config.get("coverage"):
        cmd.append("--coverage")

    if config.get("verbose"):
        cmd.append("--verbose")

    # JSON output
    cmd.append("--json")

    return cmd


def build_vitest_command(config: dict[str, Any]) -> list[str]:
    """Build Vitest command with options."""
    cmd = ["npx", "vitest", "run"]

    target = config.get("target", "")
    if target:
        cmd.append(target)

    if config.get("coverage"):
        cmd.append("--coverage")

    # JSON reporter
    cmd.extend(["--reporter", "json"])

    return cmd


def parse_pytest_output(output: str, stderr: str) -> dict[str, Any]:
    """Parse pytest output to extract results."""
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "duration_seconds": 0.0,
    }

    # Parse summary line: "X passed, Y failed, Z skipped in N.NNs"
    summary_pattern = r"(\d+) passed"
    if match := re.search(summary_pattern, output):
        results["passed"] = int(match.group(1))

    failed_pattern = r"(\d+) failed"
    if match := re.search(failed_pattern, output):
        results["failed"] = int(match.group(1))

    skipped_pattern = r"(\d+) skipped"
    if match := re.search(skipped_pattern, output):
        results["skipped"] = int(match.group(1))

    duration_pattern = r"in (\d+\.?\d*)s"
    if match := re.search(duration_pattern, output):
        results["duration_seconds"] = float(match.group(1))

    results["total"] = results["passed"] + results["failed"] + results["skipped"]

    return results


def parse_coverage_json(project_root: Path) -> dict[str, Any] | None:
    """Parse coverage.json if it exists."""
    coverage_file = project_root / "coverage.json"
    if not coverage_file.exists():
        return None

    try:
        with open(coverage_file) as f:
            data = json.load(f)

        totals = data.get("totals", {})
        return {
            "line_rate": totals.get("percent_covered", 0),
            "branch_rate": totals.get("percent_covered_branches", 0),
            "covered_lines": totals.get("covered_lines", 0),
            "total_lines": totals.get("num_statements", 0),
        }
    except Exception:
        return None


def run_tests(config: dict[str, Any]) -> dict[str, Any]:
    """
    Execute tests and return structured results.

    Args:
        config: Test configuration

    Returns:
        Test results with pass/fail counts, coverage, and errors
    """
    project_root = Path(config.get("project_root", ".")).resolve()
    framework = config.get("framework", "auto")

    # Auto-detect framework
    if framework == "auto":
        framework = detect_test_framework(project_root)

    if framework == "unknown":
        return {
            "success": False,
            "framework": "unknown",
            "results": {},
            "coverage": None,
            "errors": ["Could not detect test framework. Specify 'framework' in config."],
            "output_summary": "",
        }

    # Build command based on framework
    if framework == "pytest":
        cmd = build_pytest_command(config)
    elif framework == "jest":
        cmd = build_jest_command(config)
    elif framework == "vitest":
        cmd = build_vitest_command(config)
    else:
        return {
            "success": False,
            "framework": framework,
            "results": {},
            "coverage": None,
            "errors": [f"Unsupported framework: {framework}"],
            "output_summary": "",
        }

    # Execute tests
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        output = result.stdout
        stderr = result.stderr
        success = result.returncode == 0

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "framework": framework,
            "results": {},
            "coverage": None,
            "errors": ["Test execution timed out (5 minute limit)"],
            "output_summary": "",
        }
    except Exception as e:
        return {
            "success": False,
            "framework": framework,
            "results": {},
            "coverage": None,
            "errors": [f"Failed to execute tests: {e}"],
            "output_summary": "",
        }

    # Parse results based on framework
    if framework == "pytest":
        results = parse_pytest_output(output, stderr)
    else:
        # Generic parsing for other frameworks
        results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_seconds": 0.0,
        }

    # Parse coverage if requested
    coverage = None
    if config.get("coverage"):
        coverage = parse_coverage_json(project_root)

    # Collect errors
    errors = []
    if not success and results["failed"] == 0:
        errors.append("Test command failed - check output for details")
    if stderr and "error" in stderr.lower():
        errors.append(stderr[:500])  # Truncate long error messages

    # Truncate output summary
    output_summary = output[:2000] if output else ""

    return {
        "success": success and results["failed"] == 0,
        "framework": framework,
        "results": results,
        "coverage": coverage,
        "errors": errors,
        "output_summary": output_summary,
        "command": " ".join(cmd),
    }


def main():
    """Main entry point for script execution."""
    if len(sys.argv) < 2:
        # Default config if none provided
        config = {"type": "all", "coverage": False}
    else:
        try:
            config = json.loads(sys.argv[1])
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {e}"}))
            sys.exit(1)

    result = run_tests(config)
    print(json.dumps(result, indent=2))

    # Exit with error code if tests failed
    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
