"""
Command Executor for SuperClaude Framework.

Orchestrates command execution with agent and MCP server integration.
"""

import asyncio
import json
import logging
import os
import subprocess
import py_compile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import yaml

from .artifact_manager import CommandArtifactManager
from .parser import CommandParser, ParsedCommand
from .registry import CommandRegistry, CommandMetadata
from ..Agents.loader import AgentLoader
from ..Agents.extended_loader import ExtendedAgentLoader, AgentCategory, MatchScore
from ..MCP import get_mcp_integration
from ..ModelRouter.facade import ModelRouterFacade
from ..Modes.behavioral_manager import BehavioralMode, BehavioralModeManager
from ..Quality.quality_scorer import QualityScorer, QualityAssessment
from ..Monitoring.performance_monitor import get_monitor, MetricType

logger = logging.getLogger(__name__)

BUSINESS_PANEL_EXPERTS = {
    'christensen': {
        'name': 'Clayton Christensen',
        'lens': 'Disruption theory & jobs-to-be-done',
        'focus': ['disruption', 'innovation cadence', 'non-consumption'],
        'questions': [
            "What job is the customer hiring this to do?",
            "Which segments are overserved or underserved?",
            "How does this shift the value network?"
        ]
    },
    'porter': {
        'name': 'Michael Porter',
        'lens': 'Competitive strategy & five forces',
        'focus': ['competitive-analysis', 'moats', 'positioning'],
        'questions': [
            "How do the five forces shift under this move?",
            "Where can we create a defensible moat?",
            "What assumptions competitors rely on?"
        ]
    },
    'drucker': {
        'name': 'Peter Drucker',
        'lens': 'Management effectiveness & execution',
        'focus': ['operational-discipline', 'management'],
        'questions': [
            "What is the mission and is it still valid?",
            "What does the customer value now?",
            "Where do we place scarce resources?"
        ]
    },
    'godin': {
        'name': 'Seth Godin',
        'lens': 'Marketing innovation & tribe building',
        'focus': ['narrative', 'community', 'positioning'],
        'questions': [
            "Who is the smallest viable audience?",
            "What story are we telling that people repeat?",
            "How do we create remarkable signals?"
        ]
    },
    'kim_mauborgne': {
        'name': 'W. Chan Kim & Renee Mauborgne',
        'lens': 'Blue ocean strategy',
        'focus': ['value-innovation', 'differentiation', 'cost'],
        'questions': [
            "Which factors can we eliminate or reduce?",
            "Where can we raise new value for users?",
            "What uncontested space emerges?"
        ]
    },
    'collins': {
        'name': 'Jim Collins',
        'lens': 'Enduring companies & flywheels',
        'focus': ['execution', 'discipline', 'flywheel'],
        'questions': [
            "What is the hedgehog concept here?",
            "Which flywheel can we accelerate?",
            "What brutal facts must we confront?"
        ]
    },
    'taleb': {
        'name': 'Nassim Nicholas Taleb',
        'lens': 'Risk, optionality, and antifragility',
        'focus': ['risk', 'resilience', 'optionality'],
        'questions': [
            "Where are we exposed to tail risks?",
            "How do we gain from volatility?",
            "What optionality can we preserve?"
        ]
    },
    'meadows': {
        'name': 'Donella Meadows',
        'lens': 'Systems thinking & leverage points',
        'focus': ['systems-dynamics', 'feedback'],
        'questions': [
            "What reinforcing and balancing loops exist?",
            "Where is the highest leverage point?",
            "What delays or bottlenecks dominate?"
        ]
    },
    'doumont': {
        'name': 'Jean-luc Doumont',
        'lens': 'Structured communication & clarity',
        'focus': ['communication', 'decision-alignment'],
        'questions': [
            "How do we communicate the core message?",
            "What structure clarifies the decision?",
            "Which stakeholders need tailored framing?"
        ]
    }
}

BUSINESS_PANEL_FOCUS_MAP = {
    'disruption': ['christensen', 'porter', 'kim_mauborgne'],
    'competitive-analysis': ['porter', 'taleb', 'collins'],
    'go-to-market': ['godin', 'doumont', 'porter'],
    'systems': ['meadows', 'christensen', 'collins'],
    'risk': ['taleb', 'porter', 'christensen'],
    'execution': ['drucker', 'collins', 'kim_mauborgne']
}

DEFAULT_BUSINESS_PANEL_EXPERTS = ['porter', 'drucker', 'godin']


