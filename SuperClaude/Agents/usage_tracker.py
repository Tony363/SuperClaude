"""
Agent usage telemetry helpers for SuperClaude.

Provides lightweight, structured telemetry for agent operations including:
- Agent load/execution tracking
- Usage statistics and snapshots
- Basic reporting capabilities

This is a minimal telemetry implementation focused on observability
without heavy external dependencies.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Thread-safe storage for usage data
_lock = threading.Lock()
_usage_data: dict[str, dict[str, Any]] = defaultdict(
    lambda: {"loads": 0, "executions": 0, "plan_only": 0, "last_used": None}
)

# Logger for telemetry events
_logger = logging.getLogger("superclaude.telemetry")


def record_load(agent: str, source: str | None = None) -> None:
    """
    Record that an agent was loaded.

    Args:
        agent: Name of the agent that was loaded
        source: Optional source context (e.g., 'registry', 'direct')
    """
    with _lock:
        _usage_data[agent]["loads"] += 1
        _usage_data[agent]["last_used"] = datetime.now().isoformat()
        if source:
            _usage_data[agent].setdefault("sources", [])
            if source not in _usage_data[agent]["sources"]:
                _usage_data[agent]["sources"].append(source)

    _logger.debug(f"Agent loaded: {agent} (source={source})")


def record_execution(agent: str, source: str | None = None) -> None:
    """
    Record that an agent executed.

    Args:
        agent: Name of the agent that executed
        source: Optional source context
    """
    with _lock:
        _usage_data[agent]["executions"] += 1
        _usage_data[agent]["last_used"] = datetime.now().isoformat()

    _logger.debug(f"Agent executed: {agent} (source={source})")


def record_plan_only(agent: str, source: str | None = None) -> None:
    """
    Record that an agent returned plan-only guidance (no execution).

    Args:
        agent: Name of the agent
        source: Optional source context
    """
    with _lock:
        _usage_data[agent]["plan_only"] += 1
        _usage_data[agent]["last_used"] = datetime.now().isoformat()

    _logger.debug(f"Agent plan-only: {agent} (source={source})")


def get_usage_snapshot() -> dict[str, dict[str, int]]:
    """
    Return current usage snapshot.

    Returns:
        Dictionary mapping agent names to their usage statistics
    """
    with _lock:
        # Return a copy to avoid external mutation
        return {
            agent: {
                "loads": data["loads"],
                "executions": data["executions"],
                "plan_only": data["plan_only"],
                "last_used": data["last_used"],
            }
            for agent, data in _usage_data.items()
        }


def classify_agents(
    agent_names: dict[str, dict[str, str]],
) -> dict[str, dict[str, int]]:
    """
    Classify agents by usage patterns.

    Args:
        agent_names: Registry of agent names and metadata

    Returns:
        Dictionary with 'active', 'observed', 'planned' buckets
    """
    snapshot = get_usage_snapshot()

    active = {}  # Agents with executions
    observed = {}  # Agents loaded but not executed
    planned = {}  # Agents with plan-only usage

    for agent, stats in snapshot.items():
        if stats["executions"] > 0:
            active[agent] = stats["executions"]
        elif stats["loads"] > 0:
            observed[agent] = stats["loads"]
        elif stats["plan_only"] > 0:
            planned[agent] = stats["plan_only"]

    return {"active": active, "observed": observed, "planned": planned}


def get_top_agents(limit: int = 10) -> list[tuple[str, int]]:
    """
    Get the most frequently executed agents.

    Args:
        limit: Maximum number of agents to return

    Returns:
        List of (agent_name, execution_count) tuples sorted by count
    """
    snapshot = get_usage_snapshot()
    sorted_agents = sorted(
        [(agent, stats["executions"]) for agent, stats in snapshot.items()],
        key=lambda x: x[1],
        reverse=True,
    )
    return sorted_agents[:limit]


def write_markdown_report(
    registry_summary: dict[str, dict[str, str]],
    output_path: Path | None = None,
) -> Path:
    """
    Write a markdown usage report.

    Args:
        registry_summary: Agent registry summary data
        output_path: Output file path (defaults to .superclaude_metrics/usage_report.md)

    Returns:
        Path to the generated report
    """
    if output_path is None:
        metrics_dir = Path.home() / ".superclaude_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        output_path = metrics_dir / "usage_report.md"

    snapshot = get_usage_snapshot()
    classification = classify_agents(registry_summary)
    top_agents = get_top_agents(10)

    lines = [
        "# SuperClaude Agent Usage Report",
        f"\n_Generated: {datetime.now().isoformat()}_\n",
        "## Summary Statistics\n",
        f"- **Total agents tracked:** {len(snapshot)}",
        f"- **Active agents (executed):** {len(classification['active'])}",
        f"- **Observed agents (loaded only):** {len(classification['observed'])}",
        f"- **Plan-only agents:** {len(classification['planned'])}",
        "\n## Top 10 Most Executed Agents\n",
        "| Agent | Executions |",
        "|-------|------------|",
    ]

    for agent, count in top_agents:
        lines.append(f"| {agent} | {count} |")

    if snapshot:
        lines.extend(
            [
                "\n## Detailed Usage\n",
                "| Agent | Loads | Executions | Plan-Only | Last Used |",
                "|-------|-------|------------|-----------|-----------|",
            ]
        )
        for agent, stats in sorted(snapshot.items()):
            last_used = stats["last_used"] or "never"
            if last_used != "never":
                # Truncate to date only for readability
                last_used = last_used.split("T")[0]
            lines.append(
                f"| {agent} | {stats['loads']} | {stats['executions']} | {stats['plan_only']} | {last_used} |"
            )

    output_path.write_text("\n".join(lines))
    _logger.info(f"Usage report written to {output_path}")
    return output_path


def export_json(output_path: Path | None = None) -> Path:
    """
    Export usage data as JSON.

    Args:
        output_path: Output file path

    Returns:
        Path to the exported file
    """
    if output_path is None:
        metrics_dir = Path.home() / ".superclaude_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        output_path = metrics_dir / "usage_data.json"

    snapshot = get_usage_snapshot()
    export_data = {
        "generated_at": datetime.now().isoformat(),
        "agents": snapshot,
        "summary": {
            "total_agents": len(snapshot),
            "total_executions": sum(s["executions"] for s in snapshot.values()),
            "total_loads": sum(s["loads"] for s in snapshot.values()),
        },
    }

    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2)

    _logger.info(f"Usage data exported to {output_path}")
    return output_path


def reset_usage_stats(for_tests: bool = False) -> None:
    """
    Reset all usage statistics.

    Args:
        for_tests: If True, suppresses logging (for test isolation)
    """
    with _lock:
        _usage_data.clear()

    if not for_tests:
        _logger.info("Usage statistics reset")


__all__ = [
    "classify_agents",
    "export_json",
    "get_top_agents",
    "get_usage_snapshot",
    "record_execution",
    "record_load",
    "record_plan_only",
    "reset_usage_stats",
    "write_markdown_report",
]
