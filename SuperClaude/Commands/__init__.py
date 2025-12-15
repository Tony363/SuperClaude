"""
Command System for SuperClaude Framework.

Provides automatic discovery, parsing, and execution of /sc: commands
with full agent and MCP server integration.
"""

from .executor import CommandContext, CommandExecutor, CommandResult
from .parser import CommandParser, ParsedCommand
from .registry import CommandMetadata, CommandRegistry

__all__ = [
    "CommandContext",
    "CommandExecutor",
    "CommandMetadata",
    "CommandParser",
    "CommandRegistry",
    "CommandResult",
    "ParsedCommand",
]

__version__ = "1.0.0"
