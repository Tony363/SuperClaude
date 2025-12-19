"""Tests for JsonlTelemetryClient."""

import json
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from SuperClaude.Telemetry.interfaces import MetricType
from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient


class TestJsonlTelemetryClientBasics:
    """Basic functionality tests."""

    def test_record_event_creates_valid_jsonl(self, tmp_path):
        """Events are written as valid JSON lines."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("test.event", {"key": "value"})
        client.flush()

        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()

        with open(events_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["event"] == "test.event"
            assert entry["payload"] == {"key": "value"}
            assert "timestamp" in entry
            assert "session_id" in entry

    def test_record_metric_includes_all_fields(self, tmp_path):
        """Metrics include timestamp, session_id, metric name, value, type."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_metric("test.metric", 42.5, MetricType.GAUGE, tags={"env": "test"})
        client.flush()

        metrics_file = tmp_path / "metrics.jsonl"
        assert metrics_file.exists()

        with open(metrics_file) as f:
            entry = json.loads(f.readline())
            assert entry["metric"] == "test.metric"
            assert entry["value"] == 42.5
            assert entry["type"] == "gauge"
            assert entry["tags"] == {"env": "test"}
            assert "timestamp" in entry
            assert "session_id" in entry

    def test_increment_uses_counter_type(self, tmp_path):
        """increment() calls record_metric with COUNTER type."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.increment("test.counter", value=5)
        client.flush()

        metrics_file = tmp_path / "metrics.jsonl"
        with open(metrics_file) as f:
            entry = json.loads(f.readline())
            assert entry["metric"] == "test.counter"
            assert entry["value"] == 5
            assert entry["type"] == "counter"

    def test_increment_default_value_is_one(self, tmp_path):
        """increment() defaults to incrementing by 1."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.increment("test.counter")
        client.flush()

        metrics_file = tmp_path / "metrics.jsonl"
        with open(metrics_file) as f:
            entry = json.loads(f.readline())
            assert entry["value"] == 1


class TestJsonlTelemetryClientBuffering:
    """Buffering behavior tests."""

    def test_auto_flush_triggers_at_buffer_size(self, tmp_path):
        """Buffer flushes automatically when buffer_size reached."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=3, auto_flush=True)

        # Record 2 events - should not flush yet
        client.record_event("event1", {})
        client.record_event("event2", {})
        events_file = tmp_path / "events.jsonl"
        assert not events_file.exists()

        # Record 3rd event - should trigger flush
        client.record_event("event3", {})
        assert events_file.exists()

        with open(events_file) as f:
            lines = f.readlines()
            assert len(lines) == 3

    def test_manual_flush_writes_all_buffered_entries(self, tmp_path):
        """flush() writes all buffered events and metrics."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100)

        client.record_event("event1", {})
        client.record_event("event2", {})
        client.record_metric("metric1", 1, MetricType.COUNTER)

        # Nothing written yet
        events_file = tmp_path / "events.jsonl"
        metrics_file = tmp_path / "metrics.jsonl"
        assert not events_file.exists()
        assert not metrics_file.exists()

        # Flush writes everything
        client.flush()
        assert events_file.exists()
        assert metrics_file.exists()

        with open(events_file) as f:
            assert len(f.readlines()) == 2
        with open(metrics_file) as f:
            assert len(f.readlines()) == 1

    def test_close_flushes_remaining_data(self, tmp_path):
        """close() flushes before closing."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100)
        client.record_event("event", {"data": "test"})

        events_file = tmp_path / "events.jsonl"
        assert not events_file.exists()

        client.close()
        assert events_file.exists()


class TestJsonlTelemetryClientFileOperations:
    """File operation tests."""

    def test_creates_metrics_directory_if_missing(self, tmp_path):
        """Metrics directory is created on init."""
        metrics_dir = tmp_path / "nested" / "metrics"
        assert not metrics_dir.exists()

        client = JsonlTelemetryClient(metrics_dir=metrics_dir)
        assert metrics_dir.exists()

    def test_appends_to_existing_file(self, tmp_path):
        """New entries are appended, not overwritten."""
        # First client writes
        client1 = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client1.record_event("event1", {})
        client1.close()

        # Second client appends
        client2 = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client2.record_event("event2", {})
        client2.close()

        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            lines = f.readlines()
            assert len(lines) == 2
            assert json.loads(lines[0])["event"] == "event1"
            assert json.loads(lines[1])["event"] == "event2"

    def test_handles_directory_creation_failure(self, tmp_path):
        """Graceful handling when directory can't be created."""
        # Create a file where directory should be
        blocker = tmp_path / "blocked"
        blocker.write_text("I'm a file, not a directory")

        # Should not raise, just log warning
        client = JsonlTelemetryClient(metrics_dir=blocker / "metrics")
        # Client should still work, just won't write
        client.record_event("event", {})
        client.flush()


