from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class SQLiteMetricsSink:
    """SQLite sink for metrics, snapshots and alerts.

    Writes append-only event rows into a lightweight local database.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            base = Path.cwd() / ".superclaude_metrics"
            base.mkdir(parents=True, exist_ok=True)
            db_path = base / "metrics.db"
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def write_event(self, event: Dict[str, Any]) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                ts = event.get('data', {}).get('timestamp') or event.get('data', {}).get('time') or event.get('data', {}).get('timestamp_ms') or ''
                c.execute(
                    "INSERT INTO events (type, ts, data) VALUES (?,?,?)",
                    (event.get('type', 'metric'), str(ts), json.dumps(event, ensure_ascii=False))
                )
                conn.commit()
        except Exception:
            logger.debug(
                "Failed to write metrics event to SQLite at %s",
                self.db_path,
                exc_info=True,
            )
