"""Validation pipeline that enforces layered local quality checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..Monitoring.paths import get_metrics_dir


@dataclass
class ValidationStageResult:
    """Outcome for a single validation stage."""

    name: str
    status: str
    findings: List[str] = field(default_factory=list)
    fatal: bool = False
    degraded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    evidence_path: Optional[Path] = None


@dataclass
class ValidationStage:
    """Descriptor for a pipeline stage."""

    name: str
    handler: Callable[[Dict[str, Any]], ValidationStageResult]
    required: bool = True


class ValidationPipeline:
    """Multi-stage validation that short-circuits on fatal failures."""

    def __init__(self, stages: Optional[List[ValidationStage]] = None) -> None:
        self.stages = stages or self._default_stages()
        self.evidence_dir = get_metrics_dir() / "validation"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def run(self, context: Optional[Dict[str, Any]] = None) -> List[ValidationStageResult]:
        context = context or {}
        results: List[ValidationStageResult] = []
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
    def _default_stages(self) -> List[ValidationStage]:
        return [
            ValidationStage("syntax", self._run_syntax_stage, required=True),
            ValidationStage("security", self._run_security_stage, required=True),
            ValidationStage("style", self._run_style_stage, required=False),
            ValidationStage("tests", self._run_tests_stage, required=True),
            ValidationStage("performance", self._run_performance_stage, required=False),
        ]

    def _run_syntax_stage(self, context: Dict[str, Any]) -> ValidationStageResult:
        report = context.get("syntax_report") or {}
        errors = report.get("errors") or []
        if errors:
            return ValidationStageResult(
                name="syntax",
                status="failed",
                findings=[str(err) for err in errors],
                fatal=True,
            )
        return ValidationStageResult(name="syntax", status="passed", findings=report.get("notes", []))

    def _run_style_stage(self, context: Dict[str, Any]) -> ValidationStageResult:
        violations = context.get("style_violations") or []
        if violations:
            return ValidationStageResult(
                name="style",
                status="needs_attention",
                findings=[str(v) for v in violations],
            )
        return ValidationStageResult(name="style", status="passed")

    def _run_tests_stage(self, context: Dict[str, Any]) -> ValidationStageResult:
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

    def _run_performance_stage(self, context: Dict[str, Any]) -> ValidationStageResult:
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

        return ValidationStageResult(name="performance", status=status, findings=findings)

    def _run_security_stage(self, context: Dict[str, Any]) -> ValidationStageResult:
        findings: List[str] = []
        fatal = False

        scan_issues = self._normalize_security_issues(context.get("security_scan"), source="scan")
        manual_issues = self._normalize_security_issues(context.get("security_findings"), source="manual")
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
    def _normalize_security_issues(self, payload: Any, *, source: str) -> List[Dict[str, Any]]:
        if not payload:
            return []

        if isinstance(payload, list):
            raw = payload
        elif isinstance(payload, dict):
            raw = payload.get("issues") or payload.get("findings") or []
        else:
            return []

        normalized: List[Dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            normalized.append({
                "severity": item.get("severity"),
                "summary": item.get("title") or item.get("message") or item.get("id"),
                "source": item.get("source") or source,
            })
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
