"""
Test command system functionality.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.Commands import (
    CommandRegistry,
    CommandParser,
    CommandExecutor,
    ParsedCommand
)


class TestCommandRegistry:
    """Test command registry functionality."""

    def test_command_discovery(self):
        """Test automatic command discovery."""
        registry = CommandRegistry()

        # Should discover commands from markdown files
        commands = registry.list_commands()
        assert len(commands) > 0
        assert 'implement' in commands
        assert 'analyze' in commands

    def test_get_command(self):
        """Test getting command metadata."""
        registry = CommandRegistry()

        # Get implement command
        command = registry.get_command('implement')
        assert command is not None
        assert command.name == 'implement'
        assert 'Feature' in command.description

    def test_find_command(self):
        """Test command search functionality."""
        registry = CommandRegistry()

        # Search for commands
        matches = registry.find_command('impl')
        assert len(matches) > 0
        assert matches[0][0] == 'implement'

    def test_mcp_requirements(self):
        """Test MCP server requirement extraction."""
        registry = CommandRegistry()

        # Get MCP requirements for implement
        mcp_servers = registry.get_mcp_requirements('implement')
        assert isinstance(mcp_servers, list)
        assert 'context7' in mcp_servers or 'sequential' in mcp_servers


class TestCommandParser:
    """Test command parsing functionality."""

    def test_parse_basic_command(self):
        """Test parsing basic command."""
        parser = CommandParser()

        # Parse simple command
        parsed = parser.parse('/sc:implement')
        assert parsed.name == 'implement'
        assert len(parsed.arguments) == 0
        assert len(parsed.flags) == 0

    def test_parse_with_flags(self):
        """Test parsing command with flags."""
        parser = CommandParser()

        # Parse command with flags
        parsed = parser.parse('/sc:implement --safe --with-tests')
        assert parsed.name == 'implement'
        assert parsed.flags['safe'] == True
        assert 'with-tests' in parsed.flags or 'with_tests' in parsed.flags

    def test_parse_with_parameters(self):
        """Test parsing command with parameters."""
        parser = CommandParser()

        # Parse command with parameters
        parsed = parser.parse('/sc:analyze --scope=project --focus=security')
        assert parsed.name == 'analyze'
        assert parsed.parameters['scope'] == 'project'
        assert parsed.parameters['focus'] == 'security'

    def test_parse_with_arguments(self):
        """Test parsing command with positional arguments."""
        parser = CommandParser()

        # Parse command with arguments
        parsed = parser.parse('/sc:build production --optimize')
        assert parsed.name == 'build'
        assert 'production' in parsed.arguments
        assert parsed.flags['optimize'] == True

    def test_extract_commands(self):
        """Test extracting commands from text."""
        parser = CommandParser()

        # Extract multiple commands
        text = """
        Let me run /sc:analyze --scope=project first,
        then /sc:implement the feature,
        and finally /sc:test --coverage.
        """
        commands = parser.extract_commands(text)
        assert len(commands) == 3
        assert '/sc:analyze' in commands[0]
        assert '/sc:implement' in commands[1]
        assert '/sc:test' in commands[2]


class TestCommandExecutor:
    """Test command execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_command(self):
        """Test basic command execution."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        # Execute simple command
        result = await executor.execute('/sc:analyze')
        assert result.success == True
        assert result.command_name == 'analyze'

    @pytest.mark.asyncio
    async def test_execute_with_error(self):
        """Test command execution with error."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        # Execute invalid command
        result = await executor.execute('/sc:nonexistent')
        assert result.success == False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_command_chaining(self):
        """Test sequential command execution."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        # Execute command chain
        commands = ['/sc:analyze', '/sc:implement', '/sc:test']
        results = await executor.execute_chain(commands)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel command execution."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        # Execute commands in parallel
        commands = ['/sc:analyze --scope=file1', '/sc:analyze --scope=file2']
        results = await executor.execute_parallel(commands)
        assert len(results) == 2