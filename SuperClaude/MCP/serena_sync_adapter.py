"""
Serena Sync Adapter

Adapts SerenaIntegration to a simple key/value memory interface used
by WorktreeStateManager. Provides methods: list_memories, read_memory,
write_memory, delete_memory.
"""

from typing import Any, Dict, List, Optional
from .serena_integration import SerenaIntegration


class SerenaSyncAdapter:
    def __init__(self, integration: Optional[SerenaIntegration] = None):
        self.integration = integration or SerenaIntegration()
        self.integration.initialize()

    def list_memories(self, prefix: Optional[str] = None) -> List[str]:
        return self.integration.list_memories(prefix=prefix)

    def read_memory(self, key: str) -> Optional[Dict[str, Any]]:
        return self.integration.read_memory(key)

    def write_memory(self, key: str, value: Dict[str, Any]) -> None:
        self.integration.write_memory(key, value)

    def delete_memory(self, key: str) -> None:
        self.integration.delete_memory(key)
