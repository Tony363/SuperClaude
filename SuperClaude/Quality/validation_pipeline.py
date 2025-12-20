"""Validation pipeline that enforces layered local quality checks with real tool integration."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_validation_dir() -> Path:
    """Get validation evidence directory (uses temp dir since Monitoring removed)."""
    base = Path(tempfile.gettempdir()) / "superclaude_validation"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass
class ValidationStageResult:
    """Outcome for a single validation stage."""

    name: str
    status: str
    findings: list[str] = field(default_factory=list)
    fatal: bool = False
    degraded: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_path: Path | None = None


@dataclass
class ValidationStage:
    """Descriptor for a pipeline stage."""

    name: str
    handler: Callable[[dict[str, Any]], ValidationStageResult]
    required: bool = True


class ToolRunner:
    """
    Real tool integration for validation stages.

    Runs actual CLI tools (pytest, ruff, mypy, bandit) and parses their output.
    """

    @staticmethod
    def run_command(
        cmd: list[str],
        cwd: Path | None = None,
        timeout: int = 300,
    ) -> tuple[int, str, str]:
        """
        Run a shell command and capture output.

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return -2, "", f"Command not found: {cmd[0]}"
        except Exception as e:
            return -3, "", str(e)

    @classmethod
    def run_pytest(
        cls,
        target: Path | None = None,
        cwd: Path | None = None,
        markers: str | None = None,
        coverage: bool = False,
    ) -> dict[str, Any]:
        """
        Run pytest and parse results.

        Returns dict with:
            - passed: int
            - failed: int
            - errors: int
            - skipped: int
            - coverage: float (if coverage enabled)
            - output: str
            - success: bool
        """
        cmd = ["python", "-m", "pytest", "-v", "--tb=short"]

        if markers:
            cmd.extend(["-m", markers])

        if coverage:
            cmd.extend(["--cov", "--cov-report=term-missing"])

        if target:
            cmd.append(str(target))

        returncode, stdout, stderr = cls.run_command(cmd, cwd=cwd)

        # Parse pytest output
        result = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "coverage": 0.0,
            "output": stdout + stderr,
            "success": returncode == 0,
            "returncode": returncode,
        }

        # Extract counts from summary line (e.g., "5 passed, 2 failed, 1 error")
        summary_match = re.search(
            r"(\d+)\s+passed.*?(\d+)\s+failed|(\d+)\s+passed",
            stdout,
            re.IGNORECASE,
        )
        if summary_match:
            if summary_match.group(1):
                result["passed"] = int(summary_match.group(1))
            if summary_match.group(2):
                result["failed"] = int(summary_match.group(2))
            if summary_match.group(3):
                result["passed"] = int(summary_match.group(3))

        # Extract coverage percentage
        coverage_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", stdout)
        if coverage_match:
            result["coverage"] = float(coverage_match.group(1))

        return result

    @classmethod
    def run_ruff_check(
        cls,
        target: Path | None = None,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        """
        Run ruff linter and parse results.

        Returns dict with:
            - issues: list of issue dicts
            - count: int
            - success: bool
        """
        cmd = ["ruff", "check", "--output-format=json"]

        if target:
            cmd.append(str(target))
        else:
            cmd.append(".")

        returncode, stdout, stderr = cls.run_command(cmd, cwd=cwd)

        result = {
            "issues": [],
            "count": 0,
            "success": returncode == 0,
            "output": stderr,
        }

        # Parse JSON output
        if stdout.strip():
            try:
                issues = json.loads(stdout)
                result["issues"] = [
                    {
                        "file": issue.get("filename", ""),
                        "line": issue.get("location", {}).get("row", 0),
                        "code": issue.get("code", ""),
                        "message": issue.get("message", ""),
                    }
                    for issue in issues
                ]
                result["count"] = len(issues)
            except json.JSONDecodeError:
                result["output"] = stdout

        return result

    @classmethod
    def run_mypy(
        cls,
        target: Path | None = None,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        """
        Run mypy type checker and parse results.

        Returns dict with:
            - errors: list of error dicts
            - count: int
            - success: bool
        """
        cmd = ["mypy", "--ignore-missing-imports"]

        if target:
            cmd.append(str(target))
        else:
            cmd.append(".")

        returncode, stdout, stderr = cls.run_command(cmd, cwd=cwd)

        result = {
            "errors": [],
            "count": 0,
            "success": returncode == 0,
            "output": stdout + stderr,
        }

        # Parse mypy output (format: file:line: error: message)
        error_pattern = re.compile(
            r"^(.+):(\d+):\s*(error|warning):\s*(.+)$", re.MULTILINE
        )
        for match in error_pattern.finditer(stdout):
            result["errors"].append(
                {
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "severity": match.group(3),
                    "message": match.group(4),
                }
            )

        result["count"] = len(result["errors"])
        return result

    @classmethod
    def run_bandit(
        cls,
        target: Path | None = None,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        """
        Run bandit security scanner and parse results.

        Returns dict with:
            - issues: list of security issue dicts
            - critical: int
            - high: int
            - medium: int
            - low: int
            - success: bool
        """
        cmd = ["bandit", "-r", "-f", "json"]

        if target:
            cmd.append(str(target))
        else:
            cmd.append(".")

        returncode, stdout, stderr = cls.run_command(cmd, cwd=cwd)

        result = {
            "issues": [],
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "success": True,  # bandit returns non-zero if issues found
            "output": stderr,
        }

        if stdout.strip():
            try:
                data = json.loads(stdout)
                issues = data.get("results", [])

                for issue in issues:
                    severity = issue.get("issue_severity", "LOW").upper()
                    result["issues"].append(
                        {
                            "file": issue.get("filename", ""),
                            "line": issue.get("line_number", 0),
                            "severity": severity,
                            "confidence": issue.get("issue_confidence", ""),
                            "message": issue.get("issue_text", ""),
                            "test_id": issue.get("test_id", ""),
                        }
                    )

                    if severity == "CRITICAL":
                        result["critical"] += 1
                    elif severity == "HIGH":
                        result["high"] += 1
                    elif severity == "MEDIUM":
                        result["medium"] += 1
                    else:
                        result["low"] += 1

                # Consider critical/high issues as failures
                if result["critical"] > 0 or result["high"] > 0:
                    result["success"] = False

            except json.JSONDecodeError:
                result["output"] = stdout

        return result

    @classmethod
    def check_syntax(
        cls,
        files: list[Path] | None = None,
        cwd: Path | None = None,
    ) -> dict[str, Any]:
        """
        Check Python syntax using py_compile.

        Returns dict with:
            - errors: list of syntax error dicts
            - success: bool
        """
        result = {
            "errors": [],
            "success": True,
        }

        if not files:
            # Find all Python files
            search_dir = cwd or Path.cwd()
            files = list(search_dir.rglob("*.py"))

        for filepath in files:
            try:
                with open(filepath, encoding="utf-8") as f:
                    source = f.read()
                compile(source, str(filepath), "exec")
            except SyntaxError as e:
                result["errors"].append(
                    {
                        "file": str(filepath),
                        "line": e.lineno or 0,
                        "message": str(e.msg),
                        "offset": e.offset or 0,
                    }
                )
                result["success"] = False
            except Exception as e:
                result["errors"].append(
                    {
                        "file": str(filepath),
                        "line": 0,
                        "message": str(e),
                    }
                )

        return result


class ValidationPipeline:
    """Multi-stage validation that short-circuits on fatal failures."""

    def __init__(
        self,
        stages: list[ValidationStage] | None = None,
        use_real_tools: bool = True,
        target_path: Path | None = None,
    ) -> None:
        """
        Initialize validation pipeline.

        Args:
            stages: Custom validation stages (uses defaults if None)
            use_real_tools: If True, run actual CLI tools; if False, use context-provided data
            target_path: Path to validate (for real tool execution)
        """
        self.stages = stages or self._default_stages()
        self.evidence_dir = _get_validation_dir()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.use_real_tools = use_real_tools
        self.target_path = target_path
        self.tool_runner = ToolRunner()

    def run(self, context: dict[str, Any] | None = None) -> list[ValidationStageResult]:
        context = context or {}

        # Add target path to context if not present
        if self.target_path and "target_path" not in context:
            context["target_path"] = self.target_path

        # Add tool execution mode
        context["use_real_tools"] = self.use_real_tools

        results: list[ValidationStageResult] = []
        halted = False

        for stage in self.stages:
            if halted:
                result = ValidationStageResult(
                    name=stage.name,
                    status="skipped",
                    findings=["short-circuited after fatal stage"],
                )
            else:
                result = stage.handler(context)

            self._write_evidence(result)
            results.append(result)

            if result.fatal and result.status == "failed":
                halted = True

        return results

    # ------------------------------------------------------------------
    # Stage handlers
    # ------------------------------------------------------------------
    def _default_stages(self) -> list[ValidationStage]:
        return [
            ValidationStage("syntax", self._run_syntax_stage, required=True),
            ValidationStage("security", self._run_security_stage, required=True),
            ValidationStage("style", self._run_style_stage, required=False),
            ValidationStage("tests", self._run_tests_stage, required=True),
            ValidationStage("type_check", self._run_type_check_stage, required=False),
            ValidationStage("performance", self._run_performance_stage, required=False),
        ]

    def _run_syntax_stage(self, context: dict[str, Any]) -> ValidationStageResult:
        """Run syntax validation using real tools or context data."""

        if context.get("use_real_tools"):
            target = context.get("target_path")
            files = None
            if target:
                target = Path(target)
                if target.is_file():
                    files = [target]

            result = ToolRunner.check_syntax(
                files=files, cwd=target if target and target.is_dir() else None
            )

            if result["errors"]:
                return ValidationStageResult(
                    name="syntax",
                    status="failed",
                    findings=[
                        f"{e['file']}:{e['line']}: {e['message']}"
                        for e in result["errors"]
                    ],
                    fatal=True,
                    metadata={
                        "tool": "py_compile",
                        "error_count": len(result["errors"]),
                    },
                )
            return ValidationStageResult(
                name="syntax",
                status="passed",
                findings=["All files have valid Python syntax"],
                metadata={"tool": "py_compile"},
            )

        # Fallback to context-provided data
        report = context.get("syntax_report") or {}
        errors = report.get("errors") or []
        if errors:
            return ValidationStageResult(
                name="syntax",
                status="failed",
                findings=[str(err) for err in errors],
                fatal=True,
            )
        return ValidationStageResult(
            name="syntax", status="passed", findings=report.get("notes", [])
        )

    def _run_style_stage(self, context: dict[str, Any]) -> ValidationStageResult:
        """Run style/lint validation using ruff or context data."""

        if context.get("use_real_tools"):
            target = context.get("target_path")
            result = ToolRunner.run_ruff_check(
                target=Path(target) if target else None,
                cwd=Path(target) if target and Path(target).is_dir() else None,
            )

            if result["count"] > 0:
                findings = [
                    f"{issue['file']}:{issue['line']}: [{issue['code']}] {issue['message']}"
                    for issue in result["issues"][:10]  # Limit to first 10
                ]
                if result["count"] > 10:
                    findings.append(f"... and {result['count'] - 10} more issues")

                return ValidationStageResult(
                    name="style",
                    status="needs_attention",
                    findings=findings,
                    metadata={"tool": "ruff", "issue_count": result["count"]},
                )

            return ValidationStageResult(
                name="style",
                status="passed",
                findings=["No linting issues found"],
                metadata={"tool": "ruff"},
            )

        # Fallback to context-provided data
        violations = context.get("style_violations") or []
        if violations:
            return ValidationStageResult(
                name="style",
                status="needs_attention",
                findings=[str(v) for v in violations],
            )
        return ValidationStageResult(name="style", status="passed")

    def _run_tests_stage(self, context: dict[str, Any]) -> ValidationStageResult:
        """Run test validation using pytest or context data."""

        if context.get("use_real_tools"):
            target = context.get("target_path")
            cwd = Path(target) if target and Path(target).is_dir() else None

            # Look for tests directory
            test_dir = None
            if cwd:
                for candidate in ["tests", "test", "Tests"]:
                    if (cwd / candidate).is_dir():
                        test_dir = cwd / candidate
                        break

            result = ToolRunner.run_pytest(
                target=test_dir,
                cwd=cwd,
                markers="not slow",  # Skip slow tests by default
                coverage=True,
            )

            if result["returncode"] == -2:
                # pytest not installed
                return ValidationStageResult(
                    name="tests",
                    status="degraded",
                    degraded=True,
                    findings=["pytest not installed - cannot run tests"],
                    metadata={"tool": "pytest", "available": False},
                )

            total = result["passed"] + result["failed"] + result["errors"]

            if result["failed"] > 0 or result["errors"] > 0:
                return ValidationStageResult(
                    name="tests",
                    status="failed",
                    fatal=True,
                    findings=[
                        f"Tests: {result['passed']} passed, {result['failed']} failed, {result['errors']} errors",
                        f"Coverage: {result['coverage']}%",
                    ],
                    metadata={
                        "tool": "pytest",
                        "passed": result["passed"],
                        "failed": result["failed"],
                        "errors": result["errors"],
                        "coverage": result["coverage"],
                    },
                )

            if total == 0:
                return ValidationStageResult(
                    name="tests",
                    status="degraded",
                    degraded=True,
                    findings=["No tests found or executed"],
                    metadata={"tool": "pytest", "test_count": 0},
                )

            return ValidationStageResult(
                name="tests",
                status="passed",
                findings=[
                    f"All {result['passed']} tests passed",
                    f"Coverage: {result['coverage']}%",
                ],
                metadata={
                    "tool": "pytest",
                    "passed": result["passed"],
                    "coverage": result["coverage"],
                },
            )

        # Fallback to context-provided data
        results = context.get("test_results") or {}
        if not results:
            return ValidationStageResult(
                name="tests",
                status="degraded",
                degraded=True,
                findings=["No test results supplied"],
            )

        failed = results.get("failed", 0)
        if failed:
            return ValidationStageResult(
                name="tests",
                status="failed",
                fatal=True,
                findings=[f"{failed} test(s) failed"],
            )
        return ValidationStageResult(name="tests", status="passed")

    def _run_type_check_stage(self, context: dict[str, Any]) -> ValidationStageResult:
        """Run type checking using mypy."""

        if context.get("use_real_tools"):
            target = context.get("target_path")
            result = ToolRunner.run_mypy(
                target=Path(target) if target else None,
                cwd=Path(target) if target and Path(target).is_dir() else None,
            )

            if result["returncode"] == -2:
                return ValidationStageResult(
                    name="type_check",
                    status="degraded",
                    degraded=True,
                    findings=["mypy not installed - cannot run type checking"],
                    metadata={"tool": "mypy", "available": False},
                )

            if result["count"] > 0:
                error_findings = [
                    f"{e['file']}:{e['line']}: {e['message']}"
                    for e in result["errors"][:10]
                ]
                if result["count"] > 10:
                    error_findings.append(f"... and {result['count'] - 10} more errors")

                return ValidationStageResult(
                    name="type_check",
                    status="needs_attention",
                    findings=error_findings,
                    metadata={"tool": "mypy", "error_count": result["count"]},
                )

            return ValidationStageResult(
                name="type_check",
                status="passed",
                findings=["No type errors found"],
                metadata={"tool": "mypy"},
            )

        # Fallback: no type check data in context
        return ValidationStageResult(
            name="type_check",
            status="degraded",
            degraded=True,
            findings=["No type check data available"],
        )

    def _run_performance_stage(self, context: dict[str, Any]) -> ValidationStageResult:
        metrics = context.get("performance_metrics") or {}
        findings = []
        status = "passed"
        latency = metrics.get("latency_ms")
        if isinstance(latency, (int, float)) and latency > 1500:
            findings.append(f"Latency high: {latency}ms")
            status = "needs_attention"
        memory = metrics.get("memory_mb")
        if isinstance(memory, (int, float)) and memory > 1024:
            findings.append(f"Memory high: {memory}MB")
            status = "needs_attention"

        return ValidationStageResult(
            name="performance", status=status, findings=findings
        )

    def _run_security_stage(self, context: dict[str, Any]) -> ValidationStageResult:
        """Run security scanning using bandit or context data."""

        if context.get("use_real_tools"):
            target = context.get("target_path")
            result = ToolRunner.run_bandit(
                target=Path(target) if target else None,
                cwd=Path(target) if target and Path(target).is_dir() else None,
            )

            if "Command not found" in result.get("output", ""):
                return ValidationStageResult(
                    name="security",
                    status="degraded",
                    degraded=True,
                    findings=["bandit not installed - cannot run security scan"],
                    metadata={"tool": "bandit", "available": False},
                )

            if result["critical"] > 0 or result["high"] > 0:
                findings = [
                    f"CRITICAL: {result['critical']}, HIGH: {result['high']}, "
                    f"MEDIUM: {result['medium']}, LOW: {result['low']}"
                ]
                for issue in result["issues"][:5]:
                    if issue["severity"] in ("CRITICAL", "HIGH"):
                        findings.append(
                            f"{issue['file']}:{issue['line']}: [{issue['severity']}] {issue['message']}"
                        )

                return ValidationStageResult(
                    name="security",
                    status="failed",
                    fatal=True,
                    findings=findings,
                    metadata={
                        "tool": "bandit",
                        "critical": result["critical"],
                        "high": result["high"],
                        "medium": result["medium"],
                        "low": result["low"],
                    },
                )

            if result["medium"] > 0 or result["low"] > 0:
                return ValidationStageResult(
                    name="security",
                    status="needs_attention",
                    findings=[
                        f"Found {result['medium']} medium and {result['low']} low severity issues"
                    ],
                    metadata={
                        "tool": "bandit",
                        "medium": result["medium"],
                        "low": result["low"],
                    },
                )

            return ValidationStageResult(
                name="security",
                status="passed",
                findings=["No security issues found"],
                metadata={"tool": "bandit"},
            )

        # Fallback to context-provided data
        findings: list[str] = []
        fatal = False

        scan_issues = self._normalize_security_issues(
            context.get("security_scan"), source="scan"
        )
        manual_issues = self._normalize_security_issues(
            context.get("security_findings"), source="manual"
        )
        all_issues = scan_issues + manual_issues

        if not all_issues:
            return ValidationStageResult(
                name="security",
                status="degraded",
                findings=["No security scan data supplied"],
                degraded=True,
                metadata={"scanner": "missing"},
            )

        for issue in all_issues:
            severity = (issue.get("severity") or "").lower()
            summary = issue.get("summary") or issue.get("message") or "security finding"
            source = issue.get("source") or "scan"
            findings.append(f"{source}: {summary} ({severity or 'info'})")
            if severity in {"critical", "high"}:
                fatal = True

        status = "failed" if fatal else "needs_attention"

        return ValidationStageResult(
            name="security",
            status=status,
            findings=findings,
            fatal=fatal,
            degraded=False,
            metadata={
                "scanner": "local",
                "issue_count": len(all_issues),
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _normalize_security_issues(
        self, payload: Any, *, source: str
    ) -> list[dict[str, Any]]:
        if not payload:
            return []

        if isinstance(payload, list):
            raw = payload
        elif isinstance(payload, dict):
            raw = payload.get("issues") or payload.get("findings") or []
        else:
            return []

        normalized: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "severity": item.get("severity"),
                    "summary": item.get("title")
                    or item.get("message")
                    or item.get("id"),
                    "source": item.get("source") or source,
                }
            )
        return normalized

    def _write_evidence(self, result: ValidationStageResult) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "name": result.name,
            "status": result.status,
            "fatal": result.fatal,
            "degraded": result.degraded,
            "findings": result.findings,
            "metadata": result.metadata,
        }
        path = self.evidence_dir / f"{result.name}.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        result.evidence_path = path
