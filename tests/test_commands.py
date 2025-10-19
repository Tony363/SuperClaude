"""
Test command system functionality.
"""

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.Commands import (
    CommandRegistry,
    CommandParser,
    CommandExecutor,
    ParsedCommand,
    CommandMetadata,
    CommandContext
)
from SuperClaude.Commands import executor as executor_module
from SuperClaude.Quality.quality_scorer import QualityAssessment, IterationResult, QualityScorer


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
        assert 'business-panel' in commands

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
        assert len(results) == 3

        analyze_result, implement_result, test_result = results

        assert analyze_result.success is True
        assert analyze_result.status == 'plan-only'

        assert implement_result.command_name == 'implement'
        assert implement_result.success is True
        assert implement_result.status == 'executed'
        assert implement_result.artifacts, "Implementation should emit artifacts"
        assert implement_result.consensus is not None
        assert implement_result.consensus.get('consensus_reached') is True

        assert test_result.command_name == 'test'
        assert test_result.success is False
        assert test_result.status == 'plan-only'

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
        assert result.consensus is not None

    @pytest.mark.asyncio
    async def test_implement_generates_artifact_and_consensus(self):
        """Implementation command should emit artifacts and consensus summary."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        async def fake_consensus(prompt: str, **kwargs):
            return {
                'consensus_reached': True,
                'final_decision': {'decision': 'approve'},
                'votes': []
            }

        executor.consensus_facade.run_consensus = fake_consensus

        result = await executor.execute('/sc:implement sample feature')

        assert result.success is True
        assert result.status == 'executed'
        assert result.artifacts, "Artifact list should not be empty"
        assert result.consensus is not None
        assert result.consensus.get('consensus_reached') is True

        repo_root = executor.repo_root or Path.cwd()
        for artifact in result.artifacts:
            artifact_path = repo_root / artifact
            assert artifact_path.exists()

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
        assert 'quality_iteration_history' in result.output
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
        assert f"{base}.consensus" in metric_names
        score_entries = [
            (name, value, tags)
            for name, value, _, tags in dummy_monitor.records
            if name == f"{base}.quality_score"
        ]
        assert score_entries, "quality_score gauge not recorded"
        recorded_score = score_entries[0][1]
        assert recorded_score < 70, "Quality guardrail should flag failing score"

    @pytest.mark.asyncio
    async def test_loop_flag_invokes_agentic_loop(self, monkeypatch):
        """--loop should run the agentic quality loop with requested iteration cap."""
        parser = CommandParser()
        parsed = parser.parse('/sc:dummy --loop 2')
        metadata = CommandMetadata(
            name='dummy',
            description='',
            category='general',
            complexity='standard'
        )
        context = CommandContext(
            command=parsed,
            metadata=metadata,
            session_id='loop-test'
        )
        context.results['mode'] = {}
        context.results['behavior_mode'] = context.behavior_mode
        context.results['flags'] = sorted(parsed.flags.keys())

        executor = object.__new__(CommandExecutor)
        executor.quality_scorer = QualityScorer()
        executor.delegate_category_map = {}
        executor.extended_agent_loader = SimpleNamespace()
        executor.consensus_facade = SimpleNamespace()

        executor._apply_execution_flags(context)
        assert context.loop_enabled is True
        assert context.loop_iterations == 2

        call_record = {}

        def fake_agentic_loop(self, initial_output, loop_context, improver_func, max_iterations=None, min_improvement=None):
            call_record['called'] = True
            call_record['max_iterations'] = max_iterations
            call_record['context'] = loop_context
            improved_output = {
                'status': 'looped',
                'notes': ['auto-remediated']
            }
            assessment = QualityAssessment(
                overall_score=85.0,
                metrics=[],
                timestamp=datetime.now(),
                iteration=1,
                passed=True,
                threshold=70.0,
                context=loop_context
            )
            iteration_history = [
                IterationResult(
                    iteration=0,
                    input_quality=0.0,
                    output_quality=85.0,
                    improvements_applied=['add tests'],
                    time_taken=0.05,
                    success=True
                )
            ]
            return improved_output, assessment, iteration_history

        monkeypatch.setattr(
            executor.quality_scorer,
            "agentic_loop",
            fake_agentic_loop,
            raising=False
        )

        loop_result = executor._maybe_run_quality_loop(context, {'status': 'initial'})

        assert call_record.get('called') is True
        assert call_record.get('max_iterations') == 2
        assert call_record['context'].get('loop_requested') is True
        assert loop_result is not None
        assert loop_result['assessment'].overall_score == 85.0
        assert context.results['loop_assessment']['overall_score'] == 85.0
        assert context.results['loop_iterations_executed'] == 1

    @pytest.mark.asyncio
    async def test_consensus_flag_forces_consensus_failure(self, monkeypatch):
        """--consensus should enforce consensus checks even when not required by metadata."""
        parser = CommandParser()
        parsed = parser.parse('/sc:dummy --consensus')
        metadata = CommandMetadata(
            name='dummy',
            description='',
            category='general',
            complexity='standard'
        )
        context = CommandContext(
            command=parsed,
            metadata=metadata,
            session_id='consensus-test'
        )
        context.results['mode'] = {}
        context.results['behavior_mode'] = context.behavior_mode
        context.results['flags'] = sorted(parsed.flags.keys())

        executor = object.__new__(CommandExecutor)
        executor.quality_scorer = QualityScorer()
        executor.delegate_category_map = {}
        executor.extended_agent_loader = SimpleNamespace()

        executor._apply_execution_flags(context)
        assert context.consensus_forced is True

        call_record = {}

        async def failing_consensus(prompt, **kwargs):
            call_record['called'] = True
            call_record['think_level'] = kwargs.get('think_level')
            return {
                'consensus_reached': False,
                'error': 'hard disagreement',
                'think_level': kwargs.get('think_level')
            }

        executor.consensus_facade = SimpleNamespace(run_consensus=failing_consensus)

        result = await executor._ensure_consensus(
            context,
            {},
            enforce=context.consensus_forced,
            think_level=context.think_level
        )

        assert call_record.get('called') is True
        assert call_record.get('think_level') == 2
        assert result['error'] == 'hard disagreement'
        assert 'Consensus failed' in context.errors[0]

    @pytest.mark.asyncio
    async def test_business_panel_executor_produces_panel_artifact(self, tmp_path):
        """Business panel command should orchestrate experts and produce evidence."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        command = (
            "/sc:business-panel market expansion --mode debate "
            "--experts porter,christensen --focus disruption"
        )
        result = await executor.execute(command)

        assert result.success is True
        assert result.status == 'executed'
        assert 'sequential' in result.mcp_servers_used
        assert 'context7' in result.mcp_servers_used
        assert result.executed_operations, "Panel operations should be recorded"
        assert result.artifacts, "Business panel should emit an artifact"

        artifact_path = (executor.repo_root or Path.cwd()) / result.artifacts[0]
        assert artifact_path.exists()

        output = result.output
        assert output['panel']['mode'] == 'debate'
        expert_names = [expert['id'] for expert in output['panel']['experts']]
        assert 'porter' in expert_names
        assert 'christensen' in expert_names
        assert output['insights'], "Panel must produce insights"
        assert output['recommendations'], "Recommendations should not be empty"
