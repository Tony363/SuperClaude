"""
SuperClaude Framework MCP Server Integrations

This module provides integrations with various MCP (Model Context Protocol) servers
for enhanced capabilities including UI generation, multi-step reasoning,
documentation fetching, browser automation, and multi-model orchestration.
"""

# Import MCP integrations
from .zen_integration import (
    ZenIntegration,
    ConsensusResult,
    ThinkingMode,
    ModelConfig,
    ConsensusType
)

from .serena_integration import (
    SerenaIntegration,
    SerenaSymbol,
    SerenaMemory
)

from .playwright_integration import (
    PlaywrightIntegration,
    BrowserAction,
    PageSnapshot,
    TestResult
)

from .deepwiki_integration import (
    DeepwikiIntegration,
    DeepwikiDocument,
    DeepwikiSearchResult,
    DocumentationType
)

# Import from integrations subdirectory
from .integrations.magic_integration import (
    MagicIntegration,
    MagicComponent
)

from .integrations.sequential_integration import (
    SequentialIntegration,
    ThinkingStep,
    AnalysisResult
)

# Version info
__version__ = "6.0.0-alpha"

# Export all classes and functions
__all__ = [
    # Zen MCP
    'ZenIntegration',
    'ConsensusResult',
    'ThinkingMode',
    'ModelConfig',
    'ConsensusType',

    # Serena MCP
    'SerenaIntegration',
    'SerenaSymbol',
    'SerenaMemory',

    # Playwright MCP
    'PlaywrightIntegration',
    'BrowserAction',
    'PageSnapshot',
    'TestResult',

    # Deepwiki MCP
    'DeepwikiIntegration',
    'DeepwikiDocument',
    'DeepwikiSearchResult',
    'DocumentationType',

    # Magic MCP
    'MagicIntegration',
    'MagicComponent',

    # Sequential MCP
    'SequentialIntegration',
    'ThinkingStep',
    'AnalysisResult',
]

# MCP Server Registry
MCP_SERVERS = {
    'magic': MagicIntegration,
    'sequential': SequentialIntegration,
    'serena': SerenaIntegration,
    'playwright': PlaywrightIntegration,
    'zen': ZenIntegration,
    'deepwiki': DeepwikiIntegration,
}

def get_mcp_integration(server_name: str, **kwargs):
    """
    Factory function to get MCP integration instance.

    Args:
        server_name: Name of the MCP server
        **kwargs: Additional arguments for the integration

    Returns:
        Instance of the requested MCP integration

    Raises:
        ValueError: If server_name is not recognized
    """
    if server_name not in MCP_SERVERS:
        raise ValueError(f"Unknown MCP server: {server_name}. Available: {', '.join(MCP_SERVERS.keys())}")

    integration_class = MCP_SERVERS[server_name]
    return integration_class(**kwargs)