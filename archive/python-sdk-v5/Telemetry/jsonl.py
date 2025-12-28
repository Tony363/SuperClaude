"""
JSONL-based telemetry client for SuperClaude Framework.

Writes events and metrics to JSONL files for local storage and analysis.
"""

import fcntl
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .interfaces import MetricType

logger = logging.getLogger(__name__)


class JsonlTelemetryClient:
    """
    Telemetry client that writes to JSONL files.

    Features:
    - Atomic file appends with file locking
    - Session ID tracking
    - Timestamp on all entries
    - Buffered writes with configurable flush
    """

    def __init__(
        self,
        metrics_dir: str | Path | None = None,
        session_id: str | None = None,
        buffer_size: int = 10,
        auto_flush: bool = True,
    ):
        """
        Initialize JSONL telemetry client.

        Args:
            metrics_dir: Directory for JSONL files (default: .superclaude_metrics/)
            session_id: Unique session identifier (auto-generated if not provided)
            buffer_size: Number of entries to buffer before auto-flush
            auto_flush: Whether to auto-flush when buffer is full
        """
        self.metrics_dir = Path(
            metrics_dir
            or os.environ.get("SUPERCLAUDE_METRICS_DIR", ".superclaude_metrics")
        )
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.buffer_size = buffer_size
        self.auto_flush = auto_flush

        # Buffers for batched writes
        self._event_buffer: list[dict[str, Any]] = []
        self._metric_buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()

        # Ensure metrics directory exists
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure metrics directory exists."""
        try:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create metrics directory: {e}")

    def _get_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def _append_jsonl(self, filepath: Path, entries: list[dict[str, Any]]) -> None:
        """
        Atomically append entries to a JSONL file.

        Uses file locking for thread/process safety.
        """
        if not entries:
            return

        try:
            with open(filepath, "a", encoding="utf-8") as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    for entry in entries:
                        f.write(json.dumps(entry, default=str) + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except OSError as e:
            logger.warning(f"Failed to write telemetry to {filepath}: {e}")

    def record_event(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a discrete event.

        Args:
            name: Event name (e.g., 'commands.started', 'agents.invoked')
            payload: Event data
            tags: Optional tags for categorization
        """
        entry = {
            "timestamp": self._get_timestamp(),
            "session_id": self.session_id,
            "event": name,
            "payload": payload,
        }
        if tags:
            entry["tags"] = tags

        with self._lock:
            self._event_buffer.append(entry)
            if self.auto_flush and len(self._event_buffer) >= self.buffer_size:
                self._flush_events()

    def record_metric(
        self,
        name: str,
        value: float | int,
        kind: MetricType,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name (e.g., 'commands.duration_s', 'quality.score')
            value: Metric value
            kind: Type of metric (counter, gauge, timer, histogram)
            tags: Optional tags for categorization
        """
        entry = {
            "timestamp": self._get_timestamp(),
            "session_id": self.session_id,
            "metric": name,
            "value": value,
            "type": kind.value,
        }
        if tags:
            entry["tags"] = tags

        with self._lock:
            self._metric_buffer.append(entry)
            if self.auto_flush and len(self._metric_buffer) >= self.buffer_size:
                self._flush_metrics()

    def increment(
        self,
        name: str,
        *,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            value: Amount to increment (default: 1)
            tags: Optional tags for categorization
        """
        self.record_metric(name, value, MetricType.COUNTER, tags=tags)

    def _flush_events(self) -> None:
        """Flush buffered events to file."""
        if not self._event_buffer:
            return

        events_file = self.metrics_dir / "events.jsonl"
        entries = self._event_buffer.copy()
        self._event_buffer.clear()
        self._append_jsonl(events_file, entries)

    def _flush_metrics(self) -> None:
        """Flush buffered metrics to file."""
        if not self._metric_buffer:
            return

        metrics_file = self.metrics_dir / "metrics.jsonl"
        entries = self._metric_buffer.copy()
        self._metric_buffer.clear()
        self._append_jsonl(metrics_file, entries)

    def flush(self) -> None:
        """Flush all buffered telemetry data."""
        with self._lock:
            self._flush_events()
            self._flush_metrics()

    def close(self) -> None:
        """Close the telemetry client and flush remaining data."""
        self.flush()

    def __enter__(self) -> "JsonlTelemetryClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - flush and close."""
        self.close()
