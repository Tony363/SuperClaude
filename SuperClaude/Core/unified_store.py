"""
UnifiedStore provides local persistence for SuperClaude.

Replaces the legacy Serena integration by offering a simple SQLite-backed
store for session memories and symbol metadata. The store is intentionally
lightweight, thread-safe, and safe for concurrent access across processes.
"""

from __future__ import annotations

import atexit
import json
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SymbolInfo:
    """Simple representation of a code symbol persisted by the UnifiedStore."""

    name: str
    kind: str
    file_path: str
    line: int
    signature: Optional[str] = None


class UnifiedStore:
    """
    SQLite-backed persistence for session memories and symbols.

    The store mirrors the public interface previously provided by the Serena
    integration so that existing call-sites can migrate with minimal change.
    """

    _migration_checked: bool = False

    def __init__(self, db_path: str = "~/.claude/unified_store.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

        if not UnifiedStore._migration_checked:
            self._check_migration()
            UnifiedStore._migration_checked = True

        self._init_db()
        atexit.register(self.close)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _check_migration(self) -> None:
        """
        Warn if legacy Serena data still exists and the new database is absent.

        The warning nudges the user to run the migration script before the old
        JSON file is removed by subsequent clean-up tasks.
        """
        serena_file = Path.home() / ".claude" / "serena_memory.json"
        if not serena_file.exists():
            return

        db_missing = not self.db_path.exists() or self.db_path.stat().st_size == 0
        if db_missing:
            print(
                "WARNING: Found legacy Serena data but unified_store.db is empty.\n"
                "Run `python -m SuperClaude.Core.migrate_serena_data` to migrate "
                "session history before removing Serena."
            )

    def _get_conn(self) -> sqlite3.Connection:
        """Return a shared SQLite connection configured for concurrency."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None,
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
        return self._conn

    def _init_db(self) -> None:
        """Ensure schema exists."""
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                key TEXT PRIMARY KEY,
                data TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                file_path TEXT NOT NULL,
                line INTEGER NOT NULL,
                signature TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

    # ------------------------------------------------------------------ #
    # Session memory API
    # ------------------------------------------------------------------ #
    def write_memory(self, key: str, value: Dict[str, Any]) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO sessions (key, data) VALUES (?, ?)",
                (key, json.dumps(value)),
            )
            conn.commit()

    def read_memory(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("SELECT data FROM sessions WHERE key = ?", (key,))
            row = cursor.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    def list_memories(self, prefix: str = "") -> List[str]:
        with self._lock:
            conn = self._get_conn()
            if prefix:
                cursor = conn.execute(
                    "SELECT key FROM sessions WHERE key LIKE ?",
                    (f"{prefix}%",),
                )
            else:
                cursor = conn.execute("SELECT key FROM sessions")
            rows = cursor.fetchall()
        return [row[0] for row in rows]

    def delete_memory(self, key: str) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM sessions WHERE key = ?", (key,))
            conn.commit()

    # ------------------------------------------------------------------ #
    # Symbol API
    # ------------------------------------------------------------------ #
    def add_symbol(self, symbol: SymbolInfo) -> None:
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """
                INSERT INTO symbols (name, kind, file_path, line, signature)
                VALUES (?, ?, ?, ?, ?)
                """,
                (symbol.name, symbol.kind, symbol.file_path, symbol.line, symbol.signature),
            )
            conn.commit()

    def list_symbols(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_conn()
            if kind:
                cursor = conn.execute("SELECT * FROM symbols WHERE kind = ?", (kind,))
            else:
                cursor = conn.execute("SELECT * FROM symbols")
            rows = cursor.fetchall()
        return [
            {
                "name": row[1],
                "kind": row[2],
                "file_path": row[3],
                "line": row[4],
                "signature": row[5],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __del__(self) -> None:
        self.close()
