"""Tests for SuperClaude Telemetry module (interfaces and JSONL client)."""

from __future__ import annotations

import json


class TestMetricType:
    """Tests for MetricType enum."""

    def test_counter_value(self):
        from SuperClaude.Telemetry.interfaces import MetricType

        assert MetricType.COUNTER.value == "counter"

    def test_gauge_value(self):
        from SuperClaude.Telemetry.interfaces import MetricType

        assert MetricType.GAUGE.value == "gauge"

    def test_timer_value(self):
        from SuperClaude.Telemetry.interfaces import MetricType

        assert MetricType.TIMER.value == "timer"

    def test_histogram_value(self):
        from SuperClaude.Telemetry.interfaces import MetricType

        assert MetricType.HISTOGRAM.value == "histogram"

    def test_enum_member_count(self):
        from SuperClaude.Telemetry.interfaces import MetricType

        assert len(MetricType) == 4


class TestJsonlTelemetryClientInit:
    """Tests for JsonlTelemetryClient initialization."""

    def test_default_metrics_dir(self, tmp_path, monkeypatch):
        """Default dir should come from env or fallback."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path / "metrics"))
        client = JsonlTelemetryClient()
        assert client.metrics_dir == tmp_path / "metrics"
        client.close()

    def test_custom_metrics_dir(self, tmp_path):
        """Custom dir should be used."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        custom = tmp_path / "custom_metrics"
        client = JsonlTelemetryClient(metrics_dir=custom)
        assert client.metrics_dir == custom
        assert custom.exists()
        client.close()

    def test_custom_session_id(self, tmp_path):
        """Custom session ID should be preserved."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, session_id="test-session")
        assert client.session_id == "test-session"
        client.close()

    def test_auto_generated_session_id(self, tmp_path):
        """Session ID should be auto-generated if not provided."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path)
        assert client.session_id  # Non-empty
        assert len(client.session_id) == 8  # uuid4()[:8]
        client.close()

    def test_buffer_size_default(self, tmp_path):
        """Default buffer size should be 10."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path)
        assert client.buffer_size == 10
        client.close()

    def test_custom_buffer_size(self, tmp_path):
        """Custom buffer size should be preserved."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=5)
        assert client.buffer_size == 5
        client.close()

    def test_creates_metrics_directory(self, tmp_path):
        """Init should create the metrics directory."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        new_dir = tmp_path / "new" / "nested" / "metrics"
        client = JsonlTelemetryClient(metrics_dir=new_dir)
        assert new_dir.exists()
        client.close()


class TestJsonlTelemetryClientEvents:
    """Tests for event recording."""

    def test_record_event_buffered(self, tmp_path):
        """Events should be buffered until flush."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100)
        client.record_event("test.event", {"key": "value"})

        # Should be in buffer, not yet written
        events_file = tmp_path / "events.jsonl"
        assert not events_file.exists()
        assert len(client._event_buffer) == 1
        client.close()

    def test_record_event_with_tags(self, tmp_path):
        """Events with tags should include tags in output."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("tagged.event", {"data": 1}, tags={"env": "test"})

        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()
        line = events_file.read_text().strip()
        entry = json.loads(line)
        assert entry["tags"] == {"env": "test"}
        client.close()

    def test_auto_flush_on_buffer_full(self, tmp_path):
        """Events should auto-flush when buffer is full."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=3)
        for i in range(3):
            client.record_event(f"event.{i}", {"i": i})

        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 3
        client.close()

    def test_event_has_timestamp(self, tmp_path):
        """Events should have timestamps."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("test", {})

        events_file = tmp_path / "events.jsonl"
        entry = json.loads(events_file.read_text().strip())
        assert "timestamp" in entry

    def test_event_has_session_id(self, tmp_path):
        """Events should include session ID."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, session_id="sess-1", buffer_size=1)
        client.record_event("test", {})

        events_file = tmp_path / "events.jsonl"
        entry = json.loads(events_file.read_text().strip())
        assert entry["session_id"] == "sess-1"
        client.close()

    def test_no_tags_omits_tags_key(self, tmp_path):
        """Events without tags should not have tags key."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("test", {"data": 1})

        events_file = tmp_path / "events.jsonl"
        entry = json.loads(events_file.read_text().strip())
        assert "tags" not in entry
        client.close()


class TestJsonlTelemetryClientMetrics:
    """Tests for metric recording."""

    def test_record_metric_counter(self, tmp_path):
        """Should record counter metrics."""
        from SuperClaude.Telemetry.interfaces import MetricType
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_metric("req.count", 1, MetricType.COUNTER)

        metrics_file = tmp_path / "metrics.jsonl"
        entry = json.loads(metrics_file.read_text().strip())
        assert entry["metric"] == "req.count"
        assert entry["value"] == 1
        assert entry["type"] == "counter"
        client.close()

    def test_record_metric_gauge(self, tmp_path):
        """Should record gauge metrics."""
        from SuperClaude.Telemetry.interfaces import MetricType
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_metric("cpu.usage", 75.5, MetricType.GAUGE)

        metrics_file = tmp_path / "metrics.jsonl"
        entry = json.loads(metrics_file.read_text().strip())
        assert entry["type"] == "gauge"
        assert entry["value"] == 75.5
        client.close()

    def test_record_metric_with_tags(self, tmp_path):
        """Metrics with tags should include them."""
        from SuperClaude.Telemetry.interfaces import MetricType
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_metric("api.latency", 120, MetricType.TIMER, tags={"endpoint": "/health"})

        metrics_file = tmp_path / "metrics.jsonl"
        entry = json.loads(metrics_file.read_text().strip())
        assert entry["tags"]["endpoint"] == "/health"
        client.close()

    def test_increment_counter(self, tmp_path):
        """increment() should record counter metric with value."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.increment("page.views")

        metrics_file = tmp_path / "metrics.jsonl"
        entry = json.loads(metrics_file.read_text().strip())
        assert entry["metric"] == "page.views"
        assert entry["value"] == 1
        assert entry["type"] == "counter"
        client.close()

    def test_increment_custom_value(self, tmp_path):
        """increment() should support custom increment values."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.increment("batch.size", value=10)

        metrics_file = tmp_path / "metrics.jsonl"
        entry = json.loads(metrics_file.read_text().strip())
        assert entry["value"] == 10
        client.close()

    def test_increment_with_tags(self, tmp_path):
        """increment() should pass tags through."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.increment("errors", tags={"severity": "high"})

        metrics_file = tmp_path / "metrics.jsonl"
        entry = json.loads(metrics_file.read_text().strip())
        assert entry["tags"]["severity"] == "high"
        client.close()

    def test_metric_auto_flush(self, tmp_path):
        """Metrics should auto-flush when buffer is full."""
        from SuperClaude.Telemetry.interfaces import MetricType
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=2)
        client.record_metric("m1", 1.0, MetricType.GAUGE)
        client.record_metric("m2", 2.0, MetricType.GAUGE)

        metrics_file = tmp_path / "metrics.jsonl"
        assert metrics_file.exists()
        lines = metrics_file.read_text().strip().split("\n")
        assert len(lines) == 2
        client.close()