@dataclass
class CommandContext:
    """Execution context for a command."""
    command: ParsedCommand
    metadata: CommandMetadata
    mcp_servers: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    agent_instances: Dict[str, Any] = field(default_factory=dict)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    session_id: str = ""
    behavior_mode: str = BehavioralMode.NORMAL.value
    consensus_summary: Optional[Dict[str, Any]] = None
    artifact_records: List[Dict[str, Any]] = field(default_factory=list)
    think_level: int = 2
    loop_enabled: bool = False
    loop_iterations: Optional[int] = None
    loop_min_improvement: Optional[float] = None
    consensus_forced: bool = False
    delegated_agents: List[str] = field(default_factory=list)
    delegation_strategy: Optional[str] = None


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
    artifacts: List[str] = field(default_factory=list)
    consensus: Optional[Dict[str, Any]] = None
    behavior_mode: str = BehavioralMode.NORMAL.value
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
        self.hooks: Dict[str, List[Callable]] = {
            'pre_execute': [],
            'post_execute': [],
            'on_error': []
        }
        self.repo_root = self._detect_repo_root()
        base_path = self.repo_root or Path.cwd()
        self.agent_loader: AgentLoader = AgentLoader()
        self.extended_agent_loader: ExtendedAgentLoader = ExtendedAgentLoader()
        self.behavior_manager = BehavioralModeManager()
        self.artifact_manager = CommandArtifactManager(base_path / "SuperClaude" / "Generated")
        self.consensus_facade = ModelRouterFacade()
        self.quality_scorer = QualityScorer()
        self.delegate_category_map = {
            'delegate_core': AgentCategory.CORE_DEVELOPMENT,
            'delegate-debug': AgentCategory.QUALITY_SECURITY,
            'delegate_refactor': AgentCategory.CORE_DEVELOPMENT,
            'delegate-refactor': AgentCategory.CORE_DEVELOPMENT,
            'delegate_search': AgentCategory.DEVELOPER_EXPERIENCE,
            'delegate-search': AgentCategory.DEVELOPER_EXPERIENCE,
        }
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
        self.agent_loader = agent_loader or AgentLoader()

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

            mode_state = self._prepare_mode(parsed)

            # Create execution context
            context = CommandContext(
                command=parsed,
                metadata=metadata,
                session_id=self._generate_session_id(),
                behavior_mode=mode_state['mode']
            )
            context.results['mode'] = mode_state['context']
            context.results['behavior_mode'] = mode_state['mode']
            context.results.setdefault('executed_operations', [])
            context.results.setdefault('applied_changes', [])
            context.results.setdefault('artifacts', [])
            context.results.setdefault('flags', sorted(context.command.flags.keys()))

            self._apply_execution_flags(context)

            # Run pre-execution hooks
            await self._run_hooks('pre_execute', context)

            # Activate required MCP servers
            await self._activate_mcp_servers(context)

            # Select and load required agents
            await self._load_agents(context)

            pre_change_snapshot = self._snapshot_repo_changes()

            # Execute command logic
            output = await self._execute_command_logic(context)

            loop_assessment: Optional[QualityAssessment] = None
            if context.loop_enabled:
                loop_result = self._maybe_run_quality_loop(context, output)
                if loop_result:
                    output = loop_result['output']
                    loop_assessment = loop_result['assessment']

            consensus_result = None
            consensus_required = metadata.requires_evidence or context.consensus_forced
            if consensus_required:
                consensus_result = await self._ensure_consensus(
                    context,
                    output,
                    enforce=consensus_required,
                    think_level=context.think_level
                )
                if isinstance(output, dict):
                    output['consensus'] = consensus_result

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
                context.results['diff_stats'] = diff_stats
                if isinstance(output, dict):
                    output['diff_stats'] = diff_stats

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
                if context.results.get('artifacts'):
                    output['artifacts'] = context.results['artifacts']
                output.setdefault('mode', context.behavior_mode)
                if context.consensus_summary is not None:
                    output.setdefault('consensus', context.consensus_summary)
                if context.results.get('delegation'):
                    output.setdefault('delegation', context.results['delegation'])
                output.setdefault('think_level', context.think_level)
                if context.loop_enabled:
                    output.setdefault('loop', {
                        'requested': True,
                        'max_iterations': context.loop_iterations or self.quality_scorer.MAX_ITERATIONS,
                        'iterations_executed': context.results.get('loop_iterations_executed', 0),
                        'assessment': context.results.get('loop_assessment'),
                    })
                if context.results.get('routing_decision'):
                    output.setdefault('routing_decision', context.results['routing_decision'])

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
                    derived_status,
                    precomputed=loop_assessment
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
                        iteration_history = context.results.get('quality_iteration_history')
                        if iteration_history:
                            output['quality_iteration_history'] = iteration_history

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
                static_issues,
                context.consensus_summary
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
                artifacts=context.results.get('artifacts', []),
                consensus=context.consensus_summary,
                behavior_mode=context.behavior_mode,
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
        loader = self.agent_loader or AgentLoader()

        required_personas = context.metadata.personas or []

        for persona in required_personas:
            try:
                # Map persona to agent
                agent_name = self._map_persona_to_agent(persona)
                if agent_name:
                    logger.info(f"Loading agent: {agent_name} for persona: {persona}")
                    if agent_name in context.agent_instances:
                        continue
                    agent_instance = loader.load_agent(agent_name)
                    if agent_instance:
                        if agent_name not in context.agents:
                            context.agents.append(agent_name)
                        context.agent_instances[agent_name] = agent_instance
                    else:
                        warning = f"Agent loader returned None for {agent_name}"
                        logger.warning(warning)
                        context.errors.append(warning)
            except Exception as e:
                logger.error(f"Failed to load agent for persona {persona}: {e}")
                context.errors.append(f"Agent loading failed: {persona}")

        if context.delegated_agents:
            delegated = self._deduplicate(context.delegated_agents)
            context.delegated_agents = delegated
            context.results['delegated_agents'] = delegated
            for agent_name in delegated:
                if agent_name in context.agent_instances:
                    if agent_name not in context.agents:
                        context.agents.append(agent_name)
                    continue
                try:
                    agent_instance = loader.load_agent(agent_name)
                    if agent_instance:
                        context.agent_instances[agent_name] = agent_instance
                        if agent_name not in context.agents:
                            context.agents.append(agent_name)
                        logger.info(f"Auto-delegated agent loaded: {agent_name}")
                    else:
                        warning = f"Auto-delegation failed to load agent {agent_name}"
                        logger.warning(warning)
                        context.errors.append(warning)
                except Exception as exc:
                    message = f"Delegated agent load failed ({agent_name}): {exc}"
                    logger.error(message)
                    context.errors.append(message)

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
        elif command_name == 'business-panel':
            return await self._execute_business_panel(context)
        else:
            # Generic execution for other commands
            return await self._execute_generic(context)

    async def _execute_implement(self, context: CommandContext) -> Dict[str, Any]:
        """Execute implementation command."""
        agent_result = self._run_agent_pipeline(context)

        summary_lines = [
            f"Implementation request for: {' '.join(context.command.arguments) or 'unspecified scope'}",
            f"Mode: {context.behavior_mode}",
            f"Agents engaged: {', '.join(context.agents) or 'none'}",
        ]

        if agent_result['notes']:
            summary_lines.append("")
            summary_lines.append("Agent insights:")
            summary_lines.extend(f"- {note}" for note in agent_result['notes'])

        if agent_result['operations']:
            summary_lines.append("")
            summary_lines.append("Planned or executed operations:")
            summary_lines.extend(f"- {op}" for op in agent_result['operations'])

        if agent_result['warnings']:
            summary_lines.append("")
            summary_lines.append("Warnings:")
            summary_lines.extend(f"- {warn}" for warn in agent_result['warnings'])

        summary = "\n".join(summary_lines).strip()
        context.results['primary_summary'] = summary

        metadata = {
            'mode': context.behavior_mode,
            'agents': context.agents,
            'session_id': context.session_id,
            'mcp_servers': context.mcp_servers,
        }
        artifact_path = self._record_artifact(
            context,
            context.command.name,
            summary,
            operations=agent_result['operations'],
            metadata=metadata
        )

        status = 'executed' if artifact_path else 'implementation_started'

        output = {
            'status': status,
            'summary': summary,
            'agents': context.agents,
            'mcp_servers': context.mcp_servers,
            'parameters': context.command.parameters,
            'artifact': artifact_path,
            'agent_notes': agent_result['notes'],
            'agent_warnings': agent_result['warnings'],
            'mode': context.behavior_mode,
        }

        if artifact_path:
            output['executed_operations'] = context.results.get('agent_operations', [])

        return output

    async def _execute_analyze(self, context: CommandContext) -> Dict[str, Any]:
        """Execute analysis command."""
        return {
            'status': 'analysis_started',
            'scope': context.command.parameters.get('scope', 'project'),
            'focus': context.command.parameters.get('focus', 'all'),
            'mode': context.behavior_mode
        }

    async def _execute_test(self, context: CommandContext) -> Dict[str, Any]:
        """Execute test command."""
        return {
            'status': 'tests_started',
            'coverage': context.command.parameters.get('coverage', True),
            'type': context.command.parameters.get('type', 'all'),
            'mode': context.behavior_mode
        }

    async def _execute_build(self, context: CommandContext) -> Dict[str, Any]:
        """Execute build command."""
        return {
            'status': 'build_started',
            'optimize': context.command.parameters.get('optimize', False),
            'target': context.command.parameters.get('target', 'production'),
            'mode': context.behavior_mode
        }

    async def _execute_git(self, context: CommandContext) -> Dict[str, Any]:
        """Execute git command."""
        return {
            'status': 'git_operation_started',
            'operation': context.command.arguments[0] if context.command.arguments else 'status',
            'mode': context.behavior_mode
        }

    async def _execute_workflow(self, context: CommandContext) -> Dict[str, Any]:
        """Execute workflow command."""
        return {
            'status': 'workflow_generated',
            'steps': self._generate_workflow_steps(context),
            'mode': context.behavior_mode
        }

    async def _execute_business_panel(self, context: CommandContext) -> Dict[str, Any]:
        """Execute the business panel orchestration command."""
        agent_result = self._run_agent_pipeline(context)

        panel_topic = ' '.join(context.command.arguments).strip() or "unspecified business scenario"
        panel_mode = self._determine_business_panel_mode(context.command)
        focus_domain = self._determine_business_panel_focus(context.command)
        expert_ids = self._select_business_panel_experts(context.command, focus_domain)
        phases = self._determine_business_panel_phases(panel_mode)
        insights = self._generate_business_panel_insights(panel_topic, expert_ids, focus_domain)
        recommendations = self._generate_business_panel_recommendations(panel_topic, insights, focus_domain)

        panel_operations = [
            f"panel_mode: {panel_mode}",
            f"panel_focus: {focus_domain}",
            "experts_engaged: " + ', '.join(BUSINESS_PANEL_EXPERTS[eid]['name'] for eid in expert_ids),
            "panel_phases: " + ', '.join(phases)
        ]

        # Merge operations into execution evidence
        context.results.setdefault('executed_operations', []).extend(panel_operations)
        context.results['executed_operations'] = self._deduplicate(context.results['executed_operations'])

        if agent_result['operations']:
            context.results['executed_operations'].extend(
                op for op in agent_result['operations'] if op not in context.results['executed_operations']
            )
            context.results['executed_operations'] = self._deduplicate(context.results['executed_operations'])

        context.results.setdefault('panel', {}).update({
            'topic': panel_topic,
            'mode': panel_mode,
            'focus': focus_domain,
            'experts': expert_ids,
            'phases': phases
        })

        summary_lines = [
            f"Business panel analysis for: {panel_topic}",
            f"Mode: {panel_mode} | Focus: {focus_domain}",
            "",
            "Experts engaged:"
        ]
        for expert_id in expert_ids:
            expert = BUSINESS_PANEL_EXPERTS[expert_id]
            summary_lines.append(f"- {expert['name']} — {expert['lens']}")

        summary_lines.append("")
        summary_lines.append("Key insights:")
        for insight in insights[:5]:
            summary_lines.append(f"- {insight['expert']}: {insight['headline']}")

        summary = "\n".join(summary_lines).strip()

        metadata = {
            'topic': panel_topic,
            'mode': panel_mode,
            'focus': focus_domain,
            'experts': [BUSINESS_PANEL_EXPERTS[eid]['name'] for eid in expert_ids],
            'phases': phases
        }
        artifact_path = self._record_artifact(
            context,
            context.command.name,
            summary,
            operations=context.results['executed_operations'],
            metadata=metadata
        )

        status = 'executed' if context.results['executed_operations'] else 'panel_initialized'

        panel_payload = {
            'topic': panel_topic,
            'mode': panel_mode,
            'focus': focus_domain,
            'phases': phases,
            'experts': [
                {
                    'id': expert_id,
                    'name': BUSINESS_PANEL_EXPERTS[expert_id]['name'],
                    'lens': BUSINESS_PANEL_EXPERTS[expert_id]['lens']
                }
                for expert_id in expert_ids
            ]
        }

        output = {
            'status': status,
            'panel': panel_payload,
            'insights': insights,
            'recommendations': recommendations,
            'agent_notes': agent_result['notes'],
            'agent_warnings': agent_result['warnings'],
            'mcp_servers': context.mcp_servers,
            'artifact': artifact_path,
            'mode': context.behavior_mode
        }

        if artifact_path:
            output.setdefault('executed_operations', context.results['executed_operations'])

        return output

    async def _execute_generic(self, context: CommandContext) -> Dict[str, Any]:
        """Execute generic command."""
        return {
            'status': 'executed',
            'command': context.command.name,
            'parameters': context.command.parameters,
            'arguments': context.command.arguments,
            'mode': context.behavior_mode
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

    def _determine_business_panel_mode(self, command: ParsedCommand) -> str:
        """Select the panel interaction mode."""
        requested_mode = command.parameters.get('mode')
        if isinstance(requested_mode, str):
            requested_mode = requested_mode.lower()
        elif command.flags.get('mode'):
            requested_mode = str(command.flags.get('mode')).lower()

        valid_modes = {'discussion', 'debate', 'socratic', 'adaptive'}
        if requested_mode in valid_modes:
            return requested_mode

        for flag_name in ('mode_discussion', 'mode_debate', 'mode_socratic', 'mode_adaptive'):
            if command.flags.get(flag_name):
                suffix = flag_name.split('_', 1)[1]
                if suffix in valid_modes:
                    return suffix

        return 'discussion'

    def _determine_business_panel_focus(self, command: ParsedCommand) -> str:
        """Determine strategic focus for the panel."""
        focus = command.parameters.get('focus')
        if isinstance(focus, str) and focus:
            return focus.lower()

        return 'general'

    def _select_business_panel_experts(self, command: ParsedCommand, focus: str) -> List[str]:
        """Resolve which experts participate in the panel."""
        if command.flags.get('all-experts') or command.flags.get('all_experts'):
            return list(BUSINESS_PANEL_EXPERTS.keys())

        explicit = command.parameters.get('experts')
        if isinstance(explicit, str) and explicit.strip():
            return self._normalize_expert_identifiers(explicit)

        focus_candidates = BUSINESS_PANEL_FOCUS_MAP.get(focus)
        if focus_candidates:
            return focus_candidates

        return DEFAULT_BUSINESS_PANEL_EXPERTS

    def _normalize_expert_identifiers(self, raw_value: str) -> List[str]:
        """Normalize a comma or space separated list of expert identifiers."""
        tokens = [token.strip().lower() for token in raw_value.replace(';', ',').split(',') if token.strip()]
        resolved: List[str] = []

        alias_map: Dict[str, str] = {}
        for expert_id, data in BUSINESS_PANEL_EXPERTS.items():
            alias_map[expert_id] = expert_id
            alias_map[data['name'].lower()] = expert_id
            alias_map[data['name'].split()[0].lower()] = expert_id

        for token in tokens:
            key = alias_map.get(token)
            if key and key not in resolved:
                resolved.append(key)

        return resolved if resolved else DEFAULT_BUSINESS_PANEL_EXPERTS

    def _determine_business_panel_phases(self, mode: str) -> List[str]:
        """Return the phases the panel will run based on mode."""
        phase_map = {
            'discussion': ['discussion'],
            'debate': ['discussion', 'debate'],
            'socratic': ['socratic'],
            'adaptive': ['discussion', 'debate', 'socratic']
        }
        return phase_map.get(mode, ['discussion'])

    def _generate_business_panel_insights(
        self,
        topic: str,
        expert_ids: List[str],
        focus: str
    ) -> List[Dict[str, Any]]:
        """Generate synthesized insights for each expert."""
        insights: List[Dict[str, Any]] = []
        for expert_id in expert_ids:
            expert = BUSINESS_PANEL_EXPERTS[expert_id]
            headline = f"{expert['name']} signals {expert['focus'][0] if expert['focus'] else 'strategic'} priority for {topic}"
            insights.append({
                'expert': expert['name'],
                'headline': headline,
                'lens': expert['lens'],
                'questions': expert['questions'],
                'focus_points': expert['focus'],
                'focus_alignment': focus
            })
        return insights

    def _generate_business_panel_recommendations(
        self,
        topic: str,
        insights: List[Dict[str, Any]],
        focus: str
    ) -> List[str]:
        """Create actionable recommendations from the panel insights."""
        recommendations: List[str] = []
        if focus != 'general':
            recommendations.append(f"Establish success metrics for {focus} around '{topic}'.")

        if insights:
            lead = insights[0]
            recommendations.append(
                f"Activate a focused workstream led by {lead['expert']} to pressure-test {topic} against the primary lens: {lead['lens']}."
            )

        recommendations.append("Capture debate outcomes and assign owners for the top three decision points.")
        return recommendations

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
            elif path.suffix == '.json':
                try:
                    json.loads(path.read_text(encoding='utf-8'))
                except json.JSONDecodeError as exc:
                    issues.append(f"{rel_path}: invalid JSON — {exc}")
                except Exception as exc:
                    issues.append(f"{rel_path}: json validation failed — {exc}")
            elif path.suffix in {'.yaml', '.yml'}:
                try:
                    yaml.safe_load(path.read_text(encoding='utf-8'))
                except yaml.YAMLError as exc:
                    issues.append(f"{rel_path}: invalid YAML — {exc}")
                except Exception as exc:
                    issues.append(f"{rel_path}: yaml validation failed — {exc}")

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

    def _maybe_run_quality_loop(
        self,
        context: CommandContext,
        output: Any
    ) -> Optional[Dict[str, Any]]:
        """Execute the quality scorer's agentic loop when requested."""
        if context.results.get('loop_assessment'):
            return None

        max_iterations = context.loop_iterations or self.quality_scorer.MAX_ITERATIONS
        min_improvement = context.loop_min_improvement

        def _identity_improver(current_output: Any, loop_context: Dict[str, Any]) -> Any:
            loop_context.setdefault('notes', []).append(
                'No automated remediation implemented; returning original output.'
            )
            return current_output

        try:
            improved_output, final_assessment, iteration_history = self.quality_scorer.agentic_loop(
                output,
                dict(context.results),
                improver_func=_identity_improver,
                max_iterations=max_iterations,
                min_improvement=min_improvement
            )
        except Exception as exc:
            logger.warning(f"Agentic loop execution failed: {exc}")
            context.results['loop_error'] = str(exc)
            return None

        context.results['loop_iterations_executed'] = len(iteration_history)
        context.results['loop_assessment'] = self._serialize_assessment(final_assessment)
        context.results['quality_iteration_history'] = [
            asdict(item) for item in iteration_history
        ]
        context.results.setdefault('loop_notes', []).append(
            'Quality loop executed with identity improver (placeholder).'
        )

        return {
            'output': improved_output,
            'assessment': final_assessment
        }

    def _evaluate_quality_gate(
        self,
        context: CommandContext,
        output: Any,
        changed_paths: List[Path],
        status: str,
        precomputed: Optional[QualityAssessment] = None
    ) -> Optional[QualityAssessment]:
        """Run quality scoring against the command result."""
        evaluation_context = dict(context.results)
        evaluation_context['status'] = status
        evaluation_context['changed_files'] = [
            self._relative_to_repo_path(path) for path in changed_paths
        ]

        try:
            assessment = precomputed or self.quality_scorer.evaluate(
                output,
                evaluation_context
            )
            if assessment and not assessment.passed:
                if precomputed:
                    return assessment

                def _noop_improver(current_output, loop_context):
                    loop_context.setdefault('notes', []).append('No automated remediation available.')
                    return current_output

                (
                    _,
                    loop_assessment,
                    iteration_history
                ) = self.quality_scorer.agentic_loop(
                    output,
                    evaluation_context,
                    improver_func=_noop_improver
                )

                if iteration_history:
                    context.results['quality_iteration_history'] = [
                        asdict(item) for item in iteration_history
                    ]

                return loop_assessment

            return assessment
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
        static_issues: List[str],
        consensus: Optional[Dict[str, Any]]
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

        if consensus:
            consensus_tags = dict(tags)
            consensus_tags['consensus'] = str(consensus.get('consensus_reached', False))
            decision = consensus.get('final_decision')
            if decision is not None:
                consensus_tags['decision'] = str(decision)
            self.monitor.record_metric(f"{base}.consensus", 1, MetricType.COUNTER, consensus_tags)
            if not consensus.get('consensus_reached', False):
                self.monitor.record_metric(
                    f"{base}.consensus_failed",
                    1,
                    MetricType.COUNTER,
                    consensus_tags
                )

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

    def _prepare_mode(self, parsed: ParsedCommand) -> Dict[str, Any]:
        """Determine and apply the behavioral mode for a command."""
        detection_context = {
            'command': parsed.name,
            'flags': ' '.join(sorted(parsed.flags.keys())),
            'task': ' '.join(parsed.arguments),
            'parameters': json.dumps(parsed.parameters, sort_keys=True, default=str)
            if parsed.parameters else ''
        }

        # Always reset to normal before detection to avoid state bleed.
        self.behavior_manager.switch_mode(
            BehavioralMode.NORMAL,
            detection_context,
            trigger="reset"
        )

        detected_mode = self.behavior_manager.detect_mode_from_context(detection_context)
        if detected_mode:
            self.behavior_manager.switch_mode(detected_mode, detection_context, trigger="auto")

        applied = self.behavior_manager.apply_mode_behaviors(detection_context)
        return {
            'mode': self.behavior_manager.get_current_mode().value,
            'context': applied
        }

    def _apply_execution_flags(self, context: CommandContext) -> None:
        """Apply execution flags such as think depth, loops, consensus, and delegation."""
        parsed = context.command

        think_info = self._resolve_think_level(parsed)
        context.think_level = think_info['level']
        context.results['think_level'] = think_info['level']
        context.results['think_requested'] = think_info['requested']

        loop_info = self._resolve_loop_request(parsed)
        context.loop_enabled = loop_info['enabled']
        context.loop_iterations = loop_info['iterations']
        context.loop_min_improvement = loop_info['min_improvement']
        if loop_info['enabled']:
            context.results['loop_requested'] = True
            if loop_info['iterations'] is not None:
                context.results['loop_iterations_requested'] = loop_info['iterations']
            if loop_info['min_improvement'] is not None:
                context.results['loop_min_improvement_requested'] = loop_info['min_improvement']

        context.consensus_forced = self._flag_present(parsed, 'consensus')
        context.results['consensus_forced'] = context.consensus_forced

        self._apply_auto_delegation(context)

    def _resolve_think_level(self, parsed: ParsedCommand) -> Dict[str, Any]:
        """Resolve requested think level (1-3) from command flags/parameters."""
        default_level = 2
        requested = self._flag_present(parsed, 'think')

        candidate_keys = ['think', 'think_level', 'think-depth', 'think_depth', 'depth']
        value = None
        for key in candidate_keys:
            if key in parsed.parameters:
                value = parsed.parameters[key]
                break

        if value is None and requested:
            value = 3

        if value is None:
            level = default_level
        else:
            level = self._clamp_int(value, 1, 3, default_level)

        return {
            'level': level,
            'requested': requested or value is not None
        }

    def _resolve_loop_request(self, parsed: ParsedCommand) -> Dict[str, Any]:
        """Determine whether agentic loop is requested and capture limits."""
        enabled = self._flag_present(parsed, 'loop')
        iterations = None
        min_improvement = None

        iteration_keys = ['loop', 'loop_iterations', 'loop-count', 'loop_count']
        for key in iteration_keys:
            if key in parsed.parameters:
                iterations = self._clamp_int(
                    parsed.parameters[key],
                    1,
                    self.quality_scorer.MAX_ITERATIONS,
                    self.quality_scorer.MAX_ITERATIONS
                )
                enabled = True
                break

        min_keys = ['loop-min', 'loop_min', 'loop-improvement', 'loop_improvement']
        for key in min_keys:
            if key in parsed.parameters:
                min_improvement = self._coerce_float(parsed.parameters[key], None)
                enabled = True
                break

        return {
            'enabled': enabled,
            'iterations': iterations,
            'min_improvement': min_improvement
        }

    def _apply_auto_delegation(self, context: CommandContext) -> None:
        """Handle --delegate and related auto-delegation flags."""
        parsed = context.command

        explicit_targets = self._extract_delegate_targets(parsed)
        if explicit_targets:
            selected = self._deduplicate(explicit_targets)
            context.delegated_agents.extend(selected)
            context.delegated_agents = self._deduplicate(context.delegated_agents)
            context.delegation_strategy = 'explicit'
            context.results['delegation'] = {
                'requested': True,
                'strategy': 'explicit',
                'selected_agent': selected[0] if selected else None,
                'selected_agents': selected
            }
            context.results['delegated_agents'] = context.delegated_agents
            return

        delegate_flags = [
            'delegate',
            'delegate_core',
            'delegate-core',
            'delegate_extended',
            'delegate-extended',
            'delegate_debug',
            'delegate-debug',
            'delegate_refactor',
            'delegate-refactor',
            'delegate_search',
            'delegate-search'
        ]
        if not any(self._flag_present(parsed, flag) for flag in delegate_flags):
            return

        strategy = 'auto'
        if self._flag_present(parsed, 'delegate_extended') or self._flag_present(parsed, 'delegate-extended'):
            strategy = 'extended'
        elif self._flag_present(parsed, 'delegate_core') or self._flag_present(parsed, 'delegate-core'):
            strategy = 'core'
        elif self._flag_present(parsed, 'delegate_debug') or self._flag_present(parsed, 'delegate-debug'):
            strategy = 'debug'
        elif self._flag_present(parsed, 'delegate_refactor') or self._flag_present(parsed, 'delegate-refactor'):
            strategy = 'refactor'
        elif self._flag_present(parsed, 'delegate_search') or self._flag_present(parsed, 'delegate-search'):
            strategy = 'search'

        category_hint = None
        for key, category in self.delegate_category_map.items():
            if self._flag_present(parsed, key):
                category_hint = category
                break

        selection_context = self._build_delegation_context(context)

        try:
            matches = self.extended_agent_loader.select_agent(
                selection_context,
                category_hint=category_hint,
                top_n=5
            )
        except Exception as exc:
            logger.warning(f"Delegation selection failed: {exc}")
            context.results['delegation'] = {
                'requested': True,
                'strategy': strategy,
                'error': str(exc)
            }
            return

        if strategy == 'extended':
            matches = [
                match for match in matches
                if self._is_extended_agent(match.agent_id)
            ] or matches

        if not matches:
            context.results['delegation'] = {
                'requested': True,
                'strategy': strategy,
                'error': 'No matching agents found'
            }
            return

        primary = matches[0]
        context.delegated_agents.append(primary.agent_id)
        context.delegated_agents = self._deduplicate(context.delegated_agents)
        context.delegation_strategy = strategy

        context.results['delegation'] = {
            'requested': True,
            'strategy': strategy,
            'selected_agent': primary.agent_id,
            'confidence': primary.confidence,
            'score': round(primary.total_score, 3),
            'matched_criteria': primary.matched_criteria,
            'candidates': [
                {
                    'agent': match.agent_id,
                    'score': round(match.total_score, 3),
                    'confidence': match.confidence
                }
                for match in matches[:3]
            ],
            'selection_context': {
                'task': selection_context.get('task', '')[:120],
                'keywords': selection_context.get('keywords', [])[:5],
                'domains': selection_context.get('domains', [])[:5],
                'languages': selection_context.get('languages', [])[:5],
            }
        }
        context.results['delegated_agents'] = context.delegated_agents

    def _build_delegation_context(self, context: CommandContext) -> Dict[str, Any]:
        """Construct context payload for delegate selection."""
        parsed = context.command
        task_text = ' '.join(parsed.arguments).strip() or parsed.raw_string
        parameters = parsed.parameters

        languages = self._to_list(
            parameters.get('language') or parameters.get('languages') or parameters.get('lang')
        )
        domains = self._to_list(parameters.get('domain') or parameters.get('domains'))
        if context.metadata.category and context.metadata.category not in domains:
            domains.append(context.metadata.category)

        keywords = self._to_list(parameters.get('keywords') or parameters.get('tags'))
        if task_text:
            keywords.extend([
                word.strip(',.').lower()
                for word in task_text.split()
                if len(word) > 3
            ])

        files = self._extract_files_from_parameters(parameters)

        return {
            'task': task_text,
            'languages': languages,
            'domains': domains,
            'keywords': self._deduplicate(keywords),
            'files': files,
            'mode': context.behavior_mode,
        }

    def _extract_files_from_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Extract file or path hints from command parameters."""
        files: List[str] = []
        keys = ['file', 'files', 'path', 'paths', 'target', 'targets', 'module', 'modules']
        for key in keys:
            if key in parameters:
                files.extend(self._to_list(parameters[key]))
        return self._deduplicate([f for f in files if f])

    def _extract_delegate_targets(self, parsed: ParsedCommand) -> List[str]:
        """Extract explicit delegate targets provided by the user."""
        values: List[str] = []
        keys = [
            'delegate',
            'delegate_to',
            'delegate-to',
            'delegate_agent',
            'delegate-agent',
            'agents',
        ]
        for key in keys:
            if key in parsed.parameters:
                raw = parsed.parameters[key]
                if isinstance(raw, list):
                    values.extend(str(item) for item in raw)
                elif raw is not None:
                    values.extend(str(part).strip() for part in str(raw).split(','))
        return [value for value in (v.strip() for v in values) if value]

    def _flag_present(self, parsed: ParsedCommand, name: str) -> bool:
        """Check whether a flag or parameter is present and truthy."""
        if name in parsed.flags:
            return bool(parsed.flags[name])
        alias = name.replace('-', '_')
        if alias in parsed.flags:
            return bool(parsed.flags[alias])

        for lookup in (name, alias):
            if lookup in parsed.parameters:
                value = parsed.parameters[lookup]
                if isinstance(value, bool):
                    return value
                if isinstance(value, (int, float)):
                    return bool(value)
                if isinstance(value, str) and value.lower() in {'true', 'yes', '1', 'force', 'auto'}:
                    return True
        return False

    def _coerce_float(self, value: Any, default: Optional[float]) -> Optional[float]:
        """Best-effort float coercion."""
        try:
            if isinstance(value, bool):
                return 1.0 if value else 0.0
            return float(value)
        except (TypeError, ValueError):
            return default

    def _clamp_int(self, value: Any, minimum: int, maximum: int, default: int) -> int:
        """Coerce to int and clamp within bounds."""
        try:
            if isinstance(value, bool):
                intval = 1 if value else 0
            else:
                intval = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, intval))

    def _to_list(self, value: Any) -> List[str]:
        """Normalize value into a list of strings."""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, (set, tuple)):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        if ',' in text:
            return [part.strip() for part in text.split(',') if part.strip()]
        return [text]

    def _is_extended_agent(self, agent_id: str) -> bool:
        """Determine if an agent belongs to the extended catalogue."""
        metadata = getattr(self.extended_agent_loader, "_agent_metadata", {}).get(agent_id)
        if not metadata:
            return False
        return metadata.category != AgentCategory.CORE_DEVELOPMENT

    def _run_agent_pipeline(self, context: CommandContext) -> Dict[str, List[str]]:
        """Execute loaded agents and aggregate their outputs."""
        if not context.agent_instances:
            return {'operations': [], 'notes': [], 'warnings': []}

        task_description = ' '.join(context.command.arguments).strip()
        if not task_description:
            task_description = context.command.raw_string

        aggregated_operations: List[str] = []
        aggregated_notes: List[str] = []
        aggregated_warnings: List[str] = []

        agent_payload = {
            'task': task_description,
            'command': context.command.name,
            'flags': sorted(context.command.flags.keys()),
            'parameters': context.command.parameters,
            'mode': context.behavior_mode,
            'mode_context': context.results.get('mode', {}),
        }

        for agent_name, agent in context.agent_instances.items():
            try:
                result = agent.execute(agent_payload)
            except Exception as exc:
                warning = f"{agent_name}: execution error — {exc}"
                logger.error(warning)
                context.errors.append(warning)
                aggregated_warnings.append(warning)
                continue

            context.agent_outputs[agent_name] = result
            actions = self._normalize_evidence_value(result.get('actions_taken'))
            plans = self._normalize_evidence_value(result.get('planned_actions'))
            warnings = self._normalize_evidence_value(result.get('warnings'))
            output_text = str(result.get('output') or '').strip()

            aggregated_operations.extend(actions)
            aggregated_operations.extend(plans)
            aggregated_warnings.extend(warnings)
            note = output_text or "; ".join(plans) or "Provided guidance only."
            aggregated_notes.append(f"{agent_name}: {note}")

        dedup_ops = self._deduplicate(aggregated_operations)
        dedup_notes = self._deduplicate(aggregated_notes)
        dedup_warnings = self._deduplicate(aggregated_warnings)

        context.results.setdefault('agent_operations', []).extend(dedup_ops)
        context.results.setdefault('agent_notes', []).extend(dedup_notes)
        if dedup_warnings:
            context.results.setdefault('agent_warnings', []).extend(dedup_warnings)

        return {
            'operations': dedup_ops,
            'notes': dedup_notes,
            'warnings': dedup_warnings,
        }

    def _record_artifact(
        self,
        context: CommandContext,
        command_name: str,
        summary: str,
        operations: Iterable[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Persist an artifact and register it with the context."""
        record = self.artifact_manager.record_summary(
            command_name,
            summary,
            operations=operations,
            metadata=metadata or {}
        )

        if not record:
            return None

        rel_path = self._relative_to_repo_path(record.path)
        context.results.setdefault('artifacts', []).append(rel_path)
        context.results.setdefault('executed_operations', []).append(
            f"artifact created: {rel_path}"
        )
        context.artifact_records.append({
            'path': rel_path,
            'metadata': record.metadata,
        })
        return rel_path

    def _build_consensus_prompt(self, context: CommandContext, output: Any) -> str:
        """Construct a deterministic prompt for consensus evaluation."""
        lines = [
            f"Command: /sc:{context.command.name}",
            f"Mode: {context.behavior_mode}",
            f"Flags: {' '.join(sorted(context.command.flags.keys())) or 'none'}",
            f"Arguments: {' '.join(context.command.arguments) or 'none'}",
        ]

        summary = ""
        if isinstance(output, dict):
            summary = str(output.get('summary') or output.get('output') or '')
        if not summary:
            summary = str(context.results.get('primary_summary') or '')
        if not summary:
            summary = context.command.raw_string
        lines.append("Summary:")
        lines.append(summary.strip())

        agent_notes = context.results.get('agent_notes') or []
        if agent_notes:
            lines.append("Agent Findings:")
            lines.extend(f"- {note}" for note in agent_notes)

        operations = context.results.get('agent_operations') or []
        if operations:
            lines.append("Operations:")
            lines.extend(f"- {op}" for op in operations)

        return "\n".join(lines)

    async def _ensure_consensus(
        self,
        context: CommandContext,
        output: Any,
        *,
        enforce: bool = False,
        think_level: Optional[int] = None,
        task_type: str = "consensus"
    ) -> Dict[str, Any]:
        """Run consensus builder and attach the result to the context."""
        prompt = self._build_consensus_prompt(context, output)
        try:
            result = await self.consensus_facade.run_consensus(
                prompt,
                context=context.results,
                think_level=think_level,
                task_type=task_type
            )
        except Exception as exc:
            message = f"Consensus evaluation failed: {exc}"
            logger.error(message)
            context.errors.append(message)
            result = {'consensus_reached': False, 'error': str(exc)}

        context.consensus_summary = result
        context.results['consensus'] = result
        if result.get('routing_decision'):
            context.results['routing_decision'] = result['routing_decision']
        if result.get('models'):
            context.results['consensus_models'] = result['models']
        if result.get('think_level') is not None:
            context.results['consensus_think_level'] = result['think_level']

        if enforce and not result.get('consensus_reached', False):
            message = "Consensus not reached; additional review required."
            if result.get('error'):
                message = f"Consensus failed: {result['error']}"
            context.errors.append(message)
            if isinstance(output, dict):
                warnings_list = self._ensure_list(output, 'warnings')
                if message not in warnings_list:
                    warnings_list.append(message)

        return result

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
