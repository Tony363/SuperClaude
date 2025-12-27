"""
Testing utilities for the SuperClaude Command Executor.

Provides functions for running tests, parsing pytest output,
and summarizing test results.
"""

import logging
import os
import re
import subprocess
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .utils import is_truthy, truncate_output

if TYPE_CHECKING:
    from ..parser import ParsedCommand

logger = logging.getLogger(__name__)


def should_run_tests(parsed: "ParsedCommand") -> bool:
    """Determine if automated tests should be executed."""
    keys = ("with-tests", "with_tests", "run-tests", "run_tests")

    for key in keys:
        if is_truthy(parsed.flags.get(key)):
            return True
        if is_truthy(parsed.parameters.get(key)):
            return True

    # Always run when invoking the dedicated test command.
    return parsed.name == "test"


def run_requested_tests(
    parsed: "ParsedCommand",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Execute project tests and capture results."""
    pytest_args: list[str] = ["-q"]
    markers: list[str] = []
    targets: list[str] = []

    parameters = parsed.parameters
    flags = parsed.flags

    coverage_enabled = is_truthy(flags.get("coverage")) or is_truthy(
        parameters.get("coverage")
    )
    if coverage_enabled:
        cov_target = parameters.get("cov")
        if not isinstance(cov_target, str) or not cov_target.strip():
            cov_target = "SuperClaude"
        pytest_args.extend(
            [
                f"--cov={cov_target.strip()}",
                "--cov-report=term-missing",
                "--cov-report=html",
            ]
        )

    type_param = parameters.get("type")
    if isinstance(type_param, str):
        normalized_type = type_param.strip().lower()
        if normalized_type in {"unit", "integration", "e2e"}:
            markers.append(normalized_type)

    if is_truthy(flags.get("e2e")) or is_truthy(parameters.get("e2e")):
        markers.append("e2e")

    def _extend_markers(raw: Any) -> None:
        if raw is None:
            return
        values: Iterable[str]
        if isinstance(raw, str):
            values = [
                token.strip() for token in re.split(r"[\s,]+", raw) if token.strip()
            ]
        elif isinstance(raw, (list, tuple, set)):
            values = [str(item).strip() for item in raw if str(item).strip()]
        else:
            values = [str(raw).strip()]
        for value in values:
            markers.append(value)

    _extend_markers(parameters.get("marker"))
    _extend_markers(parameters.get("markers"))

    def _looks_like_test_target(argument: str) -> bool:
        if not argument or not isinstance(argument, str):
            return False
        if argument.startswith("-"):
            return False
        if "/" in argument or "\\" in argument:
            return True
        if "::" in argument:
            return True
        suffixes = (
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".rs",
            ".go",
            ".java",
            ".kt",
            ".cs",
        )
        return argument.endswith(suffixes)

    for argument in parsed.arguments or []:
        if _looks_like_test_target(str(argument)):
            targets.append(str(argument))
    target_param = parameters.get("target")
    if isinstance(target_param, str) and target_param.strip():
        targets.append(target_param.strip())

    unique_markers: list[str] = []
    seen_markers: set[str] = set()
    for marker in markers:
        normalized = marker.strip()
        if not normalized:
            continue
        if normalized not in seen_markers:
            seen_markers.add(normalized)
            unique_markers.append(normalized)

    command: list[str] = ["pytest", *pytest_args]
    if unique_markers:
        marker_expression = " or ".join(unique_markers)
        command.extend(["-m", marker_expression])
    if targets:
        command.extend(targets)

    env = os.environ.copy()
    env.setdefault("PYENV_DISABLE_REHASH", "1")

    working_dir = str(repo_root or Path.cwd())
    start = datetime.now()
    try:
        result = subprocess.run(
            command,
            cwd=working_dir,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        logger.warning(f"Test runner not available: {exc}")
        return {
            "command": " ".join(command),
            "args": command,
            "passed": False,
            "pass_rate": 0.0,
            "stdout": "",
            "stderr": str(exc),
            "duration_s": 0.0,
            "error": "pytest_not_found",
            "coverage": None,
            "markers": unique_markers,
            "targets": targets,
        }
    except Exception as exc:
        logger.error(f"Unexpected error running tests: {exc}")
        return {
            "command": " ".join(command),
            "args": command,
            "passed": False,
            "pass_rate": 0.0,
            "stdout": "",
            "stderr": str(exc),
            "duration_s": 0.0,
            "error": "test_execution_error",
            "coverage": None,
            "markers": unique_markers,
            "targets": targets,
        }

    duration = (datetime.now() - start).total_seconds()
    passed = result.returncode == 0
    stdout_text = result.stdout or ""
    stderr_text = result.stderr or ""
    metrics = parse_pytest_output(stdout_text, stderr_text)

    pass_rate = metrics.get("pass_rate")
    if pass_rate is None:
        pass_rate = 1.0 if passed else 0.0

    output = {
        "command": " ".join(command),
        "args": command,
        "passed": passed,
        "pass_rate": pass_rate,
        "stdout": truncate_output(stdout_text.strip()),
        "stderr": truncate_output(stderr_text.strip()),
        "duration_s": duration,
        "exit_code": result.returncode,
        "coverage": metrics.get("coverage"),
        "summary": metrics.get("summary"),
        "tests_passed": metrics.get("tests_passed", 0),
        "tests_failed": metrics.get("tests_failed", 0),
        "tests_errored": metrics.get("tests_errored", 0),
        "tests_skipped": metrics.get("tests_skipped", 0),
        "tests_collected": metrics.get("tests_collected"),
        "markers": unique_markers,
        "targets": targets,
    }

    if metrics.get("errors"):
        output["errors"] = metrics["errors"]

    return output


def summarize_test_results(test_results: dict[str, Any]) -> str:
    """Create a concise summary string for executed tests."""
    command = test_results.get("command", "tests")
    status = "pass" if test_results.get("passed") else "fail"
    duration = test_results.get("duration_s")
    duration_part = f" in {duration:.2f}s" if isinstance(duration, (int, float)) else ""
    return f"{command} ({status}{duration_part})"


def parse_pytest_output(stdout: str, stderr: str) -> dict[str, Any]:
    """Extract structured metrics from pytest stdout/stderr."""
    combined = "\n".join(part for part in (stdout, stderr) if part)

    metrics: dict[str, Any] = {
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_errored": 0,
        "tests_skipped": 0,
        "tests_collected": None,
        "pass_rate": None,
        "summary": None,
        "coverage": None,
        "errors": [],
    }

    if not combined:
        return metrics

    for line in combined.splitlines():
        stripped = line.strip()
        if re.match(r"=+\s+.+\s+=+", stripped):
            metrics["summary"] = stripped

    collected_match = re.search(r"collected\s+(\d+)\s+items?", combined)
    if collected_match:
        metrics["tests_collected"] = int(collected_match.group(1))

    for count, label in re.findall(
        r"(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed)", combined
    ):
        value = int(count)
        normalized = label.rstrip("s")
        if normalized == "passed":
            metrics["tests_passed"] += value
        elif normalized == "failed":
            metrics["tests_failed"] += value
        elif normalized == "error":
            metrics["tests_errored"] += value
        elif normalized == "skipped" or normalized == "xfailed":
            metrics["tests_skipped"] += value
        elif normalized == "xpassed":
            metrics["tests_passed"] += value

    executed = (
        metrics["tests_passed"] + metrics["tests_failed"] + metrics["tests_errored"]
    )
    if executed:
        metrics["pass_rate"] = metrics["tests_passed"] / executed

    coverage_match = re.search(r"TOTAL\s+(?:\d+\s+){1,4}(\d+(?:\.\d+)?)%", combined)
    if not coverage_match:
        coverage_match = re.search(
            r"coverage[:\s]+(\d+(?:\.\d+)?)%", combined, re.IGNORECASE
        )
    if coverage_match:
        try:
            metrics["coverage"] = float(coverage_match.group(1)) / 100.0
        except (TypeError, ValueError):
            metrics["coverage"] = None

    failure_entries = re.findall(r"FAILED\s+([^\s]+)\s+-\s+(.+)", combined)
    for test_name, message in failure_entries:
        metrics["errors"].append(f"{test_name} - {message.strip()}")

    return metrics


__all__ = [
    "parse_pytest_output",
    "run_requested_tests",
    "should_run_tests",
    "summarize_test_results",
]
