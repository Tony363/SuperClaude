from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MetricsSink:
    """Interface for persisting metrics events."""

    def write_event(self, event: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError


class JsonlMetricsSink(MetricsSink):
    """Append-only JSON Lines sink for metrics, alerts, and snapshots."""

    def __init__(self, file_path: Path | None = None):
        if file_path is None:
            base = Path.cwd() / ".superclaude_metrics"
            base.mkdir(parents=True, exist_ok=True)
            file_path = base / "metrics.jsonl"
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path = file_path

    def write_event(self, event: dict[str, Any]) -> None:
        try:
            with self.file_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as exc:
            # Best-effort persistence; surface for diagnostics without raising.
            logger.debug(
                "Failed to append metrics event to %s: %s",
                self.file_path,
                exc,
                exc_info=True,
            )
