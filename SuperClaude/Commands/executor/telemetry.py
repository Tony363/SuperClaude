"""
Telemetry utilities for the SuperClaude Command Executor.

Provides functions for recording metrics, artifacts, events, and
safe-apply snapshots. These helpers abstract telemetry operations
to simplify the main executor logic.
"""

import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)


# Metric type constants (stub for removed Monitoring module)
class MetricType:
    """Metric type constants for telemetry recording."""

    COUNTER = "counter"
    GAUGE = "gauge"
    TIMER = "timer"


@dataclass
class TelemetryConfig:
    """Configuration for telemetry operations."""

    metrics_dir: Path
    session_id: str
    enabled: bool = True

    @classmethod
    def from_env(cls, session_id: str) -> "TelemetryConfig":
        """Create config from environment defaults."""
        import os

        metrics_dir = Path(
            os.getenv("SUPERCLAUDE_METRICS_DIR", ".superclaude_metrics")
        )
        return cls(metrics_dir=metrics_dir, session_id=session_id)


def build_metric_tags(
    command_name: str,
    status: str,
    execution_mode: str = "standard",
    **extra_tags: str,
) -> Dict[str, str]:
    """Build a consistent tag dictionary for metrics recording."""
    tags = {
        "command": command_name,
        "status": status,
        "mode": execution_mode,
    }
    tags.update(extra_tags)
    return tags