class TestJsonlTelemetryClientFlush:
    """Tests for flush and close behavior."""

    def test_explicit_flush(self, tmp_path):
        """flush() should write all buffered data."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100)
        client.record_event("e1", {})
        client.record_event("e2", {})
        client.increment("m1")

        # Nothing written yet
        assert not (tmp_path / "events.jsonl").exists()

        client.flush()

        events_file = tmp_path / "events.jsonl"
        metrics_file = tmp_path / "metrics.jsonl"
        assert events_file.exists()
        assert metrics_file.exists()
        assert len(events_file.read_text().strip().split("\n")) == 2
        client.close()

    def test_close_flushes(self, tmp_path):
        """close() should flush remaining buffered data."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100)
        client.record_event("closing", {"data": True})
        client.close()

        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()
        entry = json.loads(events_file.read_text().strip())
        assert entry["event"] == "closing"

    def test_flush_empty_buffers_no_files(self, tmp_path):
        """Flushing empty buffers should not create files."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100)
        client.flush()

        assert not (tmp_path / "events.jsonl").exists()
        assert not (tmp_path / "metrics.jsonl").exists()
        client.close()

    def test_auto_flush_disabled(self, tmp_path):
        """auto_flush=False should not flush on buffer full."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=2, auto_flush=False)
        client.record_event("e1", {})
        client.record_event("e2", {})
        client.record_event("e3", {})

        # Buffer full but no auto-flush
        assert not (tmp_path / "events.jsonl").exists()
        assert len(client._event_buffer) == 3  # All still in buffer
        client.close()


class TestJsonlTelemetryClientContextManager:
    """Tests for context manager usage."""

    def test_context_manager_enter_returns_self(self, tmp_path):
        """__enter__ should return the client."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path)
        with client as c:
            assert c is client

    def test_context_manager_flushes_on_exit(self, tmp_path):
        """Context manager exit should flush."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        with JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100) as client:
            client.record_event("ctx", {"in_ctx": True})

        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()

    def test_multiple_flushes_append(self, tmp_path):
        """Multiple flushes should append to same file."""
        from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient

        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=2)
        client.record_event("e1", {})
        client.record_event("e2", {})  # Triggers auto-flush
        client.record_event("e3", {})
        client.flush()  # Flush remaining

        events_file = tmp_path / "events.jsonl"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 3
        client.close()
