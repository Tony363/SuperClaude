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
from SuperClaude.Commands import executor as executor_module


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
        assert isinstance(result.executed_operations, list)
        assert isinstance(result.applied_changes, list)
        assert result.status in {'plan-only', 'executed'}

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
        assert len(results) == 2
        assert results[0].success is True
        assert results[0].status == 'plan-only'
        assert results[1].command_name == 'implement'
        assert results[1].success is False
        assert results[1].status == 'plan-only'

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
        for result in results:
            assert isinstance(result.executed_operations, list)
            assert isinstance(result.applied_changes, list)
            assert result.status == 'plan-only'

    @pytest.mark.asyncio
    async def test_execute_with_tests_flag_runs_tests(self, monkeypatch):
        """Ensure --with-tests triggers automated test execution."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        def fake_run_requested_tests(self, parsed):
            return {
                'command': 'pytest -q',
                'passed': True,
                'pass_rate': 1.0,
                'stdout': 'collected 0 items',
                'stderr': '',
                'duration_s': 0.05,
                'exit_code': 0
            }

        monkeypatch.setattr(
            CommandExecutor,
            "_run_requested_tests",
            fake_run_requested_tests,
            raising=False
        )

        result = await executor.execute('/sc:implement --with-tests')

        assert result.success is True
        assert result.status == 'executed'
        assert any('pytest -q' in entry for entry in result.executed_operations)
        assert 'test_results' in result.output

    @pytest.mark.asyncio
    async def test_build_command_requires_evidence(self):
        """Commands marked requires_evidence should fail without proof."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        result = await executor.execute('/sc:build')

        assert result.success is False
        assert result.status == 'plan-only'
        assert any("Requires execution evidence" in err for err in result.errors)
        assert 'warnings' in result.output
        assert 'quality_assessment' in result.output
        assert isinstance(result.output['quality_assessment'], dict)
        assert result.output['quality_assessment']['overall_score'] < result.output['quality_assessment']['threshold']
        assert 'quality_suggestions' in result.output
        assert isinstance(result.output['quality_suggestions'], list)
        assert any("Quality score" in err for err in result.errors)

    @pytest.mark.asyncio
    async def test_requires_evidence_static_validation_flags_missing_file(self, monkeypatch):
        """Static validation should surface missing files as actionable feedback."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        missing_path = executor.repo_root / "nonexistent_static_validation_test.py"

        monkeypatch.setattr(
            CommandExecutor,
            "_extract_changed_paths",
            lambda self, repo_entries, applied_changes: [missing_path],
            raising=False
        )

        result = await executor.execute('/sc:build')

        assert result.success is False
        assert 'validation_errors' in result.output
        assert any("not found on disk" in err for err in result.output['validation_errors'])

    @pytest.mark.asyncio
    async def test_requires_evidence_records_monitor_metrics(self, monkeypatch):
        """Performance monitor should capture hallucination guardrail signals."""

        class DummyMonitor:
            def __init__(self):
                self.records = []

            def record_metric(self, name, value, metric_type=None, tags=None):
                self.records.append((name, value, metric_type, tags or {}))

        dummy_monitor = DummyMonitor()
        monkeypatch.setattr(
            executor_module,
            "get_monitor",
            lambda: dummy_monitor,
            raising=False
        )

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        result = await executor.execute('/sc:build')

        assert result.success is False
        metric_names = [name for name, *_ in dummy_monitor.records]
        base = "commands.requires_evidence"
        assert f"{base}.invocations" in metric_names
        assert f"{base}.plan_only" in metric_names
        assert f"{base}.missing_evidence" in metric_names
        assert f"{base}.quality_fail" in metric_names
        score_entries = [
            (name, value, tags)
            for name, value, _, tags in dummy_monitor.records
            if name == f"{base}.quality_score"
        ]
        assert score_entries, "quality_score gauge not recorded"
        recorded_score = score_entries[0][1]
        assert recorded_score < 70, "Quality guardrail should flag failing score"
