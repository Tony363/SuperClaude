#!/usr/bin/env python3
"""CI guard that fails when hallucination plan-only rate exceeds threshold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check hallucination guardrail metrics."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Maximum allowed plan-only rate for requires-evidence commands (default: 0.05)",
    )
    parser.add_argument(
        "--metrics",
        type=Path,
        default=Path(".superclaude_metrics/metrics.jsonl"),
        help="Path to metrics JSONL file (default: .superclaude_metrics/metrics.jsonl)",
    )
    return parser.parse_args()


def load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def compute_plan_only_rate(events: list[dict]) -> tuple[float, int, int]:
    total = 0
    plan_only = 0
    for event in events:
        if event.get("type") != "hallucination.guardrail":
            continue
        data = event.get("data", {})
        if not data.get("requires_evidence"):
            continue
        total += 1
        if data.get("plan_only"):
            plan_only += 1
    rate = (plan_only / total) if total else 0.0
    return rate, plan_only, total


def main() -> int:
    args = parse_args()
    events = load_events(args.metrics)
    rate, plan_only, total = compute_plan_only_rate(events)

    print(
        f"Hallucination guardrail: plan-only={plan_only}, total={total}, rate={rate:.3f}, threshold={args.threshold:.3f}"
    )

    if total and rate > args.threshold:
        print("::error::Plan-only rate exceeds threshold; block build.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
