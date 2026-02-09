"""
Telemetry interfaces and types for SuperClaude Framework.

Defines the protocol for telemetry clients and metric types.
"""

from enum import Enum
from typing import Any, Protocol


class MetricType(Enum):
    """Types of metrics that can be recorded."""

    COUNTER = "counter"  # Monotonically increasing count
    GAUGE = "gauge"  # Point-in-time value
    TIMER = "timer"  # Duration measurement
    HISTOGRAM = "histogram"  # Distribution of values


class TelemetryClient(Protocol):
    """
    Protocol for telemetry clients.

    Implementations must provide methods for recording events and metrics.
    """

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

    def flush(self) -> None:
        """Flush any buffered telemetry data."""

    def close(self) -> None:
        """Close the telemetry client and release resources."""
