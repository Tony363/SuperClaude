"""
Command Executor for SuperClaude Framework.

Orchestrates command execution with agent and MCP server integration.
"""

import asyncio
import logging
import os
import subprocess
import py_compile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import yaml

from .parser import CommandParser, ParsedCommand
from .registry import CommandRegistry, CommandMetadata
from ..MCP import get_mcp_integration
from ..Quality.quality_scorer import QualityScorer, QualityAssessment
from ..Monitoring.performance_monitor import get_monitor, MetricType

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Execution context for a command."""
    command: ParsedCommand
    metadata: CommandMetadata
    mcp_servers: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    session_id: str = ""


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    command_name: str
    output: Any
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    mcp_servers_used: List[str] = field(default_factory=list)
    agents_used: List[str] = field(default_factory=list)
    executed_operations: List[str] = field(default_factory=list)
    applied_changes: List[str] = field(default_factory=list)
    status: str = 'plan-only'


class CommandExecutor:
    """
    Executor for /sc: commands.

    Features:
    - Command routing to agents/MCP servers
    - Async execution support
    - Command chaining and composition
    - Execution history tracking
    - Error handling and recovery
    """

    def __init__(self, registry: CommandRegistry, parser: CommandParser):
        """
        Initialize command executor.

        Args:
            registry: CommandRegistry instance
            parser: CommandParser instance
        """
        self.registry = registry
        self.parser = parser
        self.execution_history: List[CommandResult] = []
        self.active_mcp_servers: Dict[str, Any] = {}
        self.agent_loader = None  # Will be injected
        self.hooks: Dict[str, List[Callable]] = {
            'pre_execute': [],
            'post_execute': [],
            'on_error': []
        }
        self.repo_root = self._detect_repo_root()
        self.quality_scorer = QualityScorer()
        try:
            self.monitor = get_monitor()
        except Exception as exc:
            logger.debug(f"Performance monitor unavailable: {exc}")
            self.monitor = None

    def set_agent_loader(self, agent_loader) -> None:
        """
        Set agent loader for command execution.

        Args:
            agent_loader: AgentLoader instance
        """
        self.agent_loader = agent_loader

    async def execute(self, command_str: str) -> CommandResult:
        """
        Execute a command string.

        Args:
            command_str: Full command string

        Returns:
            CommandResult with execution details
        """
        start_time = datetime.now()

        try:
            # Parse command
            parsed = self.parser.parse(command_str)

            # Get command metadata
            metadata = self.registry.get_command(parsed.name)
            if not metadata:
                return CommandResult(
                    success=False,
                    command_name=parsed.name,
                    output=None,
                    errors=[f"Command '{parsed.name}' not found"]
                )

            # Create execution context
            context = CommandContext(
                command=parsed,
                metadata=metadata,
                session_id=self._generate_session_id()
            )

            # Run pre-execution hooks
            await self._run_hooks('pre_execute', context)

            # Activate required MCP servers
            await self._activate_mcp_servers(context)

            # Select and load required agents
            await self._load_agents(context)

            pre_change_snapshot = self._snapshot_repo_changes()

            # Execute command logic
            output = await self._execute_command_logic(context)

            test_results = None
            if self._should_run_tests(parsed):
                test_results = self._run_requested_tests(parsed)
                context.results['test_results'] = test_results
                if isinstance(output, dict):
                    output['test_results'] = test_results
                if not test_results.get('passed', False):
                    context.errors.append("Automated tests failed")

            post_change_snapshot = self._snapshot_repo_changes()
            repo_change_entries = self._diff_snapshots(pre_change_snapshot, post_change_snapshot)
            repo_change_descriptions = [self._format_change_entry(entry) for entry in repo_change_entries]
            diff_stats = self._collect_diff_stats()

            executed_operations: List[str] = []
            applied_changes: List[str] = []

            if isinstance(output, dict):
                executed_operations.extend(self._extract_output_evidence(output, 'executed_operations'))
                executed_operations.extend(self._extract_output_evidence(output, 'actions_taken'))
                executed_operations.extend(self._extract_output_evidence(output, 'commands_run'))
                applied_changes.extend(self._extract_output_evidence(output, 'applied_changes'))
                applied_changes.extend(self._extract_output_evidence(output, 'files_modified'))

            executed_operations.extend(self._normalize_evidence_value(context.results.get('executed_operations')))
            applied_changes.extend(self._normalize_evidence_value(context.results.get('applied_changes')))

            if repo_change_descriptions:
                applied_changes.extend(repo_change_descriptions)
            if diff_stats:
                applied_changes.extend(diff_stats)

            if test_results:
                executed_operations.append(self._summarize_test_results(test_results))
                if test_results.get('stdout'):
                    executed_operations.append(f"tests stdout: {test_results['stdout']}")
                if test_results.get('stderr'):
                    executed_operations.append(f"tests stderr: {test_results['stderr']}")

            executed_operations = self._deduplicate(executed_operations)
            applied_changes = self._deduplicate(applied_changes)

            derived_status = 'executed' if executed_operations or applied_changes else 'plan-only'

            if isinstance(output, dict):
                output['executed_operations'] = executed_operations
                output['applied_changes'] = applied_changes

                existing_status = output.get('status')
                if existing_status and existing_status not in {'executed', 'plan-only', 'failed'}:
                    output.setdefault('status_detail', existing_status)
                if existing_status != 'failed':
                    output['status'] = derived_status

            context.results['executed_operations'] = executed_operations
            context.results['applied_changes'] = applied_changes
            context.results['status'] = derived_status

            requires_evidence = self._requires_execution_evidence(context.metadata)
            quality_assessment: Optional[QualityAssessment] = None
            static_issues: List[str] = []
            changed_paths: List[Path] = []
            context.results['requires_evidence'] = requires_evidence
            context.results['missing_evidence'] = derived_status == 'plan-only' if requires_evidence else False

            if requires_evidence:
                changed_paths = self._extract_changed_paths(repo_change_entries, applied_changes)
                if changed_paths:
                    context.results['changed_files'] = [
                        self._relative_to_repo_path(path) for path in changed_paths
                    ]

                static_issues = self._run_static_validation(changed_paths)
                if static_issues:
                    static_issues = self._deduplicate(static_issues)
                    context.results['static_validation_errors'] = static_issues
                    context.errors.extend(static_issues)
                    if isinstance(output, dict):
                        validation_errors = self._ensure_list(output, 'validation_errors')
                        for issue in static_issues:
                            if issue not in validation_errors:
                                validation_errors.append(issue)

                quality_assessment = self._evaluate_quality_gate(
                    context,
                    output,
                    changed_paths,
                    derived_status
                )

                if quality_assessment:
                    serialized_assessment = self._serialize_assessment(quality_assessment)
                    context.results['quality_assessment'] = serialized_assessment
                    if isinstance(output, dict):
                        output['quality_assessment'] = serialized_assessment

                    suggestions = self.quality_scorer.get_improvement_suggestions(quality_assessment)
                    context.results['quality_suggestions'] = suggestions
                    if isinstance(output, dict):
                        output['quality_suggestions'] = suggestions

                    if not quality_assessment.passed:
                        failure_msg = (
                            f"Quality score {quality_assessment.overall_score:.1f} "
                            f"(threshold {quality_assessment.threshold:.1f})"
                        )
                        context.errors.append(failure_msg)
                        if isinstance(output, dict):
                            warnings_list = self._ensure_list(output, 'warnings')
                            if failure_msg not in warnings_list:
                                warnings_list.append(failure_msg)
                            for suggestion in suggestions[:3]:
                                detail = f"Improve {suggestion.get('dimension', 'quality')} — {suggestion.get('suggestion', '')}"
                                if detail.strip() and detail not in warnings_list:
                                    warnings_list.append(detail)
                else:
                    if isinstance(output, dict):
                        warnings_list = self._ensure_list(output, 'warnings')
                        detail = context.results.get('quality_assessment_error')
                        message = (
                            f"Quality scoring unavailable: {detail}"
                            if detail else
                            "Quality scoring unavailable; unable to verify evidence."
                        )
                        if message not in warnings_list:
                            warnings_list.append(message)

            success_flag = not bool(context.errors)

            if requires_evidence and derived_status == 'plan-only':
                success_flag = False
                missing_evidence_msg = (
                    "Requires execution evidence but no repository changes were detected."
                )
                if missing_evidence_msg not in context.errors:
                    context.errors.append(missing_evidence_msg)
                if isinstance(output, dict):
                    warnings_list = self._ensure_list(output, 'warnings')
                    warning_msg = (
                        "No concrete repository changes detected; returning plan-only status."
                    )
                    if warning_msg not in warnings_list:
                        warnings_list.append(warning_msg)
                    if missing_evidence_msg not in warnings_list:
                        warnings_list.append(missing_evidence_msg)

            context.errors = self._deduplicate(context.errors)

            self._record_requires_evidence_metrics(
                parsed.name,
                requires_evidence,
                derived_status,
                success_flag,
                quality_assessment,
                static_issues
            )

            # Run post-execution hooks
            await self._run_hooks('post_execute', context)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Create result
            result = CommandResult(
                success=success_flag,
                command_name=parsed.name,
                output=output,
                errors=context.errors,
                execution_time=execution_time,
                mcp_servers_used=context.mcp_servers,
                agents_used=context.agents,
                executed_operations=executed_operations,
                applied_changes=applied_changes,
                status=derived_status
            )

            # Record in history
            self.execution_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}")

            # Run error hooks
            if 'on_error' in self.hooks:
                for hook in self.hooks['on_error']:
                    try:
                        await hook(e, command_str)
                    except:
                        pass

            return CommandResult(
                success=False,
                command_name=parsed.name if 'parsed' in locals() else 'unknown',
                output=None,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    async def _activate_mcp_servers(self, context: CommandContext) -> None:
        """
        Activate required MCP servers for command.

        Args:
            context: Command execution context
        """
        required_servers = context.metadata.mcp_servers or []

        # Load MCP server config (best-effort)
        mcp_config = {}
        try:
            # Resolve config path relative to package
            base_dir = os.path.dirname(os.path.dirname(__file__))
            cfg_path = os.path.join(base_dir, 'Config', 'mcp.yaml')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    mcp_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load MCP config: {e}")

        server_configs = (mcp_config.get('servers') or {}) if isinstance(mcp_config, dict) else {}

        for server_name in required_servers:
            if server_name in self.active_mcp_servers:
                context.mcp_servers.append(server_name)
                continue

            try:
                cfg = server_configs.get(server_name, {}) if isinstance(server_configs, dict) else {}
                # Instantiate the integration. Prefer passing config if accepted.
                try:
                    instance = get_mcp_integration(server_name, config=cfg)
                except TypeError:
                    instance = get_mcp_integration(server_name)

                # Attempt basic initialization hooks if present
                init = getattr(instance, 'initialize', None)
                init_session = getattr(instance, 'initialize_session', None)
                if callable(init):
                    maybe = init()
                    if hasattr(maybe, '__await__'):
                        await maybe
                if callable(init_session):
                    maybe = init_session()  # often async for Serena-like
                    if hasattr(maybe, '__await__'):
                        await maybe

                self.active_mcp_servers[server_name] = {
                    'status': 'active',
                    'activated_at': datetime.now(),
                    'instance': instance,
                    'config': cfg,
                }
                context.mcp_servers.append(server_name)
                logger.info(f"Activated MCP server: {server_name}")
            except Exception as e:
                # Don't fail the command for unknown/non-critical MCP servers; log and continue
                logger.warning(f"Skipping MCP server '{server_name}': {e}")

    async def _load_agents(self, context: CommandContext) -> None:
        """
        Load required agents for command.

        Args:
            context: Command execution context
        """
        if not self.agent_loader:
            logger.warning("Agent loader not configured")
            return

        required_personas = context.metadata.personas

        for persona in required_personas:
            try:
                # Map persona to agent
                agent_name = self._map_persona_to_agent(persona)
                if agent_name:
                    logger.info(f"Loading agent: {agent_name} for persona: {persona}")
                    # TODO: Integrate with actual agent loading
                    context.agents.append(agent_name)
            except Exception as e:
                logger.error(f"Failed to load agent for persona {persona}: {e}")
                context.errors.append(f"Agent loading failed: {persona}")

    def _map_persona_to_agent(self, persona: str) -> Optional[str]:
        """
        Map persona name to agent name.

        Args:
            persona: Persona name from command

        Returns:
            Agent name or None
        """
        persona_to_agent = {
            'architect': 'system-architect',
            'frontend': 'frontend-architect',
            'backend': 'backend-architect',
            'security': 'security-engineer',
            'qa-specialist': 'quality-engineer',
            'performance': 'performance-engineer',
            'devops': 'devops-architect',
            'python': 'python-expert',
            'refactoring': 'refactoring-expert',
            'documentation': 'technical-writer'
        }
        return persona_to_agent.get(persona)

    async def _execute_command_logic(self, context: CommandContext) -> Any:
        """
        Execute the actual command logic.

        Args:
            context: Command execution context

        Returns:
            Command output
        """
        command_name = context.command.name

        # Command-specific execution logic
        if command_name == 'implement':
            return await self._execute_implement(context)
        elif command_name == 'analyze':
            return await self._execute_analyze(context)
        elif command_name == 'test':
            return await self._execute_test(context)
        elif command_name == 'build':
            return await self._execute_build(context)
        elif command_name == 'git':
            return await self._execute_git(context)
        elif command_name == 'workflow':
            return await self._execute_workflow(context)
        else:
            # Generic execution for other commands
            return await self._execute_generic(context)

    async def _execute_implement(self, context: CommandContext) -> Dict[str, Any]:
        """Execute implementation command."""
        return {
            'status': 'implementation_started',
            'agents': context.agents,
            'mcp_servers': context.mcp_servers,
            'parameters': context.command.parameters
        }

    async def _execute_analyze(self, context: CommandContext) -> Dict[str, Any]:
        """Execute analysis command."""
        return {
            'status': 'analysis_started',
            'scope': context.command.parameters.get('scope', 'project'),
            'focus': context.command.parameters.get('focus', 'all')
        }

    async def _execute_test(self, context: CommandContext) -> Dict[str, Any]:
        """Execute test command."""
        return {
            'status': 'tests_started',
            'coverage': context.command.parameters.get('coverage', True),
            'type': context.command.parameters.get('type', 'all')
        }

    async def _execute_build(self, context: CommandContext) -> Dict[str, Any]:
        """Execute build command."""
        return {
            'status': 'build_started',
            'optimize': context.command.parameters.get('optimize', False),
            'target': context.command.parameters.get('target', 'production')
        }

    async def _execute_git(self, context: CommandContext) -> Dict[str, Any]:
        """Execute git command."""
        return {
            'status': 'git_operation_started',
            'operation': context.command.arguments[0] if context.command.arguments else 'status'
        }

    async def _execute_workflow(self, context: CommandContext) -> Dict[str, Any]:
        """Execute workflow command."""
        return {
            'status': 'workflow_generated',
            'steps': self._generate_workflow_steps(context)
        }

    async def _execute_generic(self, context: CommandContext) -> Dict[str, Any]:
        """Execute generic command."""
        return {
            'status': 'executed',
            'command': context.command.name,
            'parameters': context.command.parameters,
            'arguments': context.command.arguments
        }

    def _generate_workflow_steps(self, context: CommandContext) -> List[Dict[str, Any]]:
        """Generate workflow steps based on command context."""
        # Basic workflow generation
        steps = []

        # Add analysis step if needed
        if 'analyze' in context.metadata.personas:
            steps.append({
                'step': 1,
                'action': 'analyze_requirements',
                'agent': 'requirements-analyst'
            })

        # Add implementation steps
        if 'implement' in context.command.name:
            steps.append({
                'step': len(steps) + 1,
                'action': 'implement_feature',
                'agent': 'general-purpose'
            })

        # Add testing step
        if context.command.parameters.get('with-tests', False):
            steps.append({
                'step': len(steps) + 1,
                'action': 'create_tests',
                'agent': 'quality-engineer'
            })

        return steps

    def _detect_repo_root(self) -> Optional[Path]:
        """Locate the git repository root, if available."""
        try:
            current = Path.cwd().resolve()
        except Exception:
            return None

        for candidate in [current, *current.parents]:
            if (candidate / '.git').exists():
                return candidate
        return None

    def _snapshot_repo_changes(self) -> Set[str]:
        """Capture current git worktree changes for comparison."""
        if not self.repo_root or not (self.repo_root / '.git').exists():
            return set()

        snapshot: Set[str] = set()
        commands = [
            ["git", "diff", "--name-status"],
            ["git", "diff", "--name-status", "--cached"]
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
            except Exception as exc:
                logger.debug(f"Failed to run {' '.join(cmd)}: {exc}")
                return set()

            if result.returncode != 0:
                continue

            for line in result.stdout.splitlines():
                entry = line.strip()
                if entry:
                    snapshot.add(entry)

        try:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    path = line.strip()
                    if path:
                        snapshot.add(f"??\t{path}")
        except Exception as exc:
            logger.debug(f"Failed to list untracked files: {exc}")

        return snapshot

    def _diff_snapshots(self, before: Set[str], after: Set[str]) -> List[str]:
        """Return new repo changes detected between snapshots."""
        if not after:
            return []
        if not before:
            return sorted(after)
        return sorted(after - before)

    def _format_change_entry(self, entry: str) -> str:
        """Convert a git name-status entry into a human readable description."""
        parts = entry.split('\t')
        if not parts:
            return entry

        code = parts[0]
        code_letter = code[0] if code else '?'

        if code.startswith('??') and len(parts) >= 2:
            return f"add {parts[1]}"

        if code_letter == 'M' and len(parts) >= 2:
            return f"modify {parts[1]}"

        if code_letter == 'A' and len(parts) >= 2:
            return f"add {parts[1]}"

        if code_letter == 'D' and len(parts) >= 2:
            return f"delete {parts[1]}"

        if code_letter == 'R' and len(parts) >= 3:
            return f"rename {parts[1]} -> {parts[2]}"

        if code_letter == 'C' and len(parts) >= 3:
            return f"copy {parts[1]} -> {parts[2]}"

        if len(parts) >= 2:
            return f"{code_letter.lower()} {parts[1]}"

        return entry

    def _collect_diff_stats(self) -> List[str]:
        """Collect diff statistics for working and staged changes."""
        if not self.repo_root or not (self.repo_root / '.git').exists():
            return []

        stats: List[str] = []
        commands = [
            ("working", ["git", "diff", "--stat"]),
            ("staged", ["git", "diff", "--stat", "--cached"])
        ]

        for label, cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
            except Exception as exc:
                logger.debug(f"Failed to gather diff stats ({label}): {exc}")
                continue

            output = result.stdout.strip()
            if output:
                stats.append(f"diff --stat ({label}): {self._truncate_output(output)}")

        return stats

    def _extract_changed_paths(self, repo_entries: List[str], applied_changes: List[str]) -> List[Path]:
        """Derive candidate file paths that were reported as changed."""
        if not self.repo_root:
            return []

        candidates: List[str] = []

        for entry in repo_entries:
            parts = entry.split('\t')
            if not parts:
                continue
            code = parts[0]
            if code.startswith('??') and len(parts) >= 2:
                candidates.append(parts[1])
            elif (code.startswith('R') or code.startswith('C')) and len(parts) >= 3:
                candidates.append(parts[2])
            elif len(parts) >= 2:
                candidates.append(parts[1])

        for change in applied_changes:
            tokens = change.split()
            if not tokens:
                continue
            verb = tokens[0].lower()
            if verb in {'add', 'modify', 'delete'} and len(tokens) >= 2:
                candidates.append(tokens[-1])
            elif verb in {'rename', 'copy'} and len(tokens) >= 3:
                candidates.append(tokens[-1])

        seen: Set[str] = set()
        paths: List[Path] = []
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate or candidate.startswith('diff'):
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            path = (self.repo_root / candidate).resolve()
            # Ensure we do not escape repo boundaries
            try:
                path.relative_to(self.repo_root)
            except ValueError:
                continue
            paths.append(path)

        return paths

    def _run_static_validation(self, paths: List[Path]) -> List[str]:
        """Run lightweight static validation on reported file changes."""
        issues: List[str] = []
        if not paths:
            return issues

        for path in paths:
            rel_path = self._relative_to_repo_path(path)
            if not path.exists():
                issues.append(f"{rel_path}: file reported as changed but not found on disk")
                continue

            if path.suffix == '.py':
                try:
                    py_compile.compile(str(path), doraise=True)
                except py_compile.PyCompileError as exc:
                    message = getattr(exc, 'msg', str(exc))
                    issues.append(f"{rel_path}: python syntax error — {message}")
                except Exception as exc:
                    issues.append(f"{rel_path}: python validation failed — {exc}")

        return issues

    def _relative_to_repo_path(self, path: Path) -> str:
        """Convert absolute path to repo-relative string."""
        if not self.repo_root:
            return str(path)
        try:
            return str(path.relative_to(self.repo_root))
        except ValueError:
            return str(path)

    def _serialize_assessment(self, assessment: QualityAssessment) -> Dict[str, Any]:
        """Convert QualityAssessment dataclass into JSON-serializable dict."""
        data = asdict(assessment)
        data['timestamp'] = assessment.timestamp.isoformat()

        metrics = data.get('metrics', [])
        for metric in metrics:
            dimension = metric.get('dimension')
            if hasattr(dimension, 'value'):
                metric['dimension'] = dimension.value

        return data

    def _evaluate_quality_gate(
        self,
        context: CommandContext,
        output: Any,
        changed_paths: List[Path],
        status: str
    ) -> Optional[QualityAssessment]:
        """Run quality scoring against the command result."""
        evaluation_context = dict(context.results)
        evaluation_context['status'] = status
        evaluation_context['changed_files'] = [
            self._relative_to_repo_path(path) for path in changed_paths
        ]

        try:
            return self.quality_scorer.evaluate(
                output,
                evaluation_context
            )
        except Exception as exc:
            logger.warning(f"Quality scoring failed: {exc}")
            context.results['quality_assessment_error'] = str(exc)
            return None

    def _record_requires_evidence_metrics(
        self,
        command_name: str,
        requires_evidence: bool,
        derived_status: str,
        success: bool,
        assessment: Optional[QualityAssessment],
        static_issues: List[str]
    ) -> None:
        """Send telemetry for requires-evidence command outcomes."""
        if not requires_evidence or not self.monitor:
            return

        tags = {
            'command': command_name,
            'status': derived_status
        }

        base = "commands.requires_evidence"
        self.monitor.record_metric(f"{base}.invocations", 1, MetricType.COUNTER, tags)

        if derived_status == 'plan-only':
            self.monitor.record_metric(f"{base}.plan_only", 1, MetricType.COUNTER, tags)
            self.monitor.record_metric(f"{base}.missing_evidence", 1, MetricType.COUNTER, tags)

        if static_issues:
            issue_tags = dict(tags)
            issue_tags['issue_count'] = str(len(static_issues))
            self.monitor.record_metric(
                f"{base}.static_validation_fail",
                len(static_issues),
                MetricType.COUNTER,
                issue_tags
            )
            self.monitor.record_metric(
                f"{base}.static_issue_count",
                len(static_issues),
                MetricType.GAUGE,
                issue_tags
            )

        if assessment:
            score_tags = dict(tags)
            score_tags['score'] = f"{assessment.overall_score:.1f}"
            score_tags['threshold'] = f"{assessment.threshold:.1f}"
            self.monitor.record_metric(
                f"{base}.quality_score",
                assessment.overall_score,
                MetricType.GAUGE,
                score_tags
            )
            metric_name = f"{base}.quality_pass" if assessment.passed else f"{base}.quality_fail"
            self.monitor.record_metric(metric_name, 1, MetricType.COUNTER, score_tags)
        else:
            self.monitor.record_metric(f"{base}.quality_missing", 1, MetricType.COUNTER, tags)

        outcome_metric = f"{base}.success" if success else f"{base}.failure"
        self.monitor.record_metric(outcome_metric, 1, MetricType.COUNTER, tags)

    def _normalize_evidence_value(self, value: Any) -> List[str]:
        """Normalize evidence values into a flat list of strings."""
        items: List[str] = []
        if value is None:
            return items

        if isinstance(value, list):
            for item in value:
                items.extend(self._normalize_evidence_value(item))
            return items

        if isinstance(value, dict):
            for key, subvalue in value.items():
                sub_items = self._normalize_evidence_value(subvalue)
                if sub_items:
                    for sub_item in sub_items:
                        items.append(f"{key}: {sub_item}")
                else:
                    items.append(f"{key}: {subvalue}")
            return items

        text = str(value).strip()
        if text:
            items.append(text)
        return items

    def _extract_output_evidence(self, output: Dict[str, Any], key: str) -> List[str]:
        """Extract evidence from an output dictionary for a specific key."""
        if key not in output:
            return []
        return self._normalize_evidence_value(output.get(key))

    def _deduplicate(self, items: List[str]) -> List[str]:
        """Remove duplicate evidence entries preserving order."""
        seen: Set[str] = set()
        deduped: List[str] = []
        for item in items:
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _ensure_list(self, container: Dict[str, Any], key: str) -> List[str]:
        """Ensure a dictionary value is a list, normalizing if necessary."""
        value = container.get(key)
        if isinstance(value, list):
            return value
        if value is None:
            container[key] = []
            return container[key]
        container[key] = [str(value)]
        return container[key]

    def _requires_execution_evidence(self, metadata: Optional[CommandMetadata]) -> bool:
        """Determine if a command requires execution evidence to claim success."""
        if not metadata:
            return False
        if metadata.requires_evidence:
            return True
        return metadata.name in {'implement'}

    def _should_run_tests(self, parsed: ParsedCommand) -> bool:
        """Determine if automated tests should be executed."""

        def _flag_enabled(value: Any) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value != 0
            if isinstance(value, str):
                return value.lower() in {'1', 'true', 'yes', 'on'}
            return False

        keys = ('with-tests', 'with_tests', 'run-tests', 'run_tests')

        for key in keys:
            if _flag_enabled(parsed.flags.get(key)):
                return True
            if _flag_enabled(parsed.parameters.get(key)):
                return True

        # Always run when invoking the dedicated test command.
        return parsed.name == 'test'

    def _run_requested_tests(self, parsed: ParsedCommand) -> Dict[str, Any]:
        """Execute project tests and capture results."""
        command = ["pytest", "-q"]
        target = parsed.parameters.get('target')
        if isinstance(target, str) and target.strip():
            command.append(target.strip())

        start = datetime.now()
        try:
            result = subprocess.run(
                command,
                cwd=str(self.repo_root or Path.cwd()),
                capture_output=True,
                text=True,
                check=False
            )
        except FileNotFoundError as exc:
            logger.warning(f"Test runner not available: {exc}")
            return {
                'command': ' '.join(command),
                'passed': False,
                'pass_rate': 0.0,
                'stdout': '',
                'stderr': str(exc),
                'duration_s': 0.0,
                'error': 'pytest_not_found'
            }
        except Exception as exc:
            logger.error(f"Unexpected error running tests: {exc}")
            return {
                'command': ' '.join(command),
                'passed': False,
                'pass_rate': 0.0,
                'stdout': '',
                'stderr': str(exc),
                'duration_s': 0.0,
                'error': 'test_execution_error'
            }

        duration = (datetime.now() - start).total_seconds()
        passed = result.returncode == 0

        return {
            'command': ' '.join(command),
            'passed': passed,
            'pass_rate': 1.0 if passed else 0.0,
            'stdout': self._truncate_output(result.stdout.strip()),
            'stderr': self._truncate_output(result.stderr.strip()),
            'duration_s': duration,
            'exit_code': result.returncode
        }

    def _summarize_test_results(self, test_results: Dict[str, Any]) -> str:
        """Create a concise summary string for executed tests."""
        command = test_results.get('command', 'tests')
        status = 'pass' if test_results.get('passed') else 'fail'
        duration = test_results.get('duration_s')
        duration_part = f" in {duration:.2f}s" if isinstance(duration, (int, float)) else ''
        return f"{command} ({status}{duration_part})"

    def _truncate_output(self, text: str, max_length: int = 800) -> str:
        """Limit captured command output to a manageable size."""
        if not text or len(text) <= max_length:
            return text
        head = text[: max_length // 2].rstrip()
        tail = text[-max_length // 2 :].lstrip()
        return f"{head}\n... [truncated] ...\n{tail}"

    async def _run_hooks(self, hook_type: str, context: CommandContext) -> None:
        """
        Run hooks of specified type.

        Args:
            hook_type: Type of hooks to run
            context: Command execution context
        """
        if hook_type in self.hooks:
            for hook in self.hooks[hook_type]:
                try:
                    await hook(context)
                except Exception as e:
                    logger.error(f"Hook execution failed: {e}")

    def register_hook(self, hook_type: str, hook_func: Callable) -> None:
        """
        Register a hook function.

        Args:
            hook_type: Type of hook (pre_execute, post_execute, on_error)
            hook_func: Hook function to register
        """
        if hook_type in self.hooks:
            self.hooks[hook_type].append(hook_func)

    def _generate_session_id(self) -> str:
        """Generate unique session ID for command execution."""
        from datetime import datetime
        import hashlib
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:12]

    def get_history(self, limit: int = 10) -> List[CommandResult]:
        """
        Get command execution history.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of recent CommandResult objects
        """
        return self.execution_history[-limit:]

    def clear_history(self) -> None:
        """Clear command execution history."""
        self.execution_history.clear()

    async def execute_chain(self, commands: List[str]) -> List[CommandResult]:
        """
        Execute a chain of commands sequentially.

        Args:
            commands: List of command strings

        Returns:
            List of CommandResult objects
        """
        results = []
        for command_str in commands:
            result = await self.execute(command_str)
            results.append(result)

            # Stop chain if command fails
            if not result.success:
                logger.warning(f"Command chain stopped due to failure: {command_str}")
                break

        return results

    async def execute_parallel(self, commands: List[str]) -> List[CommandResult]:
        """
        Execute multiple commands in parallel.

        Args:
            commands: List of command strings

        Returns:
            List of CommandResult objects
        """
        tasks = [self.execute(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(CommandResult(
                    success=False,
                    command_name='unknown',
                    output=None,
                    errors=[str(result)]
                ))
            else:
                final_results.append(result)

        return final_results
