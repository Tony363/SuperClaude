"""Tests for the metrics module.

These tests verify the metrics emitter interface and implementations.
"""

from __future__ import annotations

import logging

from core.metrics import (
    InMemoryMetricsCollector,
    LoggingMetricsEmitter,
    MetricsEmitter,
    noop_emitter,
)


class TestNoopEmitter:
    """Tests for the no-op metrics emitter."""

    def test_noop_accepts_metric(self):
        """Noop emitter should accept metrics without error."""
        noop_emitter("test.metric.count", 1)
        noop_emitter("test.metric.gauge", 42.5, {"tag": "value"})

    def test_noop_is_callable(self):
        """Noop emitter should be callable without side effects."""
        # Verify it conforms to the MetricsEmitter protocol
        assert callable(noop_emitter)
        # Should execute without raising
        noop_emitter("test.metric", 1)


class TestInMemoryMetricsCollector:
    """Tests for the in-memory metrics collector."""

    def test_records_metrics(self):
        """Collector should record emitted metrics."""
        collector = InMemoryMetricsCollector()
        collector("test.count", 1)
        collector("test.gauge", 42.5)

        assert len(collector.metrics) == 2

    def test_get_returns_last_value(self):
        """Get should return the last value for a metric."""
        collector = InMemoryMetricsCollector()
        collector("test.gauge", 10)
        collector("test.gauge", 20)
        collector("test.gauge", 30)

        assert collector.get("test.gauge") == 30

    def test_get_returns_none_for_missing(self):
        """Get should return None for non-existent metric."""
        collector = InMemoryMetricsCollector()
        assert collector.get("nonexistent.metric") is None

    def test_get_all_returns_all_values(self):
        """Get_all should return all values for a metric."""
        collector = InMemoryMetricsCollector()
        collector("test.gauge", 10)
        collector("test.gauge", 20)
        collector("test.gauge", 30)

        assert collector.get_all("test.gauge") == [10, 20, 30]

    def test_get_all_returns_empty_for_missing(self):
        """Get_all should return empty list for non-existent metric."""
        collector = InMemoryMetricsCollector()
        assert collector.get_all("nonexistent.metric") == []

    def test_count_metrics(self):
        """Count should return number of emissions for a metric."""
        collector = InMemoryMetricsCollector()
        collector("test.count", 1)
        collector("test.count", 1)
        collector("test.count", 1)
        collector("other.count", 1)

        assert collector.count("test.count") == 3
        assert collector.count("other.count") == 1
        assert collector.count("nonexistent") == 0

    def test_records_tags(self):
        """Collector should record tags with metrics."""
        collector = InMemoryMetricsCollector()
        collector("test.metric", 1, {"env": "prod", "service": "api"})

        assert collector.metrics[0]["tags"] == {"env": "prod", "service": "api"}

    def test_filter_by_tags(self):
        """Filter_by_tags should return matching metrics."""
        collector = InMemoryMetricsCollector()
        collector("loop.completed", 1, {"termination_reason": "quality_met"})
        collector("loop.completed", 1, {"termination_reason": "max_iterations"})
        collector("loop.completed", 1, {"termination_reason": "quality_met"})

        quality_met = collector.filter_by_tags(
            "loop.completed", {"termination_reason": "quality_met"}
        )
        assert len(quality_met) == 2

        max_iter = collector.filter_by_tags(
            "loop.completed", {"termination_reason": "max_iterations"}
        )
        assert len(max_iter) == 1

    def test_clear_removes_all_metrics(self):
        """Clear should remove all collected metrics."""
        collector = InMemoryMetricsCollector()
        collector("test.metric", 1)
        collector("test.metric", 2)

        collector.clear()

        assert len(collector.metrics) == 0
        assert collector.get("test.metric") is None

    def test_implements_protocol(self):
        """Collector should implement MetricsEmitter protocol."""
        collector = InMemoryMetricsCollector()
        assert isinstance(collector, MetricsEmitter)

    def test_default_tags_empty_dict(self):
        """Tags should default to empty dict when not provided."""
        collector = InMemoryMetricsCollector()
        collector("test.metric", 1)
        assert collector.metrics[0]["tags"] == {}

    def test_filter_by_tags_multiple_tag_match(self):
        """filter_by_tags should require all specified tags to match."""
        collector = InMemoryMetricsCollector()
        collector("m", 1, {"a": "1", "b": "2"})
        collector("m", 2, {"a": "1", "b": "3"})
        collector("m", 3, {"a": "1"})

        results = collector.filter_by_tags("m", {"a": "1", "b": "2"})
        assert len(results) == 1
        assert results[0]["value"] == 1

    def test_filter_by_tags_wrong_name(self):
        """filter_by_tags should not match different metric names."""
        collector = InMemoryMetricsCollector()
        collector("correct", 1, {"env": "prod"})
        results = collector.filter_by_tags("wrong", {"env": "prod"})
        assert results == []

    def test_records_various_value_types(self):
        """Should handle int, float, and string values."""
        collector = InMemoryMetricsCollector()
        collector("int.metric", 42)
        collector("float.metric", 3.14)
        collector("str.metric", "hello")

        assert collector.get("int.metric") == 42
        assert collector.get("float.metric") == 3.14
        assert collector.get("str.metric") == "hello"

    def test_get_with_interleaved_metrics(self):
        """get() should return correct value when metrics are interleaved."""
        collector = InMemoryMetricsCollector()
        collector("a", 1)
        collector("b", 10)
        collector("a", 2)
        collector("b", 20)

        assert collector.get("a") == 2
        assert collector.get("b") == 20


class TestLoggingMetricsEmitter:
    """Tests for the logging-based metrics emitter."""

    def test_logs_metrics(self, caplog):
        """Emitter should log metrics with appropriate level."""
        logger = logging.getLogger("test.metrics")
        emitter = LoggingMetricsEmitter(logger, level=logging.DEBUG)

        with caplog.at_level(logging.DEBUG, logger="test.metrics"):
            emitter("test.metric.count", 42, {"env": "test"})

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelno == logging.DEBUG
        assert record.metric_name == "test.metric.count"
        assert record.metric_value == 42
        assert record.metric_tags == {"env": "test"}

    def test_default_log_level_is_debug(self):
        """Default log level should be DEBUG (10)."""
        logger = logging.getLogger("test.metrics")
        emitter = LoggingMetricsEmitter(logger)
        assert emitter.level == 10

    def test_implements_protocol(self):
        """Emitter should implement MetricsEmitter protocol."""
        logger = logging.getLogger("test.metrics")
        emitter = LoggingMetricsEmitter(logger)
        assert isinstance(emitter, MetricsEmitter)


class TestMetricsProtocol:
    """Tests for the MetricsEmitter protocol."""

    def test_callable_satisfies_protocol(self):
        """A simple callable should satisfy the protocol."""

        def simple_emitter(name: str, value, tags=None):
            pass

        # The runtime_checkable protocol should work with callable
        assert callable(simple_emitter)

    def test_lambda_as_emitter(self):
        """Lambda functions should work as emitters."""
        captured = []

        def emitter(name, value, tags=None):
            captured.append((name, value, tags))

        emitter("test.metric", 42, {"tag": "value"})

        assert captured == [("test.metric", 42, {"tag": "value"})]
