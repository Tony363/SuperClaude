"""
Command System for SuperClaude Framework.

Provides automatic discovery, parsing, and execution of /sc: commands
with full agent and MCP server integration.
"""

from .registry import CommandRegistry, CommandMetadata
from .parser import CommandParser, ParsedCommand
from .executor import CommandExecutor, CommandContext, CommandResult

__all__ = [
    'CommandRegistry',
    'CommandMetadata',
    'CommandParser',
    'ParsedCommand',
    'CommandExecutor',
    'CommandContext',
    'CommandResult'
]

__version__ = '1.0.0'