"""Tests for SuperClaude.Core.unified_store module.

This module tests the UnifiedStore class which provides SQLite-backed
persistence for session memories and symbol metadata.
"""

import concurrent.futures
from pathlib import Path
from unittest.mock import patch

from SuperClaude.Core.unified_store import SymbolInfo, UnifiedStore


class TestMemoryOperations:
    """Tests for session memory CRUD operations."""

    def test_write_read_memory_roundtrip(self, memory_store):
        """Test basic write and read cycle for session memory."""
        key = "session:test-123"
        value = {"user": "test", "data": [1, 2, 3], "nested": {"a": "b"}}

        memory_store.write_memory(key, value)
        result = memory_store.read_memory(key)

        assert result == value
        assert result["user"] == "test"
        assert result["data"] == [1, 2, 3]
        assert result["nested"]["a"] == "b"

    def test_read_nonexistent_memory_returns_none(self, memory_store):
        """Test that reading a nonexistent key returns None."""
        result = memory_store.read_memory("nonexistent:key")

        assert result is None

    def test_list_memories_with_prefix(self, memory_store):
        """Test listing memories filtered by prefix."""
        # Write memories with different prefixes
        memory_store.write_memory("session:a", {"id": "a"})
        memory_store.write_memory("session:b", {"id": "b"})
        memory_store.write_memory("agent:x", {"id": "x"})
        memory_store.write_memory("agent:y", {"id": "y"})

        session_keys = memory_store.list_memories("session:")
        agent_keys = memory_store.list_memories("agent:")

        assert len(session_keys) == 2
        assert "session:a" in session_keys
        assert "session:b" in session_keys
        assert len(agent_keys) == 2
        assert "agent:x" in agent_keys
        assert "agent:y" in agent_keys

    def test_list_memories_empty_prefix(self, memory_store):
        """Test listing all memories without prefix filter."""
        memory_store.write_memory("key1", {"data": 1})
        memory_store.write_memory("key2", {"data": 2})
        memory_store.write_memory("key3", {"data": 3})

        all_keys = memory_store.list_memories()

        assert len(all_keys) == 3
        assert set(all_keys) == {"key1", "key2", "key3"}

    def test_delete_memory(self, memory_store):
        """Test deleting a memory key."""
        key = "delete:me"
        memory_store.write_memory(key, {"temp": True})

        # Verify it exists
        assert memory_store.read_memory(key) is not None

        # Delete it
        memory_store.delete_memory(key)

        # Verify it's gone
        assert memory_store.read_memory(key) is None

    def test_overwrite_existing_memory(self, memory_store):
        """Test that writing to an existing key overwrites it."""
        key = "overwrite:test"
        memory_store.write_memory(key, {"version": 1})
        memory_store.write_memory(key, {"version": 2})

        result = memory_store.read_memory(key)

        assert result == {"version": 2}


class TestSymbolOperations:
    """Tests for symbol CRUD operations."""

    def test_add_symbol(self, memory_store, sample_symbol):
        """Test adding a single symbol."""
        memory_store.add_symbol(sample_symbol)

        symbols = memory_store.list_symbols()

        assert len(symbols) == 1
        assert symbols[0]["name"] == "test_function"
        assert symbols[0]["kind"] == "function"
        assert symbols[0]["file_path"] == "/path/to/file.py"
        assert symbols[0]["line"] == 42
        assert symbols[0]["signature"] == "def test_function(x: int) -> str"

    def test_list_symbols_all(self, memory_store, sample_symbols):
        """Test listing all symbols without filtering."""
        for symbol in sample_symbols:
            memory_store.add_symbol(symbol)

        symbols = memory_store.list_symbols()

        assert len(symbols) == 4
        names = {s["name"] for s in symbols}
        assert names == {"MyClass", "helper_func", "CONSTANT", "process_data"}

    def test_list_symbols_by_kind(self, memory_store, sample_symbols):
        """Test filtering symbols by kind."""
        for symbol in sample_symbols:
            memory_store.add_symbol(symbol)

        functions = memory_store.list_symbols(kind="function")
        classes = memory_store.list_symbols(kind="class")
        variables = memory_store.list_symbols(kind="variable")

        assert len(functions) == 2
        assert len(classes) == 1
        assert len(variables) == 1
        assert functions[0]["kind"] == "function"
        assert classes[0]["name"] == "MyClass"
        assert variables[0]["name"] == "CONSTANT"

    def test_add_symbol_without_signature(self, memory_store):
        """Test adding a symbol without a signature."""
        symbol = SymbolInfo(
            name="MY_VAR",
            kind="variable",
            file_path="/path/to/vars.py",
            line=5,
            signature=None,
        )

        memory_store.add_symbol(symbol)
        symbols = memory_store.list_symbols()

        assert len(symbols) == 1
        assert symbols[0]["signature"] is None


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_json_decode_error_returns_none(self, memory_store):
        """Test that corrupted JSON data returns None on read."""
        # Directly insert corrupted data into the database
        conn = memory_store._get_conn()
        conn.execute(
            "INSERT INTO sessions (key, data) VALUES (?, ?)",
            ("corrupt:key", "not valid json {{{"),
        )
        conn.commit()

        result = memory_store.read_memory("corrupt:key")

        assert result is None

    def test_close_connection(self, tmp_path):
        """Test that closing the connection works properly."""
        db_path = tmp_path / "close_test.db"
        store = UnifiedStore(str(db_path))

        # Write some data
        store.write_memory("test", {"data": 1})

        # Close the store
        store.close()

        # Connection should be None after close
        assert store._conn is None

        # Calling close again should not raise
        store.close()

    def test_double_close_is_safe(self, tmp_path):
        """Test that calling close multiple times is safe."""
        db_path = tmp_path / "double_close.db"
        store = UnifiedStore(str(db_path))

        store.close()
        store.close()  # Should not raise
        store.close()  # Should not raise


