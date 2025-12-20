"""Tests for the SQLite-backed evidence store."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from SuperClaude.Telemetry.evidence_store import (
    EvidenceRecord,
    EvidenceStore,
    QueryResult,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_evidence.db"
        yield db_path


@pytest.fixture
def store(temp_db):
    """Create an evidence store instance."""
    store = EvidenceStore(db_path=temp_db)
    yield store
    store.close()


class TestEvidenceStoreInit:
    """Test store initialization."""

    def test_creates_database(self, temp_db):
        """Database file should be created."""
        store = EvidenceStore(db_path=temp_db)
        assert temp_db.exists()
        store.close()

    def test_creates_default_path(self):
        """Uses default path when none specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_dir = Path(tmpdir) / ".superclaude_metrics"
            store = EvidenceStore(metrics_dir=metrics_dir)
            assert (metrics_dir / "evidence.db").exists()
            store.close()

    def test_schema_version_set(self, store):
        """Schema version should be recorded."""
        with store._cursor() as cursor:
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            assert row is not None
            assert row["version"] == EvidenceStore.SCHEMA_VERSION


class TestRecordOperations:
    """Test write operations."""

    def test_record_event(self, store):
        """Can record an event."""
        record_id = store.record_event(
            session_id="test-session-1",
            name="command_executed",
            payload={"command": "/sc:implement", "args": ["--loop", "3"]},
            tags={"agent": "python-expert"},
        )
        assert record_id > 0

    def test_record_metric(self, store):
        """Can record a metric."""
        record_id = store.record_metric(
            session_id="test-session-1",
            name="execution_time_ms",
            value=1234.5,
            metric_type="gauge",
            tags={"command": "implement"},
        )
        assert record_id > 0

    def test_record_validation(self, store):
        """Can record a validation result."""
        record_id = store.record_validation(
            session_id="test-session-1",
            stage_name="syntax",
            status="passed",
            findings=["All files parsed successfully"],
            metadata={"files_checked": 10},
        )
        assert record_id > 0

    def test_auto_timestamp(self, store):
        """Timestamp is auto-generated if not provided."""
        before = datetime.now(timezone.utc).isoformat()
        store.record_event(
            session_id="test-session",
            name="test_event",
            payload={},
        )
        after = datetime.now(timezone.utc).isoformat()

        result = store.query(session_id="test-session")
        assert len(result.records) == 1
        ts = result.records[0].timestamp
        assert before <= ts <= after

    def test_custom_timestamp(self, store):
        """Can specify custom timestamp."""
        custom_ts = "2024-01-15T10:30:00+00:00"
        store.record_event(
            session_id="test-session",
            name="test_event",
            payload={},
            timestamp=custom_ts,
        )

        result = store.query(session_id="test-session")
        assert result.records[0].timestamp == custom_ts


class TestQueryOperations:
    """Test query capabilities."""

    @pytest.fixture
    def populated_store(self, store):
        """Store with test data."""
        # Session 1: multiple events
        store.record_event("session-1", "start", {"mode": "normal"})
        store.record_event("session-1", "command_executed", {"cmd": "analyze"})
        store.record_metric("session-1", "duration_ms", 500, "gauge")
        store.record_validation("session-1", "syntax", "passed", [])

        # Session 2: different data
        store.record_event("session-2", "start", {"mode": "debug"})
        store.record_metric("session-2", "quality_score", 85.0, "gauge")

        return store

    def test_query_all(self, populated_store):
        """Query without filters returns all records."""
        result = populated_store.query()
        assert result.total_count == 6
        assert len(result.records) == 6

    def test_query_by_session(self, populated_store):
        """Filter by session_id."""
        result = populated_store.query(session_id="session-1")
        assert result.total_count == 4
        for record in result.records:
            assert record.session_id == "session-1"

    def test_query_by_type(self, populated_store):
        """Filter by record type."""
        result = populated_store.query(record_type="event")
        assert result.total_count == 3

        result = populated_store.query(record_type="metric")
        assert result.total_count == 2

        result = populated_store.query(record_type="validation")
        assert result.total_count == 1

    def test_query_by_name(self, populated_store):
        """Filter by exact name."""
        result = populated_store.query(name="start")
        assert result.total_count == 2

    def test_query_by_name_pattern(self, populated_store):
        """Filter by name pattern."""
        result = populated_store.query(name_pattern="%score%")
        assert result.total_count == 1
        assert result.records[0].name == "quality_score"

    def test_query_combined_filters(self, populated_store):
        """Multiple filters combined with AND."""
        result = populated_store.query(
            session_id="session-1",
            record_type="event",
        )
        assert result.total_count == 2

    def test_query_pagination(self, populated_store):
        """Limit and offset work correctly."""
        result = populated_store.query(limit=2, offset=0)
        assert len(result.records) == 2
        assert result.total_count == 6

        result = populated_store.query(limit=2, offset=2)
        assert len(result.records) == 2

    def test_query_time_tracking(self, populated_store):
        """Query time is measured."""
        result = populated_store.query()
        assert result.query_time_ms > 0

    def test_query_result_structure(self, populated_store):
        """QueryResult has correct structure."""
        result = populated_store.query(session_id="session-1", limit=1)
        assert isinstance(result, QueryResult)
        assert isinstance(result.records, list)
        assert isinstance(result.total_count, int)
        assert isinstance(result.query_time_ms, float)

    def test_evidence_record_structure(self, populated_store):
        """EvidenceRecord has correct fields."""
        result = populated_store.query(name="start", limit=1)
        record = result.records[0]
        assert isinstance(record, EvidenceRecord)
        assert isinstance(record.id, int)
        assert isinstance(record.session_id, str)
        assert isinstance(record.timestamp, str)
        assert isinstance(record.record_type, str)
        assert isinstance(record.name, str)
        assert isinstance(record.payload, dict)


