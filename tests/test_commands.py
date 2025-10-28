"""
Test command system functionality.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import List, Sequence

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
from SuperClaude.Modes.behavioral_manager import BehavioralMode


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
        assert 'zen' in mcp_servers


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
    async def test_command_chaining(self, monkeypatch):
        """Test command chaining execution."""
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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

        # Execute command chain
        commands = ['/sc:analyze', '/sc:implement', '/sc:test']
        results = await executor.execute_chain(commands)
        assert len(results) == 2

        analyze_result, implement_result = results

        assert analyze_result.success is True
        assert analyze_result.status == 'plan-only'

        assert implement_result.command_name == 'implement'
        assert implement_result.success is True
        assert implement_result.status == 'executed'
        assert implement_result.artifacts, "Implementation should emit artifacts"
        assert implement_result.consensus is not None
        assert implement_result.consensus.get('consensus_reached') is True
        applied_files = implement_result.output.get('applied_files') or []
        assert applied_files, "Implementation should apply repository changes"

        repo_root = executor.repo_root or Path.cwd()
        for rel_path in applied_files:
            target = repo_root / rel_path
            assert target.exists(), f"Expected applied file {rel_path} to exist"
            target.unlink(missing_ok=True)

        for artifact_path in implement_result.artifacts:
            artifact = repo_root / artifact_path
            artifact.unlink(missing_ok=True)

        impl_dir = repo_root / 'SuperClaude' / 'Implementation'
        if impl_dir.exists():
            try:
                impl_dir.rmdir()
            except OSError:
                pass

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
        assert result.output.get('test_artifacts'), 'Test artifacts should be recorded'
        assert result.consensus is not None

        repo_root = executor.repo_root or Path.cwd()
        applied_files = result.output.get('applied_files') or []
        for rel_path in applied_files:
            target = repo_root / rel_path
            target.unlink(missing_ok=True)

        for artifact_path in result.artifacts:
            (repo_root / artifact_path).unlink(missing_ok=True)

        impl_dir = repo_root / 'SuperClaude' / 'Implementation'
        if impl_dir.exists():
            try:
                impl_dir.rmdir()
            except OSError:
                pass

    @pytest.mark.asyncio
    async def test_build_command_runs_pipeline(self, monkeypatch):
        """Build command should execute pipeline steps and emit artifacts."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        commands_invoked: List[Sequence[str]] = []

        def fake_run_command(self, command, *, cwd=None, env=None, timeout=None):
            commands_invoked.append(tuple(command))
            return {
                'command': ' '.join(command),
                'args': list(command),
                'stdout': 'ok',
                'stderr': '',
                'exit_code': 0,
                'duration_s': 0.01
            }

        monkeypatch.setattr(
            CommandExecutor,
            '_run_command',
            fake_run_command,
            raising=False
        )

        result = await executor.execute('/sc:build --type prod')

        assert result.success is True
        assert result.output['status'] == 'build_succeeded'
        assert commands_invoked, "Expected build pipeline to invoke system commands"
        assert result.output.get('artifact'), "Build should produce an artifact"

        repo_root = executor.repo_root or Path.cwd()
        for artifact_path in result.artifacts:
            (repo_root / artifact_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_git_status_reports_repository_state(self, monkeypatch):
        """Git status should parse repository summary and create artifacts."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        def fake_run_command(self, command, *, cwd=None, env=None, timeout=None):
            if command[:4] == ['git', 'status', '--short', '--branch']:
                return {
                    'command': ' '.join(command),
                    'args': list(command),
                    'stdout': "## main\n M SuperClaude/Commands/executor.py\n?? new_feature.py\n",
                    'stderr': '',
                    'exit_code': 0,
                    'duration_s': 0.01
                }
            return {
                'command': ' '.join(command),
                'args': list(command),
                'stdout': '',
                'stderr': '',
                'exit_code': 0,
                'duration_s': 0.01
            }

        monkeypatch.setattr(
            CommandExecutor,
            '_run_command',
            fake_run_command,
            raising=False
        )

        result = await executor.execute('/sc:git status')
        assert result.success is True
        summary = result.output['summary']
        assert summary['branch'] == 'main'
        assert summary['staged_changes'] == 1
        assert summary['untracked_files'] == 1
        assert result.output.get('artifact')

        repo_root = executor.repo_root or Path.cwd()
        for artifact_path in result.artifacts:
            (repo_root / artifact_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_workflow_command_generates_plan(self):
        """Workflow command should produce structured steps from a PRD."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        repo_root = executor.repo_root or Path.cwd()
        prd_path = repo_root / "temp-workflow-spec.md"
        prd_path.write_text(
            "# Authentication feature\n\n"
            "## Goals\n"
            "- Enable secure login\n"
            "- Capture audit events\n\n"
            "## Non-Goals\n"
            "- Mobile clients\n\n"
            "## Acceptance Criteria\n"
            "- Users can authenticate with email and password\n"
            "- Security monitoring alerts on failed attempts\n",
            encoding='utf-8'
        )

        try:
            result = await executor.execute(f"/sc:workflow {prd_path.name} --strategy agile --depth deep --parallel")
            assert result.success is True
            assert result.output['status'] == 'workflow_generated'
            assert result.output['steps'], "Workflow should include generated steps"
            assert any(step['phase'] == 'Quality' for step in result.output['steps'])
            assert result.output.get('artifact')

            for artifact_path in result.artifacts:
                (repo_root / artifact_path).unlink(missing_ok=True)
        finally:
            prd_path.unlink(missing_ok=True)

    def test_run_requested_tests_translates_flags(self, monkeypatch):
        """_run_requested_tests should honor coverage, markers, and targets."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        parsed = parser.parse('/sc:test tests/unit --coverage --type unit --markers smoke,integration')

        captured = {}

        stdout = (
            "collected 3 items\n\n"
            "tests/unit/test_example.py::test_alpha PASSED\n"
            "tests/unit/test_example.py::test_beta PASSED\n"
            "tests/unit/test_example.py::test_gamma PASSED\n\n"
            "============================== 3 passed in 0.42s ==============================\n"
            "---------- coverage: platform linux, python 3.11.8-final-0 -----------\n"
            "Name                       Stmts   Miss  Cover\n"
            "----------------------------------------------\n"
            "SuperClaude/example.py        30      0   100%\n"
            "TOTAL                         30      0      0      100%\n"
        )

        def fake_run(cmd, **kwargs):
            captured['cmd'] = cmd
            return SimpleNamespace(returncode=0, stdout=stdout, stderr='')

        monkeypatch.setattr(executor_module.subprocess, 'run', fake_run, raising=False)

        result = executor._run_requested_tests(parsed)

        assert captured['cmd'][0] == 'pytest'
        assert '--cov=SuperClaude' in captured['cmd']
        assert '--cov-report=term-missing' in captured['cmd']
        assert '--cov-report=html' in captured['cmd']
        assert 'tests/unit' in captured['cmd']
        assert '-m' in captured['cmd']
        marker_expression = captured['cmd'][captured['cmd'].index('-m') + 1]
        assert 'unit' in marker_expression
        assert 'smoke' in marker_expression
        assert 'integration' in marker_expression

        assert result['passed'] is True
        assert result['coverage'] == 1.0
        assert result['tests_passed'] == 3
        assert result['tests_failed'] == 0
        assert result['pass_rate'] == 1.0
        assert result['markers'] == ['unit', 'smoke', 'integration']
        assert result['targets'] == ['tests/unit']

    def test_run_requested_tests_failure_metrics(self, monkeypatch):
        """Failure output should surface counts, errors, and coverage."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        parsed = parser.parse('/sc:test --markers smoke --target tests/failing')

        stdout = (
            "collected 2 items\n\n"
            "tests/failing/test_sample.py::test_ok PASSED\n"
            "tests/failing/test_sample.py::test_not_ok FAILED\n\n"
            "=========================== short test summary info ===========================\n"
            "FAILED tests/failing/test_sample.py::test_not_ok - AssertionError: boom\n"
            "========================= 1 failed, 1 passed in 0.33s =========================\n"
            "---------- coverage: platform linux, python 3.11.8-final-0 -----------\n"
            "Name                       Stmts   Miss  Cover\n"
            "----------------------------------------------\n"
            "SuperClaude/problem.py        20     10    50%\n"
            "TOTAL                         20     10      0      50%\n"
        )

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=1, stdout=stdout, stderr='')

        monkeypatch.setattr(executor_module.subprocess, 'run', fake_run, raising=False)

        result = executor._run_requested_tests(parsed)

        assert result['passed'] is False
        assert pytest.approx(result['pass_rate'], rel=1e-6) == 0.5
        assert result['tests_failed'] == 1
        assert result['tests_passed'] == 1
        assert result['coverage'] == 0.5
        assert 'tests/failing/test_sample.py::test_not_ok' in result.get('errors', [])[0]

    @pytest.mark.asyncio
    async def test_test_command_with_coverage_exposes_results(self, monkeypatch):
        """/sc:test --coverage should surface structured results and artifacts."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        stdout = (
            "collected 1 item\n\n"
            "tests/test_dummy.py::test_dummy PASSED\n\n"
            "============================== 1 passed in 0.21s ==============================\n"
            "---------- coverage: platform linux, python 3.11.8-final-0 -----------\n"
            "Name                       Stmts   Miss  Cover\n"
            "----------------------------------------------\n"
            "SuperClaude/dummy.py            5      0   100%\n"
            "TOTAL                           5      0      0      100%\n"
        )

        def fake_run(cmd, **kwargs):
            return SimpleNamespace(returncode=0, stdout=stdout, stderr='')

        monkeypatch.setattr(executor_module.subprocess, 'run', fake_run, raising=False)

        result = await executor.execute('/sc:test --coverage')

        assert result.success is False  # still plan-only due to no repo diffs
        assert result.command_name == 'test'
        assert result.output['test_results']['coverage'] == 1.0
        assert result.output['test_results']['tests_passed'] == 1
        assert result.output['test_results']['markers'] == []
        assert result.output['test_artifacts'], "Test evidence artifact should be recorded"

        repo_root = executor.repo_root or Path.cwd()
        for artifact_path in result.artifacts:
            path = repo_root / artifact_path
            if path.exists():
                path.unlink()

        generated_dir = repo_root / 'SuperClaude' / 'Generated'
        if generated_dir.exists():
            for child in generated_dir.glob('test-tests-*.md'):
                child.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_quality_loop_remediation_records_iteration(self, monkeypatch):
        """Quality remediation loop should apply changes and record iteration details."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        parsed = parser.parse('/sc:implement remediation --loop')
        metadata = registry.get_command('implement')
        context = CommandContext(
            command=parsed,
            metadata=metadata,
            session_id='loop-success',
            behavior_mode=BehavioralMode.NORMAL.value
        )
        context.results['mode'] = {}
        context.results['behavior_mode'] = context.behavior_mode
        context.results.setdefault('flags', [])
        context.loop_enabled = True
        context.loop_iterations = 2
        context.loop_min_improvement = 1.0

        def fake_prepare_agents(self, ctx, agents):
            return None

        monkeypatch.setattr(
            executor,
            '_prepare_remediation_agents',
            fake_prepare_agents.__get__(executor, CommandExecutor)
        )

        def fake_run_agent_pipeline(self, ctx):
            ctx.agent_outputs = {
                'quality-engineer': {
                    'proposed_changes': [{
                        'path': 'SuperClaude/Implementation/remediation.md',
                        'content': '# remediation change',
                        'mode': 'replace'
                    }]
                }
            }
            return {'operations': ['generated remediation change'], 'notes': [], 'warnings': []}

        monkeypatch.setattr(
            executor,
            '_run_agent_pipeline',
            fake_run_agent_pipeline.__get__(executor, CommandExecutor)
        )

        def fake_derive_change_plan(self, ctx, agent_result, *, label=None):
            suffix = f"-{label}" if label else ''
            return [{
                'path': f'SuperClaude/Implementation/remediation{suffix}.md',
                'content': '# remediation change',
                'mode': 'replace'
            }]

        monkeypatch.setattr(
            executor,
            '_derive_change_plan',
            fake_derive_change_plan.__get__(executor, CommandExecutor)
        )

        def fake_apply_change_plan(self, ctx, plan):
            return {
                'applied': [entry['path'] for entry in plan],
                'warnings': [],
                'base_path': str(self.repo_root or Path.cwd()),
                'session': 'repo'
            }

        monkeypatch.setattr(
            executor,
            '_apply_change_plan',
            fake_apply_change_plan.__get__(executor, CommandExecutor)
        )

        def fake_run_requested_tests(self, parsed_cmd):
            return {
                'command': 'pytest -q',
                'args': ['pytest', '-q'],
                'passed': True,
                'pass_rate': 1.0,
                'stdout': 'collected 1 item\n1 passed',
                'stderr': '',
                'duration_s': 0.2,
                'exit_code': 0,
                'coverage': 0.92,
                'summary': '1 passed'
            }

        monkeypatch.setattr(
            executor,
            '_run_requested_tests',
            fake_run_requested_tests.__get__(executor, CommandExecutor)
        )

        def make_assessment(score, passed, iteration, improvements):
            return QualityAssessment(
                overall_score=score,
                metrics=[],
                timestamp=datetime.now(),
                iteration=iteration,
                passed=passed,
                threshold=70.0,
                context={},
                improvements_needed=improvements
            )

        def fake_agentic_loop(initial_output, loop_ctx, improver_func, max_iterations=None, min_improvement=None):
            failing = make_assessment(55.0, False, 0, ['add tests'])
            remediation_context = {
                **loop_ctx,
                'iteration': 0,
                'quality_assessment': failing,
                'improvements_needed': failing.improvements_needed
            }
            improved_output = improver_func(initial_output, remediation_context)
            final = make_assessment(82.0, True, 1, [])
            history = [
                IterationResult(
                    iteration=0,
                    input_quality=55.0,
                    output_quality=82.0,
                    improvements_applied=['add tests'],
                    time_taken=0.05,
                    success=True
                )
            ]
            return improved_output, final, history

        monkeypatch.setattr(executor.quality_scorer, 'agentic_loop', fake_agentic_loop)

        output = {'status': 'plan-only'}
        loop_result = executor._maybe_run_quality_loop(context, output)

        assert loop_result is not None
        improved_output = loop_result['output']
        assert isinstance(improved_output, dict)
        assert improved_output['quality_loop'][0]['status'] == 'improved'
        assert improved_output['quality_loop'][0]['applied_files']
        assert context.results['loop_assessment']['passed'] is True
        assert context.results['quality_loop_iterations'][0]['tests']['passed'] is True

    @pytest.mark.asyncio
    async def test_quality_loop_remediation_propagates_failure(self, monkeypatch):
        """Quality remediation loop should surface failures when fixes do not succeed."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        parsed = parser.parse('/sc:implement remediation --loop')
        metadata = registry.get_command('implement')
        context = CommandContext(
            command=parsed,
            metadata=metadata,
            session_id='loop-failure',
            behavior_mode=BehavioralMode.NORMAL.value
        )
        context.results['mode'] = {}
        context.results['behavior_mode'] = context.behavior_mode
        context.loop_enabled = True
        context.loop_iterations = 1

        monkeypatch.setattr(
            executor,
            '_prepare_remediation_agents',
            (lambda self, ctx, agents: None).__get__(executor, CommandExecutor)
        )

        def fake_run_agent_pipeline(self, ctx):
            return {'operations': ['attempt remediation'], 'notes': [], 'warnings': []}

        monkeypatch.setattr(
            executor,
            '_run_agent_pipeline',
            fake_run_agent_pipeline.__get__(executor, CommandExecutor)
        )

        def fake_derive_change_plan(self, ctx, agent_result, *, label=None):
            return [{
                'path': f'SuperClaude/Implementation/noop-{label}.md',
                'content': '# noop',
                'mode': 'replace'
            }]

        monkeypatch.setattr(
            executor,
            '_derive_change_plan',
            fake_derive_change_plan.__get__(executor, CommandExecutor)
        )

        def fake_apply_change_plan(self, ctx, plan):
            return {
                'applied': [],
                'warnings': ['no remediation performed'],
                'base_path': str(self.repo_root or Path.cwd()),
                'session': 'repo'
            }

        monkeypatch.setattr(
            executor,
            '_apply_change_plan',
            fake_apply_change_plan.__get__(executor, CommandExecutor)
        )

        def fake_run_requested_tests(self, parsed_cmd):
            return {
                'command': 'pytest -q',
                'args': ['pytest', '-q'],
                'passed': False,
                'pass_rate': 0.0,
                'stdout': 'collected 1 item\n1 failed',
                'stderr': 'AssertionError',
                'duration_s': 0.15,
                'exit_code': 1,
                'coverage': 0.4,
                'summary': '1 failed'
            }

        monkeypatch.setattr(
            executor,
            '_run_requested_tests',
            fake_run_requested_tests.__get__(executor, CommandExecutor)
        )

        def make_assessment(score, passed, iteration, improvements):
            return QualityAssessment(
                overall_score=score,
                metrics=[],
                timestamp=datetime.now(),
                iteration=iteration,
                passed=passed,
                threshold=70.0,
                context={},
                improvements_needed=improvements
            )

        def fake_agentic_loop(initial_output, loop_ctx, improver_func, max_iterations=None, min_improvement=None):
            failing = make_assessment(50.0, False, 0, ['fix failures'])
            remediation_context = {
                **loop_ctx,
                'iteration': 0,
                'quality_assessment': failing,
                'improvements_needed': failing.improvements_needed
            }
            improver_func(initial_output, remediation_context)
            final = make_assessment(55.0, False, 1, ['fix failures'])
            history = [
                IterationResult(
                    iteration=0,
                    input_quality=50.0,
                    output_quality=55.0,
                    improvements_applied=['fix failures'],
                    time_taken=0.05,
                    success=False
                )
            ]
            return initial_output, final, history

        monkeypatch.setattr(executor.quality_scorer, 'agentic_loop', fake_agentic_loop)

        output = {'status': 'plan-only'}
        loop_result = executor._maybe_run_quality_loop(context, output)

        assert loop_result is not None
        assert context.results['loop_assessment']['passed'] is False
        iteration_record = context.results['quality_loop_iterations'][0]
        assert iteration_record['status'] in {'tests-failed', 'no-changes-tests-failed', 'no-changes'}
        assert iteration_record['tests']['passed'] is False
        assert context.results['quality_loop_warnings']

    @pytest.mark.asyncio
    async def test_implement_stub_runs_fail_requires_evidence(self, monkeypatch):
        """Stub-only implement runs should fail the requires-evidence gate."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        from SuperClaude.Monitoring import plan_only_logger
        monkeypatch.setattr(plan_only_logger, "_PLAN_ONLY_PATH", None, raising=False)

        async def fake_consensus(prompt: str, **kwargs):
            return {
                'consensus_reached': True,
                'final_decision': {'decision': 'approve'},
                'votes': []
            }

        executor.consensus_facade.run_consensus = fake_consensus

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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

        result = await executor.execute('/sc:implement sample feature')

        assert result.success is False
        assert result.status == 'plan-only'
        assert result.consensus is not None
        assert result.consensus.get('consensus_reached') is True
        assert result.output.get('applied_files') == []

        error_text = "\n".join(result.errors)
        assert "Requires execution evidence but no repository changes were detected." in error_text
        assert "Auto-generated implementation stubs were withheld" in error_text
        assert any("Suggested file targets" in err for err in result.errors)

        change_plan = result.output.get('change_plan') or []
        assert change_plan, "Change plan should include stub guidance"
        auto_stub_entries = [entry for entry in change_plan if entry.get('auto_stub')]
        assert auto_stub_entries, "Stub entries should be flagged as auto_stub"

        repo_root = executor.repo_root or Path.cwd()
        for entry in auto_stub_entries:
            stub_path = repo_root / entry['path']
            assert not stub_path.exists(), f"Stub file {stub_path} should not be written to disk"

        worktree_warnings = result.output.get('worktree_warnings') or []
        assert any("Auto-generated implementation stubs" in warning for warning in worktree_warnings), \
            "Worktree warnings should note that stubs were withheld"

        guidance = (result.output.get('guidance') or {}).get('plan_only') or []
        assert guidance, "Plan-only guidance should be surfaced in output"
        assert any(line.startswith('Suggested file targets') for line in guidance)

    @pytest.mark.asyncio
    async def test_plan_only_event_written(self, monkeypatch, tmp_path):
        """Plan-only outcomes should produce structured telemetry artifacts."""
        monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path))

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        async def fake_consensus(prompt: str, **kwargs):
            return {
                'consensus_reached': True,
                'final_decision': {'decision': 'approve'},
                'models': ['gpt-5', 'claude-opus-4.1'],
            }

        executor.consensus_facade.run_consensus = fake_consensus

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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

        result = await executor.execute('/sc:implement sample feature')

        assert result.success is False
        assert result.status == 'plan-only'

        plan_only_path = Path(tmp_path) / 'plan_only.jsonl'
        assert plan_only_path.exists(), "Plan-only telemetry file should be created"

        lines = [line for line in plan_only_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        assert lines, "Telemetry file should contain at least one entry"

        payload = json.loads(lines[-1])
        assert payload['command'] == 'implement'
        assert payload['requires_evidence'] is True
        assert payload['status'] == 'plan-only'
        assert 'change_plan_count' in payload
        assert payload.get('safe_apply_requested') is False

    @pytest.mark.asyncio
    async def test_safe_apply_writes_snapshot(self, monkeypatch, tmp_path):
        """--safe-apply should persist stubs to a scratch directory without touching the repo."""
        monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path))

        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        async def fake_consensus(prompt: str, **kwargs):
            return {
                'consensus_reached': True,
                'final_decision': {'decision': 'approve'},
                'models': ['gpt-5', 'claude-opus-4.1'],
            }

        executor.consensus_facade.run_consensus = fake_consensus

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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

        quality_loop_calls = {'count': 0}

        def fake_agentic_loop(output, context_data, improver_func=None, max_iterations=None, min_improvement=None):
            from datetime import datetime
            quality_loop_calls['count'] += 1
            assessment = QualityAssessment(
                overall_score=60.0,
                metrics=[],
                timestamp=datetime.utcnow(),
                iteration=1,
                passed=False,
                threshold=70.0,
                context=context_data,
                improvements_needed=['apply real diff'],
                metadata={}
            )
            history = [
                IterationResult(
                    iteration=0,
                    input_quality=50.0,
                    output_quality=60.0,
                    improvements_applied=['capture stub guidance'],
                    time_taken=0.1,
                    success=False
                )
            ]
            return output, assessment, history

        monkeypatch.setattr(
            executor.quality_scorer,
            'agentic_loop',
            fake_agentic_loop,
            raising=False
        )

        result = await executor.execute('/sc:implement sample feature --safe-apply')

        assert result.success is False
        assert result.status == 'plan-only'

        guidance = (result.output.get('guidance') or {}).get('plan_only') or []
        assert any('safe-apply snapshot' in line for line in guidance)

        safe_apply_root = tmp_path / 'safe_apply'
        assert safe_apply_root.exists(), "Safe apply directory should be materialized"

        session_dirs = list(safe_apply_root.rglob('*'))
        assert session_dirs, "Safe apply snapshot should create nested directories"

        snapshot_files = list(safe_apply_root.rglob('*.py'))
        assert snapshot_files, "Stub files should be written to the safe-apply area"

        payload_path = Path(tmp_path) / 'plan_only.jsonl'
        payload_lines = [line for line in payload_path.read_text(encoding='utf-8').splitlines() if line.strip()]
        payload = json.loads(payload_lines[-1])
        assert payload.get('safe_apply_requested') is True
        assert payload.get('safe_apply_directory')
        assert quality_loop_calls['count'] == 1

        loop_info = result.output.get('loop') or {}
        assert loop_info.get('auto_triggered') is True

    @pytest.mark.asyncio
    async def test_requires_evidence_blocks_on_consensus_failure(self, monkeypatch):
        """Requires-evidence commands should fail when consensus cannot be reached."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        async def failing_consensus(prompt: str, **kwargs):
            return {
                'consensus_reached': False,
                'error': 'no agreement between models',
                'models': ['gpt-5', 'claude-opus-4.1'],
                'think_level': kwargs.get('think_level', 2),
                'offline': True
            }

        executor.consensus_facade.run_consensus = failing_consensus

        def fake_run_requested_tests(self, parsed_cmd):
            return {
                'command': 'pytest -q',
                'args': ['pytest', '-q'],
                'passed': True,
                'pass_rate': 1.0,
                'stdout': 'collected 0 items',
                'stderr': '',
                'duration_s': 0.05,
                'exit_code': 0
            }

        monkeypatch.setattr(
            CommandExecutor,
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

        def fake_apply_change_plan(self, ctx, plan):
            return {
                'applied': [entry['path'] for entry in plan],
                'warnings': [],
                'base_path': str(self.repo_root or Path.cwd()),
                'session': 'repo'
            }

        monkeypatch.setattr(
            CommandExecutor,
            '_apply_change_plan',
            fake_apply_change_plan,
            raising=False
        )

        result = await executor.execute('/sc:implement sample feature --consensus')

        assert result.success is False
        assert any('consensus' in err.lower() for err in result.errors)
        assert result.consensus.get('consensus_reached') is False

    @pytest.mark.asyncio
    async def test_implement_fails_when_no_changes_applied(self, monkeypatch):
        """Implementation should fail fast when no repository changes are applied."""
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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

        def fake_apply_change_plan(self, context, plan):
            return {
                'applied': [],
                'warnings': ['no changes produced'],
                'base_path': str(self.repo_root or Path.cwd()),
                'session': 'stub'
            }

        monkeypatch.setattr(
            CommandExecutor,
            '_apply_change_plan',
            fake_apply_change_plan,
            raising=False
        )

        result = await executor.execute('/sc:implement empty feature')

        assert result.success is False
        assert result.status == 'plan-only'
        assert any('no repository changes' in err.lower() for err in result.errors)
        assert not result.output.get('applied_files')
        assert result.output.get('test_artifacts'), "Test artifact should still be recorded"

    @pytest.mark.asyncio
    async def test_analyze_command_includes_consensus(self, monkeypatch):
        """Non evidence commands should still attach consensus payloads."""
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

        result = await executor.execute('/sc:analyze repo health')

        assert result.success is True
        assert result.consensus is not None
        assert result.consensus.get('consensus_reached') is True
        assert isinstance(result.output, dict)
        assert result.output.get('consensus'), "Consensus payload should be included in command output"

    @pytest.mark.asyncio
    async def test_build_command_requires_evidence(self, monkeypatch):
        """Commands marked requires_evidence should fail without proof."""
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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

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

        repo_root = executor.repo_root or Path.cwd()
        for artifact_path in result.artifacts:
            (repo_root / artifact_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_requires_evidence_static_validation_flags_missing_file(self, monkeypatch):
        """Static validation should surface missing files as actionable feedback."""
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        missing_path = executor.repo_root / "nonexistent_static_validation_test.py"

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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

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

        repo_root = executor.repo_root or Path.cwd()
        for artifact_path in result.artifacts:
            (repo_root / artifact_path).unlink(missing_ok=True)

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
            '_run_requested_tests',
            fake_run_requested_tests,
            raising=False
        )

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

        repo_root = executor.repo_root or Path.cwd()
        for artifact_path in result.artifacts:
            (repo_root / artifact_path).unlink(missing_ok=True)

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

        def fake_agentic_loop(initial_output, loop_context, *, improver_func=None, max_iterations=None, min_improvement=None):
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
        assert result.status == 'plan-only'
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

    @pytest.mark.asyncio
    async def test_task_command_records_rube_operations(self, monkeypatch):
        """/sc:task should record Rube automation hooks when available."""
        monkeypatch.setenv("SC_NETWORK_MODE", "online")
        monkeypatch.setenv("SC_RUBE_MODE", "dry-run")

        registry = CommandRegistry()
        parser = CommandParser(registry=registry)
        executor = CommandExecutor(registry, parser)

        result = await executor.execute('/sc:task create "release notes" --strategy systematic')

        assert any(op.startswith('rube:') for op in result.executed_operations), "Expected Rube automation log"

    def _write_cleanup_stub(self, target: Path) -> None:
        target.write_text(
            (
                '"""Auto-generated implementation stub for cleanup test.\n\n'
                'Generated by the SuperClaude auto-implementation pipeline on 2001-01-01T00:00:00.\n'
                'Replace this placeholder with the final implementation once the change plan is complete.\n"""\n\n'
                'def auto_task_cleanup() -> None:\n'
                '    """Work through the auto-generated change plan before removing this stub."""\n'
                '    raise NotImplementedError("Replace auto-generated stub once implementation is complete")\n\n'
                '# Planned operations\n'
                '#  - remove placeholder\n'
            ),
            encoding="utf-8",
        )

    @pytest.mark.asyncio
    async def test_cleanup_helper_removes_stale_auto_stub(self):
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        repo_root = Path(executor.repo_root or Path.cwd())
        auto_root = repo_root / "SuperClaude" / "Implementation" / "Auto"
        test_dir = auto_root / "unit-tests"
        test_dir.mkdir(parents=True, exist_ok=True)

        stub_path = test_dir / "cleanup-20010101000000.py"
        self._write_cleanup_stub(stub_path)
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(stub_path, (old_time, old_time))

        removed, skipped = executor._cleanup_auto_stubs(auto_root, ttl_days=7)
        rel_path = executor._relative_to_repo_path(stub_path)
        assert rel_path in removed
        assert not skipped
        assert not stub_path.exists()
        if test_dir.exists():
            try:
                test_dir.rmdir()
            except OSError:
                pass

    @pytest.mark.asyncio
    async def test_cleanup_flag_triggers_stub_removal(self, monkeypatch):
        registry = CommandRegistry()
        parser = CommandParser()
        executor = CommandExecutor(registry, parser)

        repo_root = Path(executor.repo_root or Path.cwd())
        auto_root = repo_root / "SuperClaude" / "Implementation" / "Auto"
        test_dir = auto_root / "unit-tests-flag"
        test_dir.mkdir(parents=True, exist_ok=True)

        stub_path = test_dir / "cleanup-flag-20010101000000.py"
        self._write_cleanup_stub(stub_path)
        old_time = (datetime.now() - timedelta(days=30)).timestamp()
        os.utime(stub_path, (old_time, old_time))

        def fake_run_agent_pipeline(self, context):
            return {'operations': [], 'notes': [], 'warnings': []}

        def fake_derive_change_plan(self, context, agent_result):
            return []

        def fake_apply_change_plan(self, context, plan):
            return {'warnings': [], 'applied': [], 'base_path': str(repo_root), 'session': 'repo'}

        def fake_record_artifact(self, *args, **kwargs):
            return None

        monkeypatch.setattr(CommandExecutor, "_run_agent_pipeline", fake_run_agent_pipeline, raising=False)
        monkeypatch.setattr(CommandExecutor, "_derive_change_plan", fake_derive_change_plan, raising=False)
        monkeypatch.setattr(CommandExecutor, "_apply_change_plan", fake_apply_change_plan, raising=False)
        monkeypatch.setattr(CommandExecutor, "_record_artifact", fake_record_artifact, raising=False)

        parsed = parser.parse("/sc:implement cleanup --cleanup --cleanup-ttl=0")
        metadata = registry.get_command('implement')
        context = CommandContext(
            command=parsed,
            metadata=metadata,
            session_id="unit-test",
            behavior_mode=BehavioralMode.NORMAL.value,
        )
        context.results = {
            'mode': {},
            'behavior_mode': context.behavior_mode,
            'executed_operations': [],
            'applied_changes': [],
            'flags': sorted(parsed.flags.keys()),
            'agent_operations': [],
        }

        output = await executor._execute_implement(context)
        assert 'auto_stub_cleanup' in output
        removed = output['auto_stub_cleanup']['removed']
        assert executor._relative_to_repo_path(stub_path) in removed
        assert not stub_path.exists()
        if test_dir.exists():
            try:
                test_dir.rmdir()
            except OSError:
                pass