def format_evidence_event(
    command_name: str,
    requires_evidence: bool,
    derived_status: str,
    success: bool,
    static_issues: List[str],
    context_snapshot: Optional[Dict[str, Any]] = None,
    consensus: Optional[Dict[str, Any]] = None,
    quality_score: Optional[float] = None,
    quality_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """Format a structured event payload for requires-evidence telemetry."""
    snapshot = context_snapshot or {}
    execution_mode = str(snapshot.get("execution_mode") or "standard")

    event_payload = {
        "timestamp": datetime.now().isoformat(),
        "command": command_name,
        "requires_evidence": requires_evidence,
        "status": derived_status,
        "success": success,
        "static_issues": static_issues,
        "static_issue_count": len(static_issues),
        "consensus_reached": (
            bool(consensus.get("consensus_reached"))
            if isinstance(consensus, dict)
            else None
        ),
        "quality_score": quality_score,
        "quality_threshold": quality_threshold,
        "consensus_vote_type": snapshot.get("consensus_vote_type"),
        "consensus_quorum": snapshot.get("consensus_quorum_size"),
        "plan_only": derived_status == "plan-only",
        "execution_mode": execution_mode,
        "fast_codex": snapshot.get("fast_codex"),
        "fast_codex_cli": snapshot.get("fast_codex_cli"),
    }
    return event_payload


def format_fast_codex_event(
    phase: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Format a structured fast-codex event entry."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "phase": phase,
        "message": message,
    }
    if details:
        entry["details"] = details
    return entry


def format_plan_only_event(
    command_name: str,
    arguments: List[str],
    flags: Dict[str, Any],
    session_id: str,
    requires_evidence: bool,
    derived_status: str,
    missing_evidence: bool = False,
    plan_only_agents: Optional[List[str]] = None,
    guidance: Optional[List[str]] = None,
    safe_apply_requested: bool = False,
    change_plan: Optional[List[Dict[str, Any]]] = None,
    consensus: Optional[Dict[str, Any]] = None,
    errors: Optional[List[str]] = None,
    retrieval_hits: Optional[int] = None,
    safe_apply_snapshot: Optional[Dict[str, Any]] = None,
    safe_apply_directory: Optional[str] = None,
) -> Dict[str, Any]:
    """Format a plan-only event for telemetry."""
    event: Dict[str, Any] = {
        "command": command_name,
        "arguments": list(arguments),
        "flags": sorted(flags.keys()),
        "requires_evidence": requires_evidence,
        "status": derived_status,
        "session_id": session_id,
        "missing_evidence": missing_evidence,
        "plan_only_agents": list(plan_only_agents or []),
        "guidance": list(guidance or []),
        "safe_apply_requested": safe_apply_requested,
    }

    if change_plan:
        summary: List[Dict[str, Any]] = []
        for entry in change_plan[:10]:
            if not isinstance(entry, dict):
                continue
            summary.append(
                {
                    "path": entry.get("path"),
                    "intent": entry.get("intent"),
                    "description": (
                        entry.get("description")
                        or entry.get("summary")
                        or entry.get("title")
                    ),
                }
            )
        event["change_plan"] = summary
        event["change_plan_count"] = len(change_plan)
    else:
        event["change_plan_count"] = 0

    if consensus:
        event["consensus"] = {
            "consensus_reached": consensus.get("consensus_reached"),
            "models": consensus.get("models"),
            "decision": consensus.get("final_decision"),
        }
    else:
        event["consensus"] = None

    if errors:
        event["errors"] = errors[:5]

    if retrieval_hits is not None:
        event["retrieval_hits"] = retrieval_hits

    if safe_apply_snapshot:
        event["safe_apply_snapshot"] = safe_apply_snapshot
    if safe_apply_directory:
        event["safe_apply_directory"] = safe_apply_directory

    return event


def write_safe_apply_snapshot(
    session_id: str,
    stubs: Sequence[Dict[str, Any]],
    base_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Write stub files to a safe-apply snapshot directory.

    Args:
        session_id: Unique session identifier for organizing snapshots.
        stubs: List of stub dictionaries with 'path' and 'content' keys.
        base_dir: Optional base directory; defaults to temp directory.

    Returns:
        Manifest dictionary with 'directory' and 'files' keys, or None if
        no files were created.
    """
    if base_dir is None:
        metrics_dir = Path(tempfile.gettempdir()) / "superclaude_metrics"
        base_dir = metrics_dir / "safe_apply" / session_id

    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    snapshot_dir = base_dir / timestamp

    saved_files: List[str] = []
    created_any = False

    for entry in stubs:
        raw_path = entry.get("path")
        content = entry.get("content", "")
        if not raw_path or not isinstance(content, str):
            continue

        raw_string = str(raw_path).strip()
        if not raw_string:
            continue

        rel_parts = [
            part for part in Path(raw_string).parts if part not in ("", ".")
        ]
        if not rel_parts:
            continue
        if rel_parts[0] == ".." or any(part == ".." for part in rel_parts):
            continue

        if raw_string.startswith(("/", "\\")) and len(rel_parts) > 1:
            rel_parts = rel_parts[1:]

        rel_path = Path(*rel_parts)
        target = snapshot_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            target.write_text(content, encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to write safe-apply stub %s: %s", target, exc)
            continue

        created_any = True
        saved_files.append(str(target.relative_to(snapshot_dir)))

    if not created_any:
        return None

    manifest = {
        "directory": str(snapshot_dir),
        "files": saved_files,
    }

    prune_safe_apply_snapshots(base_dir)

    return manifest


def prune_safe_apply_snapshots(session_root: Path, keep: int = 3) -> None:
    """Remove old safe-apply snapshots, keeping only the most recent.

    Args:
        session_root: Directory containing timestamp-named snapshot dirs.
        keep: Number of recent snapshots to retain.
    """
    try:
        candidates = [path for path in session_root.iterdir() if path.is_dir()]
    except FileNotFoundError:
        return

    candidates.sort(key=lambda path: path.name, reverse=True)
    for obsolete in candidates[keep:]:
        try:
            shutil.rmtree(obsolete)
        except Exception as exc:
            logger.debug("Safe-apply cleanup skipped for %s: %s", obsolete, exc)


def truncate_fast_codex_stream(payload: Optional[str], limit: int = 600) -> str:
    """Return a concise preview of Codex CLI stdout/stderr for display."""
    if not payload:
        return ""
    snippet = str(payload).strip()
    if len(snippet) <= limit:
        return snippet
    head = snippet[: limit // 2].rstrip()
    tail = snippet[-limit // 2 :].lstrip()
    return f"{head} … {tail}"


def format_test_artifact_summary(test_results: Dict[str, Any]) -> List[str]:
    """Format test results into artifact summary lines."""
    if not test_results:
        return []

    status = "pass" if test_results.get("passed") else "fail"
    summary = [
        f"Test command: {test_results.get('command', 'pytest')}",
        f"Status: {status.upper()}",
    ]
    duration = test_results.get("duration_s")
    if isinstance(duration, (int, float)):
        summary.append(f"Duration: {duration:.2f}s")
    stdout = test_results.get("stdout")
    if stdout:
        summary.append("\n## Stdout\n" + stdout)
    stderr = test_results.get("stderr")
    if stderr:
        summary.append("\n## Stderr\n" + stderr)

    return summary


def format_quality_artifact_summary(
    overall_score: float,
    threshold: float,
    passed: bool,
    metrics: List[Dict[str, Any]],
    improvements_needed: Optional[List[str]] = None,
) -> List[str]:
    """Format quality assessment into artifact summary lines."""
    lines = [
        f"Overall: {overall_score:.1f} (threshold {threshold:.1f})",
        f"Passed: {'yes' if passed else 'no'}",
        "",
        "## Dimensions",
    ]
    for metric in metrics:
        dimension = metric.get("dimension", "unknown")
        score = metric.get("score", 0.0)
        issues_count = len(metric.get("issues", []))
        lines.append(f"- {dimension}: {score:.1f} — issues: {issues_count}")

    if improvements_needed:
        lines.append("")
        lines.append("## Improvements Needed")
        lines.extend(f"- {item}" for item in improvements_needed)

    return lines


def summarize_rube_context(
    command_name: str,
    output: Any,
    applied_changes: Optional[List[Any]] = None,
    status: str = "unknown",
) -> str:
    """Generate a short summary for Rube automation payloads."""
    if isinstance(output, dict):
        summary = (
            output.get("summary")
            or output.get("description")
            or output.get("title")
        )
        if isinstance(summary, str) and summary.strip():
            return summary.strip()[:400]

    if isinstance(applied_changes, list) and applied_changes:
        return f"{command_name} touched {len(applied_changes)} files."

    return f"{command_name} executed with status {status}"


__all__ = [
    "MetricType",
    "TelemetryConfig",
    "build_metric_tags",
    "format_evidence_event",
    "format_fast_codex_event",
    "format_plan_only_event",
    "format_quality_artifact_summary",
    "format_test_artifact_summary",
    "prune_safe_apply_snapshots",
    "summarize_rube_context",
    "truncate_fast_codex_stream",
    "write_safe_apply_snapshot",
]
