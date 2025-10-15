"""
Serena MCP Integration

Local, file-backed project memory and symbol storage to emulate Serena
capabilities without any external services.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import subprocess
import threading


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
        self.max_age_days = int(self.config.get("max_age_days", 30))
        self.repo_root = self._detect_repo_root()

    def initialize(self):
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        if self.storage.exists():
            try:
                self._data = json.loads(self.storage.read_text(encoding="utf-8"))
            except Exception:
                # Corrupted file; reset
                self._data = {"symbols": [], "memories": {}}
        self._prune_stale_memories()
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
        memory = self._data.get("memories", {}).get(key)
        if not memory:
            return None

        if self._is_stale(memory):
            self.delete_memory(key)
            return None

        if not self._validate_memory_schema(memory):
            self.delete_memory(key)
            return None

        if not self._validate_memory_references(memory):
            self.delete_memory(key)
            return None

        current_commit = self._current_commit()
        if current_commit and memory.get("commit_sha") and memory["commit_sha"] != current_commit:
            memory = dict(memory)
            memory["stale"] = True

        return memory

    def write_memory(self, key: str, value: Dict[str, Any]):
        with self._lock:
            sanitized = self._sanitize_memory_payload(key, value)
            sanitized["updated_at"] = datetime.now().isoformat()
            sanitized["commit_sha"] = self._current_commit()
            sanitized.setdefault("schema_version", 1)
            self._data.setdefault("memories", {})[key] = sanitized
            self._persist()
        self._prune_stale_memories()

    def delete_memory(self, key: str):
        with self._lock:
            if key in self._data.get("memories", {}):
                del self._data["memories"][key]
                self._persist()

    def list_memories(self, prefix: Optional[str] = None) -> List[str]:
        self._prune_stale_memories()
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

    def _sanitize_memory_payload(self, key: str, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {"payload": value, "key": key}
        sanitized = dict(value)
        sanitized["key"] = sanitized.get("key", key)
        return sanitized

    def _is_stale(self, memory: Dict[str, Any]) -> bool:
        if self.max_age_days <= 0:
            return False
        updated_at = memory.get("updated_at")
        if not updated_at:
            return False
        try:
            timestamp = datetime.fromisoformat(updated_at)
        except ValueError:
            return True
        return timestamp < datetime.now() - timedelta(days=self.max_age_days)

    def _prune_stale_memories(self) -> None:
        if not self._data.get("memories"):
            return
        keys_to_remove = []
        for key, memory in self._data["memories"].items():
            if self._is_stale(memory) or not self._validate_memory_schema(memory):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._data["memories"][key]
        if keys_to_remove:
            self._persist()

    def _validate_memory_schema(self, memory: Dict[str, Any]) -> bool:
        if not isinstance(memory, dict):
            return False
        required = {"key"}
        return required.issubset(memory.keys())

    def _validate_memory_references(self, memory: Dict[str, Any]) -> bool:
        paths = memory.get("paths") or memory.get("files")
        if not paths:
            return True
        base = self.repo_root or Path.cwd()
        for path in paths:
            candidate = Path(path)
            if not candidate.is_absolute():
                candidate = base / candidate
            if not candidate.exists():
                return False
        return True

    def _detect_repo_root(self) -> Optional[Path]:
        try:
            current = Path.cwd().resolve()
        except Exception:
            return None
        for candidate in [current, *current.parents]:
            if (candidate / ".git").exists():
                return candidate
        return None

    def _current_commit(self) -> Optional[str]:
        if not self.repo_root:
            return None
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            return None
        return None
