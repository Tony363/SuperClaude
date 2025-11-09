"""
Command Registry System for SuperClaude Framework.

Provides automatic discovery, registration, and execution of /sc: commands.
Integrates with MCP servers and agent system for comprehensive functionality.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from functools import lru_cache
import logging

try:  # Optional dependency
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional install
    yaml = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class CommandMetadata:
    """Metadata for a registered command."""
    name: str
    description: str
    category: str
    complexity: str
    mcp_servers: List[str] = field(default_factory=list)
    personas: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    flags: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    file_path: str = ""
    content: str = ""
    requires_evidence: bool = False


class CommandRegistry:
    """
    Central registry for all /sc: commands.

    Features:
    - Auto-discovery of command markdown files
    - YAML frontmatter parsing for metadata
    - Dynamic command routing
    - MCP server activation
    - Command validation and caching
    """

    def __init__(self, commands_dir: Optional[str] = None):
        """
        Initialize command registry.

        Args:
            commands_dir: Path to commands directory (defaults to Commands/)
        """
        self.commands_dir = Path(commands_dir or os.path.join(
            os.path.dirname(__file__), '.'
        ))
        self.commands: Dict[str, CommandMetadata] = {}
        self.categories: Dict[str, List[str]] = {}
        self._discover_commands()

    def _discover_commands(self) -> None:
        """Auto-discover and register all command files."""
        logger.info(f"Discovering commands in {self.commands_dir}")

        if yaml is None:
            logger.warning("PyYAML missing; skipping command discovery")
            return

        for file_path in self.commands_dir.glob("*.md"):
            if file_path.name.startswith("_"):
                continue  # Skip private files

            try:
                command = self._load_command(file_path)
                if command:
                    self.register_command(command)
                    logger.debug(f"Registered command: {command.name}")
            except Exception as e:
                logger.error(f"Failed to load command {file_path}: {e}")

    def _load_command(self, file_path: Path) -> Optional[CommandMetadata]:
        """
        Load command from markdown file with YAML frontmatter.

        Args:
            file_path: Path to command markdown file

        Returns:
            CommandMetadata or None if loading fails
        """
        if yaml is None:
            logger.warning(f"Cannot parse {file_path} because PyYAML is not installed")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract YAML frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            if not frontmatter_match:
                logger.warning(f"No frontmatter found in {file_path}")
                return None

            frontmatter = yaml.safe_load(frontmatter_match.group(1))

            if frontmatter.get('archived'):
                logger.info(f"Skipping archived command: {file_path.name}")
                return None

            # Extract command content
            command_content = content[frontmatter_match.end():]

            # Create command metadata
            command = CommandMetadata(
                name=frontmatter.get('name', file_path.stem),
                description=frontmatter.get('description', ''),
                category=frontmatter.get('category', 'general'),
                complexity=frontmatter.get('complexity', 'standard'),
                mcp_servers=frontmatter.get('mcp-servers', []),
                personas=frontmatter.get('personas', []),
                triggers=self._extract_triggers(command_content),
                flags=frontmatter.get('flags', []) or [],
                parameters=self._extract_parameters(command_content),
                file_path=str(file_path),
                content=command_content,
                requires_evidence=bool(frontmatter.get('requires_evidence', False))
            )

            return command

        except Exception as e:
            logger.error(f"Error loading command from {file_path}: {e}")
            return None

    def _extract_triggers(self, content: str) -> List[str]:
        """
        Extract trigger patterns from command content.

        Args:
            content: Command markdown content

        Returns:
            List of trigger patterns
        """
        triggers = []

        # Look for trigger patterns in content
        trigger_section = re.search(
            r'## (?:Triggers?|Context Trigger Pattern)\n(.*?)\n##',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if trigger_section:
            # Extract patterns from code blocks
            code_blocks = re.findall(r'```\n(.*?)\n```', trigger_section.group(1), re.DOTALL)
            for block in code_blocks:
                # Extract /sc: patterns
                patterns = re.findall(r'/sc:\w+(?:\s+\[.*?\])*', block)
                triggers.extend(patterns)

            # Also extract bullet points
            bullets = re.findall(r'^[-*]\s+(.+)$', trigger_section.group(1), re.MULTILINE)
            triggers.extend(bullets)

        return triggers

    def _extract_parameters(self, content: str) -> Dict[str, Any]:
        """
        Extract parameter definitions from command content.

        Args:
            content: Command markdown content

        Returns:
            Dictionary of parameter definitions
        """
        parameters = {}

        # Look for parameter patterns like [--flag] or [parameter]
        param_pattern = r'\[--?(\w+)(?:\s+(\w+(?:\|\w+)*))?(?:\]|\s+([^\]]+)\])'
        matches = re.findall(param_pattern, content)

        for match in matches:
            param_name = match[0]
            param_type = match[1] if match[1] else 'flag'
            param_desc = match[2] if match[2] else ''

            parameters[param_name] = {
                'type': param_type,
                'description': param_desc,
                'required': False  # Brackets indicate optional
            }

        return parameters

    def register_command(self, command: CommandMetadata) -> None:
        """
        Register a command in the registry.

        Args:
            command: CommandMetadata to register
        """
        self.commands[command.name] = command

        # Update category index
        if command.category not in self.categories:
            self.categories[command.category] = []
        self.categories[command.category].append(command.name)

    def get_command(self, name: str) -> Optional[CommandMetadata]:
        """
        Get command by name.

        Args:
            name: Command name (without /sc: prefix)

        Returns:
            CommandMetadata or None if not found
        """
        # Strip /sc: prefix if present
        name = name.replace('/sc:', '').strip()
        return self.commands.get(name)

    @lru_cache(maxsize=128)
    def find_command(self, query: str) -> List[Tuple[str, float]]:
        """
        Find commands matching a query.

        Args:
            query: Search query

        Returns:
            List of (command_name, relevance_score) tuples
        """
        query_lower = query.lower()
        matches = []

        for name, command in self.commands.items():
            score = 0.0

            # Exact name match
            if name == query_lower:
                score = 1.0
            # Name contains query
            elif query_lower in name:
                score = 0.8
            # Description contains query
            elif query_lower in command.description.lower():
                score = 0.6
            # Triggers contain query
            elif any(query_lower in trigger.lower() for trigger in command.triggers):
                score = 0.5
            # Category match
            elif query_lower in command.category:
                score = 0.3

            if score > 0:
                matches.append((name, score))

        # Sort by relevance score
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def list_commands(self, category: Optional[str] = None) -> List[str]:
        """
        List all registered commands.

        Args:
            category: Optional category filter

        Returns:
            List of command names
        """
        if category:
            return self.categories.get(category, [])
        return list(self.commands.keys())

    def get_categories(self) -> List[str]:
        """Get list of all command categories."""
        return list(self.categories.keys())

    def get_mcp_requirements(self, command_name: str) -> List[str]:
        """
        Get MCP server requirements for a command.

        Args:
            command_name: Command name

        Returns:
            List of required MCP server names
        """
        command = self.get_command(command_name)
        return command.mcp_servers if command else []

    def get_persona_requirements(self, command_name: str) -> List[str]:
        """
        Get persona requirements for a command.

        Args:
            command_name: Command name

        Returns:
            List of required persona names
        """
        command = self.get_command(command_name)
        return command.personas if command else []

    def validate_command(self, command_str: str) -> Tuple[bool, str]:
        """
        Validate a command string.

        Args:
            command_str: Full command string (e.g., "/sc:implement --safe")

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Extract command name
        match = re.match(r'/sc:(\w+)', command_str)
        if not match:
            return False, "Invalid command format. Use /sc:command_name"

        command_name = match.group(1)
        command = self.get_command(command_name)

        if not command:
            # Suggest similar commands
            suggestions = self.find_command(command_name)
            if suggestions:
                similar = ", ".join([name for name, _ in suggestions[:3]])
                return False, f"Unknown command '{command_name}'. Did you mean: {similar}?"
            return False, f"Unknown command '{command_name}'"

        return True, ""

    def get_command_help(self, command_name: str) -> str:
        """
        Get help text for a command.

        Args:
            command_name: Command name

        Returns:
            Help text string
        """
        command = self.get_command(command_name)
        if not command:
            return f"Command '{command_name}' not found"

        help_text = [
            f"# /sc:{command.name}",
            f"",
            f"**Description**: {command.description}",
            f"**Category**: {command.category}",
            f"**Complexity**: {command.complexity}",
        ]

        if command.mcp_servers:
            help_text.append(f"**MCP Servers**: {', '.join(command.mcp_servers)}")

        if command.personas:
            help_text.append(f"**Personas**: {', '.join(command.personas)}")

        if command.parameters:
            help_text.append("")
            help_text.append("## Parameters")
            for param_name, param_info in command.parameters.items():
                help_text.append(f"- `--{param_name}`: {param_info.get('description', '')}")

        return "\n".join(help_text)

    def export_manifest(self) -> Dict[str, Any]:
        """
        Export command manifest for documentation.

        Returns:
            Dictionary containing all command metadata
        """
        manifest = {
            'version': '6.0.0',
            'total_commands': len(self.commands),
            'categories': {},
            'commands': {}
        }

        for category, command_names in self.categories.items():
            manifest['categories'][category] = len(command_names)

        for name, command in self.commands.items():
            manifest['commands'][name] = {
                'description': command.description,
                'category': command.category,
                'complexity': command.complexity,
                'mcp_servers': command.mcp_servers,
                'personas': command.personas
            }

        return manifest
