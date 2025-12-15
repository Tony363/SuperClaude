"""
Agent usage telemetry helpers for SuperClaude.

NOTE: Monitoring module removed - this is a no-op stub that maintains API compatibility.
"""

from __future__ import annotations

from pathlib import Path


def record_load(agent: str, source: str | None = None) -> None:
    """Record that an agent was loaded (no-op)."""
    pass


def record_execution(agent: str, source: str | None = None) -> None:
    """Record that an agent executed (no-op)."""
    pass


def record_plan_only(agent: str, source: str | None = None) -> None:
    """Record that an agent returned plan-only guidance (no-op)."""
    pass


def get_usage_snapshot() -> dict[str, dict[str, int]]:
    """Return empty usage snapshot."""
    return {}


def classify_agents(
    agent_names: dict[str, dict[str, str]],
) -> dict[str, dict[str, int]]:
    """Build empty usage buckets."""
    return {"active": {}, "observed": {}, "planned": {}}


def write_markdown_report(
    registry_summary: dict[str, dict[str, str]],
    output_path: Path | None = None,
) -> Path:
    """No-op - returns a placeholder path."""
    return Path("/dev/null")


def reset_usage_stats(for_tests: bool = False) -> None:
    """No-op reset."""
    pass


__all__ = [
    "classify_agents",
    "get_usage_snapshot",
    "record_execution",
    "record_load",
    "record_plan_only",
    "reset_usage_stats",
    "write_markdown_report",
]
