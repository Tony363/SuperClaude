"""Validation pipeline that blends CodeRabbit insights with local checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:  # Optional dependency, avoid hard import cycles in tests
    from ..MCP.coderabbit import CodeRabbitReview
except Exception:  # pragma: no cover - optional runtime import
    CodeRabbitReview = None  # type: ignore

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
        degraded = False
        fatal = False

        review = context.get("coderabbit_review") or context.get("coderabbit")
        review_status = "missing"
        issues = self._extract_coderabbit_issues(review)
        if issues:
            review_status = "available"
            for issue in issues:
                severity = (issue.get("severity") or "").lower()
                summary = issue.get("title") or issue.get("body") or "security issue"
                findings.append(f"CodeRabbit: {summary} ({severity or 'info'})")
                if severity in {"critical", "high"}:
                    fatal = True
        else:
            degraded = True

        local_scan = context.get("security_scan") or {}
        for item in local_scan.get("issues", []):
            summary = item.get("message") or item.get("id") or "security finding"
            severity = (item.get("severity") or "").lower()
            findings.append(f"Local: {summary} ({severity or 'info'})")
            if severity in {"critical", "high"}:
                fatal = True

        status = "passed"
        if fatal:
            status = "failed"
        elif findings:
            status = "needs_attention"

        return ValidationStageResult(
            name="security",
            status=status,
            findings=findings,
            fatal=fatal,
            degraded=degraded,
            metadata={"coderabbit_status": review_status},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _extract_coderabbit_issues(self, review: Any) -> List[Dict[str, Any]]:
        if review is None:
            return []

        if CodeRabbitReview is not None and isinstance(review, CodeRabbitReview):  # type: ignore[arg-type]
            return [
                {
                    "title": getattr(issue, "title", None),
                    "severity": getattr(issue, "severity", None),
                    "tag": getattr(issue, "tag", None),
                }
                for issue in getattr(review, "issues", [])
            ]

        if isinstance(review, dict):
            raw_issues = review.get("issues") or review.get("comments") or []
            cleaned: List[Dict[str, Any]] = []
            for issue in raw_issues:
                if isinstance(issue, dict):
                    cleaned.append(issue)
            return cleaned

        return []

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
