"""
No-op telemetry client for SuperClaude Framework.

A null implementation that discards all telemetry data.
Useful for testing and when telemetry is disabled.
"""

from typing import Any

from .interfaces import MetricType


class NoopTelemetryClient:
    """
    No-op telemetry client that discards all data.

    Use when telemetry is disabled or for testing.
    """

    def record_event(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Discard event."""
        pass

    def record_metric(
        self,
        name: str,
        value: float | int,
        kind: MetricType,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Discard metric."""
        pass

    def increment(
        self,
        name: str,
        *,
        value: int = 1,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Discard increment."""
        pass

    def flush(self) -> None:
        """No-op flush."""
        pass

    def close(self) -> None:
        """No-op close."""
        pass

    def __enter__(self) -> "NoopTelemetryClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        pass
