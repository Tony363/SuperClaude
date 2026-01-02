"""
Metrics emitter interface for SuperClaude operational metrics.

This module provides a callback-based metrics system that decouples
the orchestrator from specific metrics backends (Prometheus, StatsD, etc.).

Usage:
    from core.metrics import MetricsEmitter, noop_emitter, InMemoryMetricsCollector

    # Option 1: Custom emitter function
    def my_emitter(name: str, value: Any, tags: dict | None = None):
        print(f"{name}={value} tags={tags}")

    orchestrator = LoopOrchestrator(config, metrics_emitter=my_emitter)

    # Option 2: In-memory collector for testing
    collector = InMemoryMetricsCollector()
    orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
    # After run: collector.get("loop.duration.seconds")

    # Option 3: Logging-based emitter
    emitter = LoggingMetricsEmitter(logging.getLogger("metrics"))
    orchestrator = LoopOrchestrator(config, metrics_emitter=emitter)

Metric naming convention:
    <component>.<subject>.<unit>
    e.g., "loop.duration.seconds", "learning.skills.applied.count"

Metric types (indicated by suffix):
    .count - Incremental counter (use for events)
    .gauge - Point-in-time value (use for current state)
    .seconds - Duration measurement (use for timing)

Available Metrics:
    Loop Orchestrator (core.loop_orchestrator):
        loop.started.count              - Loop initiated
        loop.completed.count            - Loop finished (tags: termination_reason)
        loop.duration.seconds           - Total loop time (tags: termination_reason)
        loop.iterations.total.gauge     - Iterations executed (tags: termination_reason)
        loop.quality_score.final.gauge  - Final quality score (tags: termination_reason)
        loop.errors.count               - Errors encountered (tags: reason)
        loop.iteration.duration.seconds - Per-iteration timing
        loop.iteration.quality_score.gauge    - Per-iteration quality
        loop.iteration.quality_delta.gauge    - Per-iteration improvement

    Learning Orchestrator (core.skill_learning_integration):
        learning.skills.applied.count   - Skills injected at start
        learning.skills.extracted.count - Skills learned (tags: domain, success)
        learning.skills.promoted.count  - Skills auto-promoted (tags: reason)

Integration Examples:
    # Prometheus integration
    from prometheus_client import Counter, Gauge, Histogram

    counters = {}
    gauges = {}

    def prometheus_emitter(name, value, tags=None):
        labels = tags or {}
        if name.endswith('.count'):
            if name not in counters:
                counters[name] = Counter(name.replace('.', '_'), '', list(labels.keys()))
            counters[name].labels(**labels).inc(value)
        elif name.endswith('.gauge'):
            if name not in gauges:
                gauges[name] = Gauge(name.replace('.', '_'), '', list(labels.keys()))
            gauges[name].labels(**labels).set(value)

    # StatsD integration
    import statsd
    client = statsd.StatsClient()

    def statsd_emitter(name, value, tags=None):
        if name.endswith('.count'):
            client.incr(name, value)
        elif name.endswith('.gauge'):
            client.gauge(name, value)
        elif name.endswith('.seconds'):
            client.timing(name, value * 1000)  # Convert to ms
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable


@runtime_checkable
class MetricsEmitter(Protocol):
    """Protocol defining the interface for metrics emission.

    Implementations can send metrics to various backends:
    - Prometheus (via prometheus_client)
    - StatsD
    - CloudWatch
    - Simple logging
    - In-memory collection for testing
    """

    def __call__(
        self,
        metric_name: str,
        value: Any,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Emit a metric.

        Args:
            metric_name: Name following convention <component>.<subject>.<unit>
            value: Metric value (int, float, or other numeric type)
            tags: Optional key-value tags for metric dimensions
        """
        ...


def noop_emitter(
    metric_name: str,
    value: Any,
    tags: Optional[Dict[str, str]] = None,
) -> None:
    """A metrics emitter that does nothing.

    Used as default when no emitter is configured.
    """
    pass


class InMemoryMetricsCollector:
    """Simple in-memory metrics collector for testing.

    Example:
        collector = InMemoryMetricsCollector()
        orchestrator = LoopOrchestrator(config, metrics_emitter=collector)
        result = orchestrator.run(context, invoker)

        assert collector.get("loop.completed.count") == 1
        assert collector.get("loop.duration.seconds") > 0
    """

    def __init__(self) -> None:
        """Initialize the collector with empty metrics storage."""
        self.metrics: list[Dict[str, Any]] = []

    def __call__(
        self,
        metric_name: str,
        value: Any,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric emission."""
        self.metrics.append(
            {
                "name": metric_name,
                "value": value,
                "tags": tags or {},
            }
        )

    def get(self, metric_name: str) -> Any:
        """Get the last value for a metric name."""
        for m in reversed(self.metrics):
            if m["name"] == metric_name:
                return m["value"]
        return None

    def get_all(self, metric_name: str) -> list[Any]:
        """Get all values for a metric name."""
        return [m["value"] for m in self.metrics if m["name"] == metric_name]

    def count(self, metric_name: str) -> int:
        """Count how many times a metric was emitted."""
        return sum(1 for m in self.metrics if m["name"] == metric_name)

    def filter_by_tags(
        self,
        metric_name: str,
        tags: Dict[str, str],
    ) -> list[Dict[str, Any]]:
        """Get metrics matching name and tags."""
        results = []
        for m in self.metrics:
            if m["name"] != metric_name:
                continue
            if all(m["tags"].get(k) == v for k, v in tags.items()):
                results.append(m)
        return results

    def clear(self) -> None:
        """Clear all collected metrics."""
        self.metrics.clear()


class LoggingMetricsEmitter:
    """Metrics emitter that logs metrics using Python logging.

    Example:
        import logging
        emitter = LoggingMetricsEmitter(logging.getLogger("metrics"))
        orchestrator = LoopOrchestrator(config, metrics_emitter=emitter)
    """

    def __init__(self, logger: Any, level: int = 10) -> None:  # 10 = DEBUG
        """Initialize with a logger instance.

        Args:
            logger: Python logger instance
            level: Log level for metric emissions (default: DEBUG)
        """
        self.logger = logger
        self.level = level

    def __call__(
        self,
        metric_name: str,
        value: Any,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log a metric emission."""
        self.logger.log(
            self.level,
            "metric",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_tags": tags or {},
            },
        )
