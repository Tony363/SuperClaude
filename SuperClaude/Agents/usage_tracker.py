"""
Agent usage telemetry helpers for SuperClaude.

This module records how often agents are loaded and executed, persisting the
counts to the project metrics directory so maintenance tooling can surface
“active” versus “planned” personas without touching configuration files.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..Monitoring.paths import get_metrics_dir

_LOCK = threading.Lock()
_CACHE: Dict[str, Dict[str, int]] = {}
_LOADED = False
_USAGE_PATH: Optional[Path] = None


def _usage_file() -> Path:
    """Return the path to the usage JSON file."""
    global _USAGE_PATH
    if _USAGE_PATH is None:
        _USAGE_PATH = get_metrics_dir() / "agent_usage.json"
    return _USAGE_PATH


def _load_cache() -> Dict[str, Dict[str, int]]:
    """Lazy-load usage data from disk into memory."""
    global _LOADED
    if _LOADED:
        return _CACHE

    path = _usage_file()
    data: Dict[str, Dict[str, int]] = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for agent, stats in payload.items():
                    if not isinstance(stats, dict):
                        continue
                    loaded = int(stats.get("loaded", 0))
                    executed = int(stats.get("executed", 0))
                    source = stats.get("source", "unknown")
                    plan_only = int(stats.get("plan_only", 0))
                    data[agent] = {
                        "loaded": max(0, loaded),
                        "executed": max(0, executed),
                        "plan_only": max(0, plan_only),
                        "source": str(source or "unknown"),
                    }
        except Exception:
            # Corrupted payloads are treated as empty; caller can repopulate.
            data = {}

    _CACHE.clear()
    _CACHE.update(data)
    _LOADED = True
    return _CACHE


def _persist_cache() -> None:
    """Write the in-memory cache back to disk."""
    path = _usage_file()
    serializable = {
        agent: {
            "loaded": stats.get("loaded", 0),
            "executed": stats.get("executed", 0),
            "plan_only": stats.get("plan_only", 0),
            "source": stats.get("source", "unknown"),
        }
        for agent, stats in _CACHE.items()
    }
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True), encoding="utf-8")


def _bump(agent: str, field: str, source: Optional[str] = None) -> None:
    """Increment a single usage field."""
    if not agent:
        return

    with _LOCK:
        cache = _load_cache()
        entry = cache.setdefault(agent, {"loaded": 0, "executed": 0, "plan_only": 0, "source": source or "unknown"})
        entry[field] = max(0, int(entry.get(field, 0))) + 1
        if source:
            entry["source"] = source
        _persist_cache()


def record_load(agent: str, source: Optional[str] = None) -> None:
    """Record that an agent was loaded."""
    _bump(agent, "loaded", source=source)


def record_execution(agent: str, source: Optional[str] = None) -> None:
    """Record that an agent executed."""
    _bump(agent, "executed", source=source)


def record_plan_only(agent: str, source: Optional[str] = None) -> None:
    """Record that an agent returned plan-only guidance."""
    _bump(agent, "plan_only", source=source)


def get_usage_snapshot() -> Dict[str, Dict[str, int]]:
    """
    Return a shallow copy of the current usage snapshot.

    The data shape is: {agent_name: {"loaded": int, "executed": int, "source": str}}
    """
    with _LOCK:
        cache = _load_cache()
        return {agent: dict(stats) for agent, stats in cache.items()}


def classify_agents(agent_names: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, int]]:
    """
    Build usage buckets for reporting.

    Args:
        agent_names: Mapping of agent name -> metadata (expects 'source' key with
                     values 'core' or 'extended').

    Returns:
        Dictionary with three keys (active, observed, planned) containing counts.
    """
    snapshot = get_usage_snapshot()
    active = {
        name: snapshot[name]
        for name in snapshot
        if snapshot[name].get("executed", 0) > 0
    }
    observed = {
        name: snapshot[name]
        for name in snapshot
        if snapshot[name].get("executed", 0) == 0 and snapshot[name].get("loaded", 0) > 0
    }

    planned = {
        name: {"loaded": 0, "executed": 0, "source": agent_names.get(name, {}).get("source", "unknown")}
        for name in agent_names
        if name not in snapshot
    }

    return {
        "active": active,
        "observed": observed,
        "planned": planned,
    }


def write_markdown_report(
    registry_summary: Dict[str, Dict[str, str]],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Write a markdown summary describing agent usage.

    Args:
        registry_summary: Mapping of agent name -> metadata (expects 'source').
        output_path: Optional explicit location. Defaults to
                     ``.superclaude_metrics/agent_usage_report.md``.

    Returns:
        Path to the written report.
    """
    buckets = classify_agents(registry_summary)
    lines = [
        "# SuperClaude Agent Usage",
        "",
        "| Bucket | Agents | Description |",
        "|--------|--------|-------------|",
        f"| Active | {len(buckets['active'])} | Executed at least once |",
        f"| Observed | {len(buckets['observed'])} | Loaded but not yet executed |",
        f"| Planned | {len(buckets['planned'])} | Discovered but untouched |",
        "",
    ]

    def _render_section(title: str, data: Dict[str, Dict[str, int]]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not data:
            lines.append("_None observed yet._")
            lines.append("")
            return
        lines.append("| Agent | Loaded | Executed | Source |")
        lines.append("|-------|--------|----------|--------|")
        for name in sorted(data):
            stats = data[name]
            lines.append(
                f"| {name} | {stats.get('loaded', 0)} | {stats.get('executed', 0)} | {stats.get('source', 'unknown')} |"
            )
        lines.append("")

    _render_section("Active Agents", buckets["active"])
    _render_section("Observed (Loaded Only)", buckets["observed"])
    _render_section("Planned (Discovered, Unused)", buckets["planned"])

    output = output_path or (get_metrics_dir() / "agent_usage_report.md")
    output.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return output


def reset_usage_stats(for_tests: bool = False) -> None:
    """
    Reset in-memory stats. If ``for_tests`` is True, the persisted file is removed.
    """
    global _LOADED, _USAGE_PATH
    with _LOCK:
        _CACHE.clear()
        _LOADED = False
        if for_tests:
            _USAGE_PATH = None
        if for_tests:
            path = _usage_file()
            if path.exists():
                try:
                    path.unlink()
                except Exception:
                    path.write_text("{}", encoding="utf-8")


__all__ = [
    "record_load",
    "record_execution",
    "record_plan_only",
    "get_usage_snapshot",
    "classify_agents",
    "write_markdown_report",
    "reset_usage_stats",
]