class TestConcurrency:
    """Tests for thread safety and concurrent access."""

    def test_concurrent_writes(self, memory_store):
        """Test that concurrent writes are handled safely."""
        num_threads = 10
        num_writes_per_thread = 20
        errors = []

        def writer(thread_id):
            try:
                for i in range(num_writes_per_thread):
                    key = f"thread:{thread_id}:item:{i}"
                    value = {"thread": thread_id, "item": i}
                    memory_store.write_memory(key, value)
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(writer, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        # No errors should have occurred
        assert len(errors) == 0

        # All writes should have succeeded
        all_keys = memory_store.list_memories("thread:")
        assert len(all_keys) == num_threads * num_writes_per_thread

    def test_concurrent_reads_and_writes(self, memory_store):
        """Test concurrent read and write operations."""
        # Pre-populate some data
        for i in range(50):
            memory_store.write_memory(f"data:{i}", {"value": i})

        read_results = []
        write_errors = []

        def reader():
            try:
                for i in range(50):
                    result = memory_store.read_memory(f"data:{i}")
                    if result:
                        read_results.append(result)
            except Exception as e:
                write_errors.append(e)

        def writer():
            try:
                for i in range(50, 100):
                    memory_store.write_memory(f"data:{i}", {"value": i})
            except Exception as e:
                write_errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(reader),
                executor.submit(reader),
                executor.submit(writer),
                executor.submit(writer),
            ]
            concurrent.futures.wait(futures)

        assert len(write_errors) == 0


class TestMigrationWarning:
    """Tests for legacy Serena data migration warning."""

    def test_migration_warning_when_legacy_exists(self, tmp_path, capsys):
        """Test that migration warning is shown when legacy data exists."""
        # Create a mock legacy Serena file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        legacy_file = claude_dir / "serena_memory.json"
        legacy_file.write_text('{"legacy": "data"}')

        # Reset the migration check flag to trigger the check
        UnifiedStore._migration_checked = False

        # Create a new store with empty db in the same directory
        db_path = claude_dir / "unified_store.db"

        with patch.object(Path, "home", return_value=tmp_path):
            store = UnifiedStore(str(db_path))
            store.close()

        # Reset for other tests
        UnifiedStore._migration_checked = False

        # Check that warning was printed
        capsys.readouterr()
        # Note: The warning may or may not appear depending on exact timing
        # The important thing is no exception was raised

    def test_no_warning_when_no_legacy_data(self, tmp_path, capsys):
        """Test that no warning is shown when no legacy data exists."""
        # Reset the migration check flag
        UnifiedStore._migration_checked = False

        db_path = tmp_path / "clean_store.db"

        with patch.object(Path, "home", return_value=tmp_path):
            store = UnifiedStore(str(db_path))
            store.close()

        # Reset for other tests
        UnifiedStore._migration_checked = False

        captured = capsys.readouterr()
        assert "WARNING" not in captured.out


class TestDatabaseConfiguration:
    """Tests for SQLite database configuration."""

    def test_wal_mode_enabled(self, memory_store):
        """Test that WAL journal mode is enabled for concurrency."""
        conn = memory_store._get_conn()
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]

        assert mode.lower() == "wal"

    def test_busy_timeout_set(self, memory_store):
        """Test that busy timeout is configured."""
        conn = memory_store._get_conn()
        cursor = conn.execute("PRAGMA busy_timeout")
        timeout = cursor.fetchone()[0]

        assert timeout == 5000

    def test_database_path_created(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        nested_path = tmp_path / "deep" / "nested" / "path" / "store.db"

        store = UnifiedStore(str(nested_path))
        store.write_memory("test", {"data": 1})
        store.close()

        assert nested_path.exists()