class TestJsonlTelemetryClientThreadSafety:
    """Thread safety tests."""

    def test_concurrent_writes_produce_valid_jsonl(self, tmp_path):
        """Multiple threads writing don't corrupt the file."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        num_threads = 10
        events_per_thread = 20

        def write_events(thread_id):
            for i in range(events_per_thread):
                client.record_event(f"thread_{thread_id}", {"index": i})

        threads = [
            threading.Thread(target=write_events, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        client.flush()

        # Verify all entries are valid JSON
        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            lines = f.readlines()
            # Should have all events (may have more if auto-flush triggered)
            assert len(lines) >= num_threads * events_per_thread

            for line in lines:
                # Each line should be valid JSON
                entry = json.loads(line)
                assert "event" in entry
                assert "timestamp" in entry

    def test_lock_prevents_interleaved_writes(self, tmp_path):
        """File locking ensures atomic appends."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=5)

        def writer():
            for _ in range(50):
                client.record_event("test", {"data": "x" * 100})

        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        client.flush()

        # Verify no corruption - each line should be complete JSON
        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            for line_num, line in enumerate(f, 1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {line_num} is not valid JSON: {e}")


class TestJsonlTelemetryClientContextManager:
    """Context manager tests."""

    def test_context_manager_flushes_on_exit(self, tmp_path):
        """Context manager calls close() on exit."""
        with JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=100) as client:
            client.record_event("event", {})

        # After exiting context, file should exist
        events_file = tmp_path / "events.jsonl"
        assert events_file.exists()


class TestJsonlTelemetryClientEdgeCases:
    """Edge case tests."""

    def test_empty_payload_is_valid(self, tmp_path):
        """Empty payload dict is acceptable."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("empty", {})
        client.flush()

        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            entry = json.loads(f.readline())
            assert entry["payload"] == {}

    def test_custom_session_id_is_used(self, tmp_path):
        """Custom session_id from constructor is included."""
        client = JsonlTelemetryClient(
            metrics_dir=tmp_path, session_id="my-custom-session", buffer_size=1
        )
        client.record_event("event", {})
        client.flush()

        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            entry = json.loads(f.readline())
            assert entry["session_id"] == "my-custom-session"

    def test_auto_generated_session_id(self, tmp_path):
        """Session ID is auto-generated if not provided."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        assert client.session_id is not None
        assert len(client.session_id) == 8  # UUID[:8]

    def test_env_var_metrics_dir_is_respected(self, tmp_path):
        """SUPERCLAUDE_METRICS_DIR env var sets directory."""
        custom_dir = tmp_path / "custom_metrics"
        with patch.dict(os.environ, {"SUPERCLAUDE_METRICS_DIR": str(custom_dir)}):
            client = JsonlTelemetryClient()
            assert client.metrics_dir == custom_dir

    def test_event_with_tags(self, tmp_path):
        """Events can include optional tags."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("tagged", {"data": 1}, tags={"env": "prod", "service": "api"})
        client.flush()

        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            entry = json.loads(f.readline())
            assert entry["tags"] == {"env": "prod", "service": "api"}

    def test_event_without_tags_has_no_tags_key(self, tmp_path):
        """Events without tags don't include tags key."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("untagged", {"data": 1})
        client.flush()

        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            entry = json.loads(f.readline())
            assert "tags" not in entry

    def test_timestamp_is_utc_iso_format(self, tmp_path):
        """Timestamps are in UTC ISO format."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)
        client.record_event("event", {})
        client.flush()

        events_file = tmp_path / "events.jsonl"
        with open(events_file) as f:
            entry = json.loads(f.readline())
            timestamp = entry["timestamp"]
            # Should contain timezone info (ends with +00:00 or Z)
            assert "+" in timestamp or timestamp.endswith("Z")

    def test_all_metric_types_supported(self, tmp_path):
        """All MetricType values can be recorded."""
        client = JsonlTelemetryClient(metrics_dir=tmp_path, buffer_size=1)

        for metric_type in MetricType:
            client.record_metric(f"test.{metric_type.value}", 1.0, metric_type)

        client.flush()

        metrics_file = tmp_path / "metrics.jsonl"
        with open(metrics_file) as f:
            lines = f.readlines()
            types_recorded = {json.loads(line)["type"] for line in lines}
            expected_types = {mt.value for mt in MetricType}
            assert types_recorded == expected_types
