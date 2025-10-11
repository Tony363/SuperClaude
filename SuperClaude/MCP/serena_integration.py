"""
Serena MCP Integration

Local, file-backed project memory and symbol storage to emulate Serena
capabilities without any external services.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from pathlib import Path
import json
import threading
from datetime import datetime


@dataclass
class SymbolInfo:
    name: str
    kind: str
    path: Optional[str] = None
    line: Optional[int] = None
    metadata: Dict[str, Any] = None


@dataclass
class SessionMemory:
    key: str
    value: Dict[str, Any]
    updated_at: str = datetime.now().isoformat()


class SerenaIntegration:
    """
    Simple local-memory Serena integration using a JSON file in ~/.claude.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        base_dir = Path(self.config.get("base_dir", Path.home() / ".claude"))
        self.storage = base_dir / "serena_memory.json"
        self._lock = threading.Lock()
        self._data = {"symbols": [], "memories": {}}

    def initialize(self):
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        if self.storage.exists():
            try:
                self._data = json.loads(self.storage.read_text(encoding="utf-8"))
            except Exception:
                # Corrupted file; reset
                self._data = {"symbols": [], "memories": {}}
        return True

    async def initialize_session(self):
        return True

    # Symbols API
    def add_symbol(self, symbol: SymbolInfo):
        with self._lock:
            self._data.setdefault("symbols", []).append(asdict(symbol))
            self._persist()

    def list_symbols(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        symbols = self._data.get("symbols", [])
        if kind:
            return [s for s in symbols if s.get("kind") == kind]
        return symbols

    # Session memory API
    def read_memory(self, key: str) -> Optional[Dict[str, Any]]:
        return self._data.get("memories", {}).get(key)

    def write_memory(self, key: str, value: Dict[str, Any]):
        with self._lock:
            value = {**value, "updated_at": datetime.now().isoformat()}
            self._data.setdefault("memories", {})[key] = value
            self._persist()

    def delete_memory(self, key: str):
        with self._lock:
            if key in self._data.get("memories", {}):
                del self._data["memories"][key]
                self._persist()

    def list_memories(self, prefix: Optional[str] = None) -> List[str]:
        keys = list(self._data.get("memories", {}).keys())
        if prefix:
            return [k for k in keys if k.startswith(prefix)]
        return keys

    # Internal
    def _persist(self):
        try:
            self.storage.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            pass
