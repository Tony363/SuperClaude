#!/usr/bin/env python3
"""
One-time migration helper that copies legacy Serena data into UnifiedStore.

Run this script before removing Serena integrations to ensure existing
session memories and symbols are preserved inside the new SQLite-backed
store located at ~/.claude/unified_store.db.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from SuperClaude.Core.unified_store import SymbolInfo, UnifiedStore


def migrate_serena_data() -> bool:
    """
    Copy entries from serena_memory.json into the UnifiedStore database.

    Returns:
        bool: True if migration succeeded or no data was found. False on error.
    """
    serena_file = Path.home() / ".claude" / "serena_memory.json"
    if not serena_file.exists():
        print("No serena_memory.json found – skipping migration.")
        return True

    print(f"Migrating Serena data from {serena_file}")
    store = UnifiedStore()

    try:
        content = serena_file.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(content)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Failed to read Serena data: {exc}")
        store.close()
        return False

    # Restore memories
    memories = data.get("memories", {}) or {}
    for key, value in memories.items():
        store.write_memory(key, value)
        print(f"  Migrated memory key: {key}")

    # Restore symbols
    symbols = data.get("symbols", []) or []
    for symbol_data in symbols:
        symbol = SymbolInfo(
            name=symbol_data.get("name", ""),
            kind=symbol_data.get("kind", ""),
            file_path=symbol_data.get("path")
            or symbol_data.get("file_path", ""),
            line=symbol_data.get("line", 0),
            signature=symbol_data.get("signature"),
        )
        store.add_symbol(symbol)
    if symbols:
        print(f"  Migrated {len(symbols)} symbols")

    store.close()

    # Backup original JSON file for safety.
    backup_path = serena_file.with_suffix(".json.backup")
    try:
        serena_file.rename(backup_path)
        print(f"Legacy file backed up to {backup_path}")
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Warning: unable to rename legacy file ({exc}).")

    print("Migration completed successfully.")
    return True


if __name__ == "__main__":
    migrate_serena_data()
