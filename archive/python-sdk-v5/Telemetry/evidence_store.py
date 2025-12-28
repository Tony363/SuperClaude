"""
SQLite-backed evidence store for SuperClaude telemetry.

Provides queryable storage for events, metrics, and validation evidence,
addressing the "write-only logging" gap identified in the consensus analysis.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvidenceRecord:
    """A single evidence record."""

    id: int
    session_id: str
    timestamp: str
    record_type: str  # 'event', 'metric', 'validation'
    name: str
    payload: dict[str, Any]
    tags: dict[str, str] | None = None


@dataclass
class QueryResult:
    """Result of an evidence query."""

    records: list[EvidenceRecord]
    total_count: int
    query_time_ms: float


class EvidenceStore:
    """
    SQLite-backed store for telemetry evidence with query capabilities.

    Features:
    - Queryable event/metric storage
    - Session-based filtering
    - Time-range queries
    - Aggregation support
    - Thread-safe operations
    - JSONL import support
    """

    SCHEMA_VERSION = 1

    CREATE_TABLES_SQL = """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );

    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        record_type TEXT NOT NULL,  -- 'event', 'metric', 'validation'
        name TEXT NOT NULL,
        payload TEXT NOT NULL,  -- JSON
        tags TEXT,  -- JSON or NULL
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_evidence_session ON evidence(session_id);
    CREATE INDEX IF NOT EXISTS idx_evidence_type ON evidence(record_type);
    CREATE INDEX IF NOT EXISTS idx_evidence_name ON evidence(name);
    CREATE INDEX IF NOT EXISTS idx_evidence_timestamp ON evidence(timestamp);
    CREATE INDEX IF NOT EXISTS idx_evidence_session_type ON evidence(session_id, record_type);
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        metrics_dir: str | Path | None = None,
    ):
        """
        Initialize the evidence store.

        Args:
            db_path: Path to SQLite database (default: .superclaude_metrics/evidence.db)
            metrics_dir: Directory for metrics files (for JSONL import)
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            base_dir = Path(metrics_dir or ".superclaude_metrics")
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = base_dir / "evidence.db"

        self.metrics_dir = Path(metrics_dir) if metrics_dir else self.db_path.parent
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        """Context manager for database cursor with auto-commit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._cursor() as cursor:
            cursor.executescript(self.CREATE_TABLES_SQL)

            # Check/set schema version
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )

    # ------------------------------------------------------------------
    # Write Operations
    # ------------------------------------------------------------------

    def record_event(
        self,
        session_id: str,
        name: str,
        payload: dict[str, Any],
        timestamp: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> int:
        """
        Record an event.

        Returns the record ID.
        """
        return self._insert_record(
            session_id=session_id,
            record_type="event",
            name=name,
            payload=payload,
            timestamp=timestamp,
            tags=tags,
        )

    def record_metric(
        self,
        session_id: str,
        name: str,
        value: float | int,
        metric_type: str,
        timestamp: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> int:
        """
        Record a metric.

        Returns the record ID.
        """
        payload = {"value": value, "type": metric_type}
        return self._insert_record(
            session_id=session_id,
            record_type="metric",
            name=name,
            payload=payload,
            timestamp=timestamp,
            tags=tags,
        )

    def record_validation(
        self,
        session_id: str,
        stage_name: str,
        status: str,
        findings: list[str],
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> int:
        """
        Record a validation result.

        Returns the record ID.
        """
        payload = {
            "status": status,
            "findings": findings,
            "metadata": metadata or {},
        }
        return self._insert_record(
            session_id=session_id,
            record_type="validation",
            name=stage_name,
            payload=payload,
            timestamp=timestamp,
        )

    def _insert_record(
        self,
        session_id: str,
        record_type: str,
        name: str,
        payload: dict[str, Any],
        timestamp: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> int:
        """Insert a record and return its ID."""
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO evidence (session_id, timestamp, record_type, name, payload, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    timestamp,
                    record_type,
                    name,
                    json.dumps(payload),
                    json.dumps(tags) if tags else None,
                ),
            )
            return cursor.lastrowid or 0

    # ------------------------------------------------------------------
    # Query Operations
    # ------------------------------------------------------------------

    def query(
        self,
        session_id: str | None = None,
        record_type: str | None = None,
        name: str | None = None,
        name_pattern: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        tags: dict[str, str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> QueryResult:
        """
        Query evidence records with filters.

        Args:
            session_id: Filter by session
            record_type: Filter by type ('event', 'metric', 'validation')
            name: Exact name match
            name_pattern: SQL LIKE pattern for name
            start_time: ISO timestamp lower bound
            end_time: ISO timestamp upper bound
            tags: Filter by tag key-value pairs
            limit: Maximum records to return
            offset: Pagination offset

        Returns:
            QueryResult with matching records and metadata
        """
        import time

        start = time.perf_counter()

        conditions = []
        params: list[Any] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        if record_type:
            conditions.append("record_type = ?")
            params.append(record_type)

        if name:
            conditions.append("name = ?")
            params.append(name)

        if name_pattern:
            conditions.append("name LIKE ?")
            params.append(name_pattern)

        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)

        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self._cursor() as cursor:
            # Get total count
            # SECURITY: where_clause only contains hardcoded SQL fragments; user values in params
            cursor.execute(
                f"SELECT COUNT(*) FROM evidence WHERE {where_clause}",  # noqa: S608
                params,
            )
            total_count = cursor.fetchone()[0]

            # Get records
            cursor.execute(
                f"""
                SELECT id, session_id, timestamp, record_type, name, payload, tags
                FROM evidence
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
                """,  # noqa: S608
                params + [limit, offset],
            )

            records = []
            for row in cursor.fetchall():
                payload = json.loads(row["payload"])
                tags_data = json.loads(row["tags"]) if row["tags"] else None

                # Filter by tags if specified
                if tags:
                    if not tags_data:
                        continue
                    if not all(tags_data.get(k) == v for k, v in tags.items()):
                        continue

                records.append(
                    EvidenceRecord(
                        id=row["id"],
                        session_id=row["session_id"],
                        timestamp=row["timestamp"],
                        record_type=row["record_type"],
                        name=row["name"],
                        payload=payload,
                        tags=tags_data,
                    )
                )

        query_time = (time.perf_counter() - start) * 1000

        return QueryResult(
            records=records,
            total_count=total_count,
            query_time_ms=query_time,
        )

    def get_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get recent sessions with summary statistics.

        Returns list of session summaries with event/metric counts.
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    session_id,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen,
                    COUNT(*) as total_records,
                    SUM(CASE WHEN record_type = 'event' THEN 1 ELSE 0 END) as event_count,
                    SUM(CASE WHEN record_type = 'metric' THEN 1 ELSE 0 END) as metric_count,
                    SUM(CASE WHEN record_type = 'validation' THEN 1 ELSE 0 END) as validation_count
                FROM evidence
                GROUP BY session_id
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (limit,),
            )

            return [
                {
                    "session_id": row["session_id"],
                    "first_seen": row["first_seen"],
                    "last_seen": row["last_seen"],
                    "total_records": row["total_records"],
                    "event_count": row["event_count"],
                    "metric_count": row["metric_count"],
                    "validation_count": row["validation_count"],
                }
                for row in cursor.fetchall()
            ]

    def get_quality_history(
        self,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get quality assessment history.

        Returns quality scores over time.
        """
        conditions = ["name LIKE '%quality%' OR name LIKE '%score%'"]
        params: list[Any] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)

        where_clause = " AND ".join(conditions)

        with self._cursor() as cursor:
            # SECURITY: where_clause only contains hardcoded SQL fragments; user values in params
            cursor.execute(
                f"""
                SELECT session_id, timestamp, name, payload
                FROM evidence
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
                """,  # noqa: S608
                params + [limit],
            )

            return [
                {
                    "session_id": row["session_id"],
                    "timestamp": row["timestamp"],
                    "name": row["name"],
                    "payload": json.loads(row["payload"]),
                }
                for row in cursor.fetchall()
            ]

    def get_validation_summary(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Get validation summary for a session.

        Returns aggregated validation results.
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT name, payload
                FROM evidence
                WHERE session_id = ? AND record_type = 'validation'
                ORDER BY timestamp DESC
                """,
                (session_id,),
            )

            stages = {}
            for row in cursor.fetchall():
                name = row["name"]
                payload = json.loads(row["payload"])
                if name not in stages:
                    stages[name] = payload

            # Compute summary
            passed = sum(1 for s in stages.values() if s.get("status") == "passed")
            failed = sum(1 for s in stages.values() if s.get("status") == "failed")
            degraded = sum(1 for s in stages.values() if s.get("status") == "degraded")

            return {
                "session_id": session_id,
                "stages": stages,
                "summary": {
                    "total": len(stages),
                    "passed": passed,
                    "failed": failed,
                    "degraded": degraded,
                    "success_rate": passed / len(stages) if stages else 0,
                },
            }

    # ------------------------------------------------------------------
    # Import Operations
    # ------------------------------------------------------------------

    def import_jsonl(
        self,
        filepath: Path | None = None,
        record_type: str = "event",
    ) -> int:
        """
        Import records from a JSONL file.

        Args:
            filepath: Path to JSONL file (default: events.jsonl in metrics_dir)
            record_type: Type to assign to imported records

        Returns:
            Number of records imported
        """
        if not filepath:
            if record_type == "event":
                filepath = self.metrics_dir / "events.jsonl"
            else:
                filepath = self.metrics_dir / "metrics.jsonl"

        if not filepath.exists():
            return 0

        count = 0
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    self._insert_record(
                        session_id=data.get("session_id", "unknown"),
                        record_type=record_type,
                        name=data.get("event") or data.get("metric", "unknown"),
                        payload=data.get("payload", data),
                        timestamp=data.get("timestamp"),
                        tags=data.get("tags"),
                    )
                    count += 1
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON line: {line[:50]}...")
                except Exception as e:
                    logger.warning(f"Error importing record: {e}")

        return count

    def import_all_jsonl(self) -> dict[str, int]:
        """
        Import all JSONL files from metrics directory.

        Returns dict with counts per file type.
        """
        results = {}

        events_file = self.metrics_dir / "events.jsonl"
        if events_file.exists():
            results["events"] = self.import_jsonl(events_file, "event")

        metrics_file = self.metrics_dir / "metrics.jsonl"
        if metrics_file.exists():
            results["metrics"] = self.import_jsonl(metrics_file, "metric")

        return results

    # ------------------------------------------------------------------
    # Cleanup Operations
    # ------------------------------------------------------------------

    def delete_session(self, session_id: str) -> int:
        """Delete all records for a session. Returns count deleted."""
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM evidence WHERE session_id = ?",
                (session_id,),
            )
            return cursor.rowcount

    def delete_before(self, timestamp: str) -> int:
        """Delete all records before a timestamp. Returns count deleted."""
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM evidence WHERE timestamp < ?",
                (timestamp,),
            )
            return cursor.rowcount

    def vacuum(self) -> None:
        """Reclaim space from deleted records."""
        conn = self._get_connection()
        conn.execute("VACUUM")

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            del self._local.connection