class TestSessionManagement:
    """Test session-level operations."""

    def test_get_sessions(self, store):
        """Get session summaries."""
        store.record_event("session-a", "event1", {})
        store.record_event("session-a", "event2", {})
        store.record_metric("session-a", "metric1", 100, "counter")
        store.record_event("session-b", "event1", {})

        sessions = store.get_sessions()
        assert len(sessions) == 2

        # Check session-a stats
        session_a = next(s for s in sessions if s["session_id"] == "session-a")
        assert session_a["total_records"] == 3
        assert session_a["event_count"] == 2
        assert session_a["metric_count"] == 1

    def test_delete_session(self, store):
        """Delete all records for a session."""
        store.record_event("delete-me", "event", {})
        store.record_event("delete-me", "event2", {})
        store.record_event("keep-me", "event", {})

        deleted = store.delete_session("delete-me")
        assert deleted == 2

        result = store.query(session_id="delete-me")
        assert result.total_count == 0

        result = store.query(session_id="keep-me")
        assert result.total_count == 1


class TestValidationSummary:
    """Test validation-specific queries."""

    def test_get_validation_summary(self, store):
        """Aggregate validation results for session."""
        store.record_validation("session-1", "syntax", "passed", [])
        store.record_validation("session-1", "security", "passed", [])
        store.record_validation("session-1", "tests", "failed", ["2 tests failed"])
        store.record_validation("session-1", "style", "degraded", ["Minor issues"])

        summary = store.get_validation_summary("session-1")
        assert summary["session_id"] == "session-1"
        assert len(summary["stages"]) == 4
        assert summary["summary"]["passed"] == 2
        assert summary["summary"]["failed"] == 1
        assert summary["summary"]["degraded"] == 1
        assert summary["summary"]["success_rate"] == 0.5


class TestQualityHistory:
    """Test quality tracking queries."""

    def test_get_quality_history(self, store):
        """Retrieve quality scores over time."""
        store.record_metric("s1", "quality_score", 75.0, "gauge")
        store.record_metric("s1", "overall_quality", 80.0, "gauge")
        store.record_metric("s1", "execution_time", 100, "gauge")  # Not quality

        history = store.get_quality_history()
        assert len(history) == 2  # Only quality-related metrics

        names = [h["name"] for h in history]
        assert "quality_score" in names
        assert "overall_quality" in names


class TestJSONLImport:
    """Test JSONL import functionality."""

    def test_import_jsonl(self, store, temp_db):
        """Import events from JSONL file."""
        jsonl_file = temp_db.parent / "events.jsonl"
        events = [
            {
                "session_id": "import-1",
                "event": "start",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {"session_id": "import-1", "event": "end", "payload": {"status": "ok"}},
        ]
        with open(jsonl_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        count = store.import_jsonl(jsonl_file, record_type="event")
        assert count == 2

        result = store.query(session_id="import-1")
        assert result.total_count == 2

    def test_import_handles_invalid_json(self, store, temp_db):
        """Skips invalid JSON lines gracefully."""
        jsonl_file = temp_db.parent / "events.jsonl"
        with open(jsonl_file, "w") as f:
            f.write('{"session_id": "valid", "event": "test"}\n')
            f.write("not valid json\n")
            f.write('{"session_id": "valid2", "event": "test2"}\n')

        count = store.import_jsonl(jsonl_file)
        assert count == 2  # Only valid lines imported

    def test_import_nonexistent_file(self, store):
        """Returns 0 for non-existent file."""
        count = store.import_jsonl(Path("/nonexistent/file.jsonl"))
        assert count == 0


class TestCleanup:
    """Test cleanup operations."""

    def test_delete_before_timestamp(self, store):
        """Delete records before a timestamp."""
        store.record_event("s1", "old", {}, timestamp="2024-01-01T00:00:00Z")
        store.record_event("s1", "new", {}, timestamp="2024-06-01T00:00:00Z")

        deleted = store.delete_before("2024-03-01T00:00:00Z")
        assert deleted == 1

        result = store.query()
        assert result.total_count == 1
        assert result.records[0].name == "new"

    def test_vacuum(self, store):
        """Vacuum doesn't raise."""
        store.record_event("s1", "event", {})
        store.delete_session("s1")
        store.vacuum()  # Should not raise


class TestThreadSafety:
    """Test concurrent access."""

    def test_thread_local_connections(self, temp_db):
        """Each thread gets its own connection."""
        import threading

        store = EvidenceStore(db_path=temp_db)
        results = []

        def worker(session_id):
            for i in range(10):
                store.record_event(session_id, f"event-{i}", {"thread": session_id})
            results.append(session_id)

        threads = [
            threading.Thread(target=worker, args=(f"thread-{i}",)) for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        store.close()

        # Verify all records were written
        store2 = EvidenceStore(db_path=temp_db)
        result = store2.query(limit=1000)
        assert result.total_count == 50  # 5 threads * 10 events
        store2.close()
