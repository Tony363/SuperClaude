"""
SuperClaude Framework MCP Server Integrations

Provides integration factories and exports for MCP (Model Context Protocol)
servers including multi-model orchestration (Zen),
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

from .deepwiki_integration import (
    DeepwikiIntegration,
    DeepwikiDocument,
    DeepwikiSearchResult,
    DocumentationType,
)

from .rube_integration import (
    RubeIntegration,
)

# Version info
__version__ = "6.0.0-alpha"

__all__ = [
    'ZenIntegration', 'ConsensusResult', 'ThinkingMode', 'ModelConfig', 'ConsensusType',
    'DeepwikiIntegration', 'DeepwikiDocument', 'DeepwikiSearchResult', 'DocumentationType',
    'RubeIntegration',
    'get_mcp_integration',
]

# MCP Server Registry
MCP_SERVERS: Dict[str, Type[Any]] = {
    'zen': ZenIntegration,
    'deepwiki': DeepwikiIntegration,
    'rube': RubeIntegration,
}

def get_mcp_integration(server_name: str, **kwargs):
    """Factory to create an MCP integration instance by server name."""
    cls = MCP_SERVERS.get(server_name)
    if not cls:
        available = ', '.join(sorted(MCP_SERVERS.keys()))
        raise ValueError(f"Unknown MCP server: {server_name}. Available: {available}")
    return cls(**kwargs)
