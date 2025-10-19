"""
SuperClaude Framework MCP Server Integrations

Provides integration factories and exports for MCP (Model Context Protocol)
servers including UI generation (Magic), sequential reasoning, project memory
(Serena), browser automation (Playwright), multi-model orchestration (Zen),
and documentation (Deepwiki).
"""

from typing import Dict, Type, Any

# Import MCP integrations with correct symbol names and aliases
from .zen_integration import (
    ZenIntegration,
    ConsensusResult,
    ThinkingMode,
    ModelConfig,
    ConsensusType,
)

from .serena_integration import (
    SerenaIntegration,
    SymbolInfo as SerenaSymbol,
    SessionMemory as SerenaMemory,
)

from .playwright_integration import (
    PlaywrightIntegration,
    TestResult,
)

from .deepwiki_integration import (
    DeepwikiIntegration,
    DeepwikiDocument,
    DeepwikiSearchResult,
    DocumentationType,
)

from .integrations.magic_integration import (
    MagicIntegration,
    MagicComponent,
)

from .integrations.sequential_integration import (
    SequentialIntegration,
)

from .integrations.context7_integration import (
    Context7Integration,
    Context7Reference,
)

from .integrations.morphllm_integration import (
    MorphLLMIntegration,
    MorphRecipe,
)

# Version info
__version__ = "6.0.0-alpha"

__all__ = [
    'ZenIntegration', 'ConsensusResult', 'ThinkingMode', 'ModelConfig', 'ConsensusType',
    'SerenaIntegration', 'SerenaSymbol', 'SerenaMemory',
    'PlaywrightIntegration', 'TestResult',
    'DeepwikiIntegration', 'DeepwikiDocument', 'DeepwikiSearchResult', 'DocumentationType',
    'MagicIntegration', 'MagicComponent',
    'SequentialIntegration',
    'Context7Integration', 'Context7Reference',
    'MorphLLMIntegration', 'MorphRecipe',
    'get_mcp_integration',
]

# MCP Server Registry
MCP_SERVERS: Dict[str, Type[Any]] = {
    'magic': MagicIntegration,
    'sequential': SequentialIntegration,
    'serena': SerenaIntegration,
    'playwright': PlaywrightIntegration,
    'zen': ZenIntegration,
    'deepwiki': DeepwikiIntegration,
    'context7': Context7Integration,
    'morphllm': MorphLLMIntegration,
}

def get_mcp_integration(server_name: str, **kwargs):
    """Factory to create an MCP integration instance by server name."""
    cls = MCP_SERVERS.get(server_name)
    if not cls:
        available = ', '.join(sorted(MCP_SERVERS.keys()))
        raise ValueError(f"Unknown MCP server: {server_name}. Available: {available}")
    return cls(**kwargs)
