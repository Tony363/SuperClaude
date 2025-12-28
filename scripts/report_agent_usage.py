#!/usr/bin/env python3
"""Generate a markdown report summarising agent usage."""

from __future__ import annotations

import argparse
from pathlib import Path

from SuperClaude.Agents import usage_tracker
from SuperClaude.Agents.registry import AgentRegistry


def _build_registry_summary(registry: AgentRegistry) -> dict:
    """Return mapping of agent name to a minimal metadata dict."""
    summary = {}
    for name in registry.get_all_agents():
        config = registry.get_agent_config(name) or {}
        source = "core" if config.get("is_core") else "extended"
        summary[name] = {"source": source}
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit a markdown report of SuperClaude agent usage."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the generated markdown file (defaults to .superclaude_metrics/agent_usage_report.md).",
    )
    args = parser.parse_args()

    registry = AgentRegistry()
    registry.discover_agents(force=True)
    registry_summary = _build_registry_summary(registry)

    report_path = usage_tracker.write_markdown_report(registry_summary, output_path=args.output)
    print(f"Wrote agent usage report to {report_path}")


if __name__ == "__main__":
    main()
