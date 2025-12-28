"""
MCP component - Reference documentation for native MCP tools.

SuperClaude now uses Claude Code's native MCP tools directly instead of
custom Python wrappers. This component provides documentation and verification
that MCP tools are available.
"""

from pathlib import Path
from typing import Any

from setup import __version__

from ..core.base import Component
from ..utils.ui import display_info


class MCPComponent(Component):
    """MCP documentation and verification component.

    MCP servers are now accessed via Claude Code's native tool system:
    - mcp__rube__* for Rube/Composio tools
    - mcp__pal__* for PAL tools (consensus, code review, etc.)

    No custom installation is needed - Claude Code handles MCP configuration.
    """

    def __init__(self, install_dir: Path | None = None):
        """Initialize MCP component."""
        super().__init__(install_dir)

        # Reference documentation for available MCP tools
        self.mcp_tools = {
            "rube": {
                "prefix": "mcp__rube__",
                "description": "Rube MCP - automation hub for 500+ app integrations",
                "tools": [
                    "RUBE_SEARCH_TOOLS",
                    "RUBE_MULTI_EXECUTE_TOOL",
                    "RUBE_CREATE_PLAN",
                    "RUBE_MANAGE_CONNECTIONS",
                    "RUBE_REMOTE_WORKBENCH",
                    "RUBE_REMOTE_BASH_TOOL",
                    "RUBE_FIND_RECIPE",
                    "RUBE_EXECUTE_RECIPE",
                ],
            },
            "pal": {
                "prefix": "mcp__pal__",
                "description": "PAL MCP - collaborative thinking and code review",
                "tools": [
                    "chat",
                    "thinkdeep",
                    "planner",
                    "consensus",
                    "codereview",
                    "precommit",
                    "debug",
                    "challenge",
                    "apilookup",
                    "listmodels",
                ],
            },
        }

    def get_metadata(self) -> dict[str, str]:
        """Get component metadata."""
        return {
            "name": "mcp",
            "version": __version__,
            "description": "Native MCP tools reference (Rube, PAL)",
            "category": "integration",
        }

    def validate_prerequisites(self, installSubPath: Path | None = None) -> tuple[bool, list[str]]:
        """No prerequisites needed - native MCP tools are built into Claude Code."""
        return True, []

    def get_files_to_install(self) -> list[tuple[Path, Path]]:
        """No files to install - MCP is native to Claude Code."""
        return []

    def get_metadata_modifications(self) -> dict[str, Any]:
        """Get metadata modifications for MCP component."""
        return {
            "components": {
                "mcp": {
                    "version": __version__,
                    "installed": True,
                    "native_mcp": True,
                }
            },
            "mcp": {
                "mode": "native",
                "tools": list(self.mcp_tools.keys()),
            },
        }

    def install(self, config: dict = None, **kwargs) -> bool:
        """Display MCP tools information.

        No installation needed - just shows documentation about available tools.
        """
        display_info("MCP Integration (Native Claude Code Tools)")
        display_info("")
        display_info("SuperClaude uses Claude Code's native MCP tools directly.")
        display_info("No custom installation or configuration needed.")
        display_info("")

        for server, info in self.mcp_tools.items():
            display_info(f"  {info['prefix']}*: {info['description']}")
            for tool in info["tools"][:5]:
                display_info(f"    - {info['prefix']}{tool}")
            if len(info["tools"]) > 5:
                display_info(f"    - ... and {len(info['tools']) - 5} more")
            display_info("")

        display_info("Usage: Call these tools directly in prompts or commands.")
        display_info("Example: 'Use mcp__rube__RUBE_SEARCH_TOOLS to find integrations'")

        return True

    def uninstall(self) -> bool:
        """No uninstallation needed for native MCP tools."""
        display_info("Native MCP tools are built into Claude Code.")
        display_info("No uninstallation needed.")
        return True

    def update(self, config: dict = None) -> bool:
        """No update needed for native MCP tools."""
        display_info("Native MCP tools are updated with Claude Code.")
        return True

    def validate_installation(self, installSubPath: Path | None = None) -> bool:
        """Native MCP tools are always available in Claude Code."""
        return True
