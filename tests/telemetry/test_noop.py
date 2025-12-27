"""Tests for NoopTelemetryClient."""

import pytest

from SuperClaude.Telemetry.interfaces import MetricType
from SuperClaude.Telemetry.noop import NoopTelemetryClient


class TestNoopTelemetryClientBasics:
    """Basic functionality tests."""

    def test_all_methods_are_silent(self):
        """All methods execute without error or side effects."""
        client = NoopTelemetryClient()

        # None of these should raise or have any observable effect
        client.record_event("event", {"key": "value"})
        client.record_event("event", {}, tags={"tag": "value"})
        client.record_metric("metric", 42, MetricType.COUNTER)
        client.record_metric("metric", 1.5, MetricType.GAUGE, tags={"env": "test"})
        client.increment("counter")
        client.increment("counter", value=10, tags={"type": "test"})
        client.flush()
        client.close()

    def test_methods_accept_all_parameter_combinations(self):
        """All method signatures work correctly."""
        client = NoopTelemetryClient()

        # record_event variations
        client.record_event("name", {})
        client.record_event("name", {"data": 123})
        client.record_event("name", {"nested": {"dict": True}}, tags=None)
        client.record_event("name", {}, tags={"a": "b"})

        # record_metric variations
        client.record_metric("metric", 0, MetricType.COUNTER)
        client.record_metric("metric", -1, MetricType.GAUGE)
        client.record_metric("metric", 99.99, MetricType.TIMER)
        client.record_metric("metric", 100, MetricType.HISTOGRAM, tags=None)
        client.record_metric("metric", 1, MetricType.COUNTER, tags={"x": "y"})

        # increment variations
        client.increment("counter")
        client.increment("counter", value=1)
        client.increment("counter", value=100)
        client.increment("counter", tags={"key": "val"})
        client.increment("counter", value=5, tags={"key": "val"})


class TestNoopTelemetryClientProtocol:
    """Protocol compliance tests."""

    def test_implements_protocol(self):
        """NoopTelemetryClient satisfies TelemetryClient protocol."""
        client = NoopTelemetryClient()

        # Verify all protocol methods exist and are callable
        assert hasattr(client, "record_event")
        assert callable(client.record_event)

        assert hasattr(client, "record_metric")
        assert callable(client.record_metric)

        assert hasattr(client, "increment")
        assert callable(client.increment)

        assert hasattr(client, "flush")
        assert callable(client.flush)

        assert hasattr(client, "close")
        assert callable(client.close)

    def test_method_signatures_match_protocol(self):
        """Method signatures match TelemetryClient protocol."""
        client = NoopTelemetryClient()

        # These calls should work without TypeError
        client.record_event(name="event", payload={})
        client.record_event(name="event", payload={}, tags={"a": "b"})

        client.record_metric(name="metric", value=1, kind=MetricType.COUNTER)
        client.record_metric(name="metric", value=1, kind=MetricType.GAUGE, tags={"a": "b"})

        client.increment(name="counter")
        client.increment(name="counter", value=5)
        client.increment(name="counter", tags={"a": "b"})


class TestNoopTelemetryClientContextManager:
    """Context manager tests."""

    def test_context_manager_works(self):
        """Context manager entry/exit work correctly."""
        with NoopTelemetryClient() as client:
            assert isinstance(client, NoopTelemetryClient)
            client.record_event("event", {})

    def test_context_manager_returns_self(self):
        """__enter__ returns the client instance."""
        client = NoopTelemetryClient()
        with client as ctx:
            assert ctx is client

    def test_context_manager_exit_handles_exception(self):
        """Context manager exit handles exceptions gracefully."""
        with pytest.raises(ValueError), NoopTelemetryClient() as client:
            client.record_event("event", {})
            raise ValueError("Test exception")
        # No additional exception from __exit__


class TestNoopTelemetryClientReturnValues:
    """Return value tests."""

    def test_methods_return_none(self):
        """All methods return None."""
        client = NoopTelemetryClient()

        assert client.record_event("event", {}) is None
        assert client.record_metric("metric", 1, MetricType.COUNTER) is None
        assert client.increment("counter") is None
        assert client.flush() is None
        assert client.close() is None


class TestNoopTelemetryClientMultipleCalls:
    """Multiple call tests."""

    def test_can_call_methods_repeatedly(self):
        """Methods can be called multiple times without issues."""
        client = NoopTelemetryClient()

        for _ in range(100):
            client.record_event("event", {"iteration": _})

        for _ in range(100):
            client.record_metric("metric", _, MetricType.COUNTER)

        for _ in range(100):
            client.increment("counter")

        # Multiple flushes and closes are fine
        client.flush()
        client.flush()
        client.close()
        client.close()

    def test_can_use_after_close(self):
        """Methods work even after close() is called."""
        client = NoopTelemetryClient()
        client.close()

        # Should still work (no-op)
        client.record_event("event", {})
        client.record_metric("metric", 1, MetricType.GAUGE)
        client.increment("counter")
        client.flush()
