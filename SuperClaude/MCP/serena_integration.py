"""
Serena MCP Integration for project memory and symbol operations.

Provides semantic understanding and session persistence capabilities.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Information about a code symbol."""

    name: str
    type: str  # function, class, variable, etc.
    file_path: str
    line_number: int
    description: str
    references: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionMemory:
    """Session state and context memory."""

    session_id: str
    timestamp: datetime
    context: Dict[str, Any]
    symbols: List[SymbolInfo]
    tasks: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]
    checkpoints: List[Dict[str, Any]]


class SerenaMCPIntegration:
    """
    Integration with Serena MCP server for project memory.

    Provides:
    - Symbol indexing and retrieval
    - Session persistence
    - Project understanding
    - Cross-session memory
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Serena integration."""
        self.config = config or {}
        self.memory_prefix = self.config.get('memory_prefix', 'sc_')
        self.persistence_enabled = self.config.get('persistence', True)
        self.current_session: Optional[SessionMemory] = None
        self.symbol_index: Dict[str, SymbolInfo] = {}

    async def initialize_session(self, session_id: Optional[str] = None) -> SessionMemory:
        """
        Initialize or resume a session.

        Args:
            session_id: Optional session ID to resume

        Returns:
            SessionMemory object
        """
        if session_id and self.persistence_enabled:
            # Try to load existing session
            session = await self._load_session(session_id)
            if session:
                self.current_session = session
                logger.info(f"Resumed session: {session_id}")
                return session

        # Create new session
        session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session = SessionMemory(
            session_id=session_id,
            timestamp=datetime.now(),
            context={},
            symbols=[],
            tasks=[],
            decisions=[],
            checkpoints=[]
        )

        logger.info(f"Created new session: {session_id}")
        return self.current_session

    async def index_symbols(self, directory: Path) -> List[SymbolInfo]:
        """
        Index symbols in a directory.

        Args:
            directory: Directory to index

        Returns:
            List of discovered symbols
        """
        symbols = []

        # Mock implementation - real version would use Serena MCP
        try:
            # In real implementation, call Serena MCP server
            # response = await self._call_serena("index_symbols", {"path": str(directory)})

            # Mock response
            mock_symbols = [
                SymbolInfo(
                    name="CommandRegistry",
                    type="class",
                    file_path=str(directory / "Commands" / "registry.py"),
                    line_number=15,
                    description="Command registration and discovery"
                ),
                SymbolInfo(
                    name="ModelRouter",
                    type="class",
                    file_path=str(directory / "ModelRouter" / "router.py"),
                    line_number=45,
                    description="Intelligent model routing"
                )
            ]

            for symbol in mock_symbols:
                self.symbol_index[symbol.name] = symbol
                symbols.append(symbol)

            if self.current_session:
                self.current_session.symbols.extend(symbols)

            logger.info(f"Indexed {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to index symbols: {e}")

        return symbols

    async def find_symbol(self, name: str, type_filter: Optional[str] = None) -> Optional[SymbolInfo]:
        """
        Find a symbol by name.

        Args:
            name: Symbol name to find
            type_filter: Optional type filter (function, class, etc.)

        Returns:
            SymbolInfo if found, None otherwise
        """
        # Check local cache first
        if name in self.symbol_index:
            symbol = self.symbol_index[name]
            if not type_filter or symbol.type == type_filter:
                return symbol

        # In real implementation, query Serena MCP
        # response = await self._call_serena("find_symbol", {"name": name, "type": type_filter})

        return None

    async def get_references(self, symbol_name: str) -> List[str]:
        """
        Get all references to a symbol.

        Args:
            symbol_name: Name of the symbol

        Returns:
            List of file paths containing references
        """
        if symbol_name in self.symbol_index:
            return self.symbol_index[symbol_name].references

        # In real implementation, query Serena MCP
        # response = await self._call_serena("get_references", {"symbol": symbol_name})

        return []

    async def write_memory(self, key: str, value: Any) -> bool:
        """
        Write to persistent memory.

        Args:
            key: Memory key
            value: Value to store

        Returns:
            Success status
        """
        if not self.current_session:
            logger.error("No active session")
            return False

        prefixed_key = f"{self.memory_prefix}{key}"

        try:
            # In real implementation, call Serena MCP
            # response = await self._call_serena("write_memory", {"key": prefixed_key, "value": value})

            # Update local session
            self.current_session.context[key] = value

            logger.debug(f"Wrote memory: {prefixed_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to write memory: {e}")
            return False

    async def read_memory(self, key: str) -> Optional[Any]:
        """
        Read from persistent memory.

        Args:
            key: Memory key

        Returns:
            Stored value if exists
        """
        if not self.current_session:
            logger.error("No active session")
            return None

        # Check local session first
        if key in self.current_session.context:
            return self.current_session.context[key]

        prefixed_key = f"{self.memory_prefix}{key}"

        try:
            # In real implementation, call Serena MCP
            # response = await self._call_serena("read_memory", {"key": prefixed_key})
            # return response.get("value")

            return None

        except Exception as e:
            logger.error(f"Failed to read memory: {e}")
            return None

    async def list_memories(self) -> List[str]:
        """
        List all memory keys.

        Returns:
            List of memory keys
        """
        if not self.current_session:
            return []

        try:
            # In real implementation, call Serena MCP
            # response = await self._call_serena("list_memories", {"prefix": self.memory_prefix})
            # return response.get("keys", [])

            return list(self.current_session.context.keys())

        except Exception as e:
            logger.error(f"Failed to list memories: {e}")
            return []

    async def checkpoint(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create a session checkpoint.

        Args:
            name: Checkpoint name
            metadata: Optional checkpoint metadata

        Returns:
            Success status
        """
        if not self.current_session:
            logger.error("No active session")
            return False

        checkpoint = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "context_snapshot": dict(self.current_session.context)
        }

        self.current_session.checkpoints.append(checkpoint)

        # Persist checkpoint
        await self.write_memory(f"checkpoint_{name}", checkpoint)

        logger.info(f"Created checkpoint: {name}")
        return True

    async def restore_checkpoint(self, name: str) -> bool:
        """
        Restore from a checkpoint.

        Args:
            name: Checkpoint name

        Returns:
            Success status
        """
        checkpoint_data = await self.read_memory(f"checkpoint_{name}")

        if not checkpoint_data:
            logger.error(f"Checkpoint not found: {name}")
            return False

        if self.current_session:
            self.current_session.context = checkpoint_data.get("context_snapshot", {})
            logger.info(f"Restored checkpoint: {name}")
            return True

        return False

    async def track_task(self, task_id: str, status: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Track task execution.

        Args:
            task_id: Task identifier
            status: Task status
            metadata: Optional task metadata
        """
        if not self.current_session:
            return

        task = {
            "id": task_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.current_session.tasks.append(task)
        await self.write_memory(f"task_{task_id}", task)

    async def record_decision(self, decision: str, reason: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Record an architectural or design decision.

        Args:
            decision: Decision made
            reason: Reasoning for the decision
            metadata: Optional decision metadata
        """
        if not self.current_session:
            return

        decision_record = {
            "decision": decision,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.current_session.decisions.append(decision_record)
        await self.write_memory(f"decision_{len(self.current_session.decisions)}", decision_record)

    async def save_session(self) -> bool:
        """
        Save current session state.

        Returns:
            Success status
        """
        if not self.current_session:
            logger.error("No active session")
            return False

        if not self.persistence_enabled:
            return True

        try:
            session_data = {
                "session_id": self.current_session.session_id,
                "timestamp": self.current_session.timestamp.isoformat(),
                "context": self.current_session.context,
                "symbols": [self._serialize_symbol(s) for s in self.current_session.symbols],
                "tasks": self.current_session.tasks,
                "decisions": self.current_session.decisions,
                "checkpoints": self.current_session.checkpoints
            }

            await self.write_memory(f"session_{self.current_session.session_id}", session_data)

            logger.info(f"Saved session: {self.current_session.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    async def _load_session(self, session_id: str) -> Optional[SessionMemory]:
        """
        Load a saved session.

        Args:
            session_id: Session ID to load

        Returns:
            SessionMemory if found
        """
        session_data = await self.read_memory(f"session_{session_id}")

        if not session_data:
            return None

        try:
            session = SessionMemory(
                session_id=session_data["session_id"],
                timestamp=datetime.fromisoformat(session_data["timestamp"]),
                context=session_data["context"],
                symbols=[self._deserialize_symbol(s) for s in session_data["symbols"]],
                tasks=session_data["tasks"],
                decisions=session_data["decisions"],
                checkpoints=session_data["checkpoints"]
            )

            # Rebuild symbol index
            for symbol in session.symbols:
                self.symbol_index[symbol.name] = symbol

            return session

        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None

    def _serialize_symbol(self, symbol: SymbolInfo) -> Dict[str, Any]:
        """Serialize a symbol for storage."""
        return {
            "name": symbol.name,
            "type": symbol.type,
            "file_path": symbol.file_path,
            "line_number": symbol.line_number,
            "description": symbol.description,
            "references": symbol.references,
            "dependencies": symbol.dependencies,
            "metadata": symbol.metadata
        }

    def _deserialize_symbol(self, data: Dict[str, Any]) -> SymbolInfo:
        """Deserialize a symbol from storage."""
        return SymbolInfo(**data)

    async def _call_serena(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Serena MCP server.

        In production, this would make actual MCP server calls.
        """
        # Mock implementation
        return {}


# Convenience functions
async def create_serena_integration(config: Optional[Dict[str, Any]] = None) -> SerenaMCPIntegration:
    """Create and initialize Serena integration."""
    integration = SerenaMCPIntegration(config)
    await integration.initialize_session()
    return integration