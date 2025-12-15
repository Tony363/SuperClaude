"""
Command Executor for SuperClaude Framework.

Orchestrates command execution with agent and MCP server integration.
"""

import ast
import asyncio
import builtins
import copy
import importlib.util
import json
import logging
import os
import py_compile
import re
import shutil
import subprocess
import textwrap
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:  # Optional dependency used for config parsing
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional extras
    yaml = None  # type: ignore

from ..Agents import usage_tracker as agent_usage_tracker
from ..Agents.extended_loader import AgentCategory, ExtendedAgentLoader
from ..Agents.loader import AgentLoader
from ..Agents.registry import AgentRegistry
from ..APIClients.codex_cli import CodexCLIClient, CodexCLIUnavailable
from ..Core.worktree_manager import WorktreeManager
from ..MCP import get_mcp_integration
from ..ModelRouter.consensus import VoteType
from ..ModelRouter.facade import ModelRouterFacade
from ..Modes.behavioral_manager import BehavioralMode, BehavioralModeManager
from ..Quality.quality_scorer import (
    QualityAssessment,
    QualityDimension,
    QualityMetric,
    QualityScorer,
)
from .artifact_manager import CommandArtifactManager
from .parser import CommandParser, ParsedCommand
from .registry import CommandMetadata, CommandRegistry

logger = logging.getLogger(__name__)


# Stub for removed Monitoring module
class MetricType:
    COUNTER = "counter"
    GAUGE = "gauge"
    TIMER = "timer"


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
    active_personas: List[str] = field(default_factory=list)
    fast_codex_requested: bool = False
    fast_codex_active: bool = False
    fast_codex_blocked: List[str] = field(default_factory=list)
    zen_review_enabled: bool = False
    zen_review_model: str = "gpt-5"


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
    status: str = "plan-only"


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

    def __init__(
        self,
        registry: CommandRegistry,
        parser: CommandParser,
        repo_root: Optional[Path] = None,
    ):
        """
        Initialize command executor.

        Args:
            registry: CommandRegistry instance
            parser: CommandParser instance
            repo_root: Optional root of the target repository; defaults to detected git root
        """
        self.registry = registry
        self.parser = parser
        self.execution_history: List[CommandResult] = []
        self.active_mcp_servers: Dict[str, Any] = {}
        self.hooks: Dict[str, List[Callable]] = {
            "pre_execute": [],
            "post_execute": [],
            "on_error": [],
        }
        self.repo_root = self._normalize_repo_root(repo_root)
        if self.repo_root:
            # Export for downstream helpers (metrics, monitoring, etc.) without clobbering user choice
            os.environ.setdefault("SUPERCLAUDE_REPO_ROOT", str(self.repo_root))
            os.environ.setdefault(
                "SUPERCLAUDE_METRICS_DIR", str(self.repo_root / ".superclaude_metrics")
            )
        base_path = self.repo_root or Path.cwd()
        self.agent_loader: AgentLoader = AgentLoader()
        self.extended_agent_loader: ExtendedAgentLoader = ExtendedAgentLoader()
        self.behavior_manager = BehavioralModeManager()
        self.artifact_manager = CommandArtifactManager(
            base_path / "SuperClaude" / "Generated"
        )
        self.consensus_facade = ModelRouterFacade()
        self.consensus_policies = self._load_consensus_policies()
        self.quality_scorer = QualityScorer()
        self.retriever = None  # Retrieval module removed
        self.delegate_category_map = {
            "delegate_core": AgentCategory.CORE_DEVELOPMENT,
            "delegate-debug": AgentCategory.QUALITY_SECURITY,
            "delegate_refactor": AgentCategory.CORE_DEVELOPMENT,
            "delegate-refactor": AgentCategory.CORE_DEVELOPMENT,
            "delegate_search": AgentCategory.DEVELOPER_EXPERIENCE,
            "delegate-search": AgentCategory.DEVELOPER_EXPERIENCE,
        }
        try:
            self.monitor = None  # Monitoring removed
        except Exception as exc:
            logger.debug(f"Performance monitor unavailable: {exc}")
            self.monitor = None

        try:
            self.worktree_manager = WorktreeManager(str(self.repo_root or Path.cwd()))
        except Exception as exc:
            logger.debug(f"Worktree manager unavailable: {exc}")
            self.worktree_manager = None

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
                    errors=[f"Command '{parsed.name}' not found"],
                )
            metadata = copy.deepcopy(metadata)

            mode_state = self._prepare_mode(parsed)

            # Create execution context
            context = CommandContext(
                command=parsed,
                metadata=metadata,
                session_id=self._generate_session_id(),
                behavior_mode=mode_state["mode"],
            )
            context.results["mode"] = mode_state["context"]
            context.results["behavior_mode"] = mode_state["mode"]
            context.results.setdefault("executed_operations", [])
            context.results.setdefault("applied_changes", [])
            context.results.setdefault("artifacts", [])
            context.results.setdefault("flags", sorted(context.command.flags.keys()))

            self._apply_execution_flags(context)

            # Run pre-execution hooks
            await self._run_hooks("pre_execute", context)

            # Activate required MCP servers
            await self._activate_mcp_servers(context)

            # Select and load required agents
            await self._load_agents(context)
            if context.fast_codex_active and not context.agent_instances:
                context.fast_codex_blocked.append("agent-unavailable")
                context.fast_codex_active = False
                context.results["execution_mode"] = "standard"
                context.active_personas = list(context.metadata.personas or [])
                context.results["fast_codex"] = {
                    "requested": True,
                    "active": False,
                    "personas": context.active_personas,
                    "blocked": context.fast_codex_blocked,
                }
                await self._load_agents(context)

            pre_change_snapshot = self._snapshot_repo_changes()

            # Execute command logic
            output = await self._execute_command_logic(context)

            loop_assessment: Optional[QualityAssessment] = None
            if context.loop_enabled:
                loop_result = self._maybe_run_quality_loop(context, output)
                if loop_result:
                    output = loop_result["output"]
                    loop_assessment = loop_result["assessment"]
                await self._run_zen_reviews(context, output)

            consensus_required = metadata.requires_evidence or context.consensus_forced
            consensus_result = await self._ensure_consensus(
                context,
                output,
                enforce=consensus_required,
                think_level=context.think_level,
            )
            if isinstance(output, dict):
                output["consensus"] = consensus_result

            test_results = None
            explicit_tests_requested = self._should_run_tests(parsed)
            requires_evidence_auto = (
                metadata.requires_evidence and parsed.name != "test"
            )
            auto_run_tests = explicit_tests_requested or requires_evidence_auto
            if auto_run_tests:
                running_in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
                should_skip_due_to_pytest = (
                    running_in_pytest
                    and requires_evidence_auto
                    and not explicit_tests_requested
                )
                if not should_skip_due_to_pytest:
                    test_results = self._run_requested_tests(parsed)
                else:
                    test_results = {
                        "command": "pytest (suppressed inside existing pytest session)",
                        "args": ["pytest"],
                        "passed": True,
                        "pass_rate": 1.0,
                        "stdout": "Auto-test run skipped because PYTEST_CURRENT_TEST is set.",
                        "stderr": "",
                        "duration_s": 0.0,
                        "exit_code": 0,
                        "coverage": None,
                        "summary": "pytest run skipped inside pytest harness",
                        "tests_passed": 0,
                        "tests_failed": 0,
                        "tests_errored": 0,
                        "tests_skipped": 0,
                        "tests_collected": 0,
                        "markers": [],
                        "targets": [],
                        "skipped": True,
                    }

                context.results["test_results"] = test_results
                test_artifact = self._record_test_artifact(
                    context, parsed, test_results
                )
                if test_artifact:
                    test_artifacts = context.results.setdefault("test_artifacts", [])
                    if test_artifact not in test_artifacts:
                        test_artifacts.append(test_artifact)
                if isinstance(output, dict):
                    output["test_results"] = test_results
                    if test_artifact:
                        test_list = output.setdefault("test_artifacts", [])
                        if test_artifact not in test_list:
                            test_list.append(test_artifact)
                if not test_results.get("passed", False):
                    context.errors.append("Automated tests failed")

            post_change_snapshot = self._snapshot_repo_changes()
            repo_change_entries = self._diff_snapshots(
                pre_change_snapshot, post_change_snapshot
            )
            artifact_entries, evidence_entries = self._partition_change_entries(
                repo_change_entries
            )
            artifact_descriptions = [
                self._format_change_entry(entry) for entry in artifact_entries
            ]
            repo_change_descriptions = [
                self._format_change_entry(entry) for entry in evidence_entries
            ]
            diff_stats = self._collect_diff_stats()

            executed_operations: List[str] = []
            applied_changes: List[str] = []

            if isinstance(output, dict):
                executed_operations.extend(
                    self._extract_output_evidence(output, "executed_operations")
                )
                executed_operations.extend(
                    self._extract_output_evidence(output, "actions_taken")
                )
                executed_operations.extend(
                    self._extract_output_evidence(output, "commands_run")
                )
                applied_changes.extend(
                    self._extract_output_evidence(output, "applied_changes")
                )
                applied_changes.extend(
                    self._extract_output_evidence(output, "files_modified")
                )

            executed_operations.extend(
                self._normalize_evidence_value(
                    context.results.get("executed_operations")
                )
            )
            applied_changes.extend(
                self._normalize_evidence_value(context.results.get("applied_changes"))
            )

            if repo_change_descriptions:
                applied_changes.extend(repo_change_descriptions)
            if artifact_descriptions:
                artifact_log = context.results.setdefault("artifact_changes", [])
                artifact_log.extend(artifact_descriptions)
                context.results["artifact_changes"] = self._deduplicate(artifact_log)
            if diff_stats:
                context.results["diff_stats"] = diff_stats
                if isinstance(output, dict):
                    output["diff_stats"] = diff_stats

            if test_results:
                executed_operations.append(self._summarize_test_results(test_results))
                if test_results.get("stdout"):
                    executed_operations.append(
                        f"tests stdout: {test_results['stdout']}"
                    )
                if test_results.get("stderr"):
                    executed_operations.append(
                        f"tests stderr: {test_results['stderr']}"
                    )

            executed_operations = self._deduplicate(executed_operations)
            applied_changes = self._deduplicate(applied_changes)

            derived_status = "executed" if applied_changes else "plan-only"
            if context.errors:
                derived_status = "failed"

            if isinstance(output, dict):
                output["executed_operations"] = executed_operations
                output["applied_changes"] = applied_changes
                if context.results.get("artifacts"):
                    output["artifacts"] = context.results["artifacts"]
                if context.results.get("artifact_changes"):
                    output["artifact_changes"] = context.results["artifact_changes"]
                output.setdefault("mode", context.behavior_mode)
                if context.consensus_summary is not None:
                    output.setdefault("consensus", context.consensus_summary)
                if context.results.get("delegation"):
                    output.setdefault("delegation", context.results["delegation"])
                output.setdefault("think_level", context.think_level)
                if context.loop_enabled:
                    output.setdefault(
                        "loop",
                        {
                            "requested": True,
                            "max_iterations": context.loop_iterations
                            or self.quality_scorer.MAX_ITERATIONS,
                            "iterations_executed": context.results.get(
                                "loop_iterations_executed", 0
                            ),
                            "assessment": context.results.get("loop_assessment"),
                        },
                    )
                if context.results.get("routing_decision"):
                    output.setdefault(
                        "routing_decision", context.results["routing_decision"]
                    )

                existing_status = output.get("status")
                output.setdefault("execution_status", derived_status)
                if existing_status in {None, "executed", "plan-only"}:
                    output["status"] = derived_status
                elif existing_status == "failed":
                    pass
                else:
                    output.setdefault("status_detail", derived_status)

            context.results["executed_operations"] = executed_operations
            context.results["applied_changes"] = applied_changes
            context.results["status"] = derived_status

            requires_evidence = self._requires_execution_evidence(context.metadata)
            quality_assessment: Optional[QualityAssessment] = None
            static_issues: List[str] = []
            changed_paths: List[Path] = []
            context.results["requires_evidence"] = requires_evidence
            context.results["missing_evidence"] = (
                derived_status == "plan-only" if requires_evidence else False
            )

            if requires_evidence:
                changed_paths = self._extract_changed_paths(
                    evidence_entries, applied_changes
                )
                if changed_paths:
                    context.results["changed_files"] = [
                        self._relative_to_repo_path(path) for path in changed_paths
                    ]

                static_issues = self._run_static_validation(changed_paths)
                if static_issues:
                    static_issues = self._deduplicate(static_issues)
                    context.results["static_validation_errors"] = static_issues
                    context.errors.extend(static_issues)
                    if isinstance(output, dict):
                        validation_errors = self._ensure_list(
                            output, "validation_errors"
                        )
                        for issue in static_issues:
                            if issue not in validation_errors:
                                validation_errors.append(issue)

                quality_assessment = self._evaluate_quality_gate(
                    context,
                    output,
                    changed_paths,
                    derived_status,
                    precomputed=loop_assessment,
                )

                if quality_assessment:
                    serialized_assessment = self._serialize_assessment(
                        quality_assessment
                    )
                    context.results["quality_assessment"] = serialized_assessment
                    quality_artifact = self._record_quality_artifact(
                        context, quality_assessment
                    )
                    if quality_artifact:
                        quality_artifacts = context.results.setdefault(
                            "quality_artifacts", []
                        )
                        if quality_artifact not in quality_artifacts:
                            quality_artifacts.append(quality_artifact)
                    if isinstance(output, dict):
                        output["quality_assessment"] = serialized_assessment
                        if quality_artifact:
                            output["quality_artifact"] = quality_artifact

                    suggestions = self.quality_scorer.get_improvement_suggestions(
                        quality_assessment
                    )
                    context.results["quality_suggestions"] = suggestions
                    if isinstance(output, dict):
                        output["quality_suggestions"] = suggestions
                        iteration_history = context.results.get(
                            "quality_iteration_history"
                        )
                        if iteration_history:
                            output["quality_iteration_history"] = iteration_history

                    if not quality_assessment.passed:
                        failure_msg = (
                            f"Quality score {quality_assessment.overall_score:.1f} "
                            f"(threshold {quality_assessment.threshold:.1f})"
                        )
                        context.errors.append(failure_msg)
                        if isinstance(output, dict):
                            warnings_list = self._ensure_list(output, "warnings")
                            if failure_msg not in warnings_list:
                                warnings_list.append(failure_msg)
                            for suggestion in suggestions[:3]:
                                detail = f"Improve {suggestion.get('dimension', 'quality')} — {suggestion.get('suggestion', '')}"
                                if detail.strip() and detail not in warnings_list:
                                    warnings_list.append(detail)
                else:
                    if isinstance(output, dict):
                        warnings_list = self._ensure_list(output, "warnings")
                        detail = context.results.get("quality_assessment_error")
                        message = (
                            f"Quality scoring unavailable: {detail}"
                            if detail
                            else "Quality scoring unavailable; unable to verify evidence."
                        )
                        if message not in warnings_list:
                            warnings_list.append(message)

            success_flag = not bool(context.errors)

            if requires_evidence and derived_status == "plan-only":
                success_flag = False
                missing_evidence_msg = "Requires execution evidence but no repository changes were detected."
                if missing_evidence_msg not in context.errors:
                    context.errors.append(missing_evidence_msg)
                if quality_assessment:
                    adjusted_score = min(
                        quality_assessment.overall_score,
                        quality_assessment.threshold - 10.0,
                        69.0,
                    )
                    quality_assessment.overall_score = adjusted_score
                    quality_assessment.passed = False
                    serialized_assessment = self._serialize_assessment(
                        quality_assessment
                    )
                    context.results["quality_assessment"] = serialized_assessment
                    if isinstance(output, dict):
                        output["quality_assessment"] = serialized_assessment
                        iteration_history = context.results.get(
                            "quality_iteration_history"
                        )
                        output.setdefault(
                            "quality_iteration_history", iteration_history or []
                        )
                    failure_msg = (
                        f"Quality score {quality_assessment.overall_score:.1f} "
                        f"(threshold {quality_assessment.threshold:.1f})"
                    )
                    if failure_msg not in context.errors:
                        context.errors.append(failure_msg)
                if isinstance(output, dict):
                    warnings_list = self._ensure_list(output, "warnings")
                    warning_msg = "No concrete repository changes detected; returning plan-only status."
                    if warning_msg not in warnings_list:
                        warnings_list.append(warning_msg)
                    if missing_evidence_msg not in warnings_list:
                        warnings_list.append(missing_evidence_msg)
                    if quality_assessment:
                        if failure_msg not in warnings_list:
                            warnings_list.append(failure_msg)

            if derived_status == "plan-only":
                self._attach_plan_only_guidance(
                    context, output if isinstance(output, dict) else None
                )
                if self._should_auto_trigger_quality_loop(
                    context, derived_status
                ) and not context.results.get("loop_assessment"):
                    context.loop_enabled = True
                    context.results["loop_auto_triggered"] = True
                    loop_result = self._maybe_run_quality_loop(context, output)
                    if loop_result:
                        output = loop_result["output"]
                        loop_assessment = loop_result["assessment"]
                        if isinstance(output, dict):
                            loop_state = output.setdefault(
                                "loop",
                                {
                                    "requested": False,
                                    "auto_triggered": True,
                                    "max_iterations": context.loop_iterations
                                    or self.quality_scorer.MAX_ITERATIONS,
                                    "iterations_executed": context.results.get(
                                        "loop_iterations_executed", 0
                                    ),
                                    "assessment": context.results.get(
                                        "loop_assessment"
                                    ),
                                },
                            )
                            loop_state.setdefault("auto_triggered", True)
                            loop_state["iterations_executed"] = context.results.get(
                                "loop_iterations_executed", 0
                            )
                            loop_state["assessment"] = context.results.get(
                                "loop_assessment"
                            )
                        if loop_assessment and not quality_assessment:
                            quality_assessment = loop_assessment
                        await self._run_zen_reviews(context, output)

            context.errors = self._deduplicate(context.errors)

            self._maybe_record_plan_only_event(
                parsed, context, derived_status, requires_evidence
            )

            self._record_requires_evidence_metrics(
                parsed.name,
                requires_evidence,
                derived_status,
                success_flag,
                quality_assessment,
                static_issues,
                context.consensus_summary,
                dict(context.results),
            )

            # Dispatch any Rube automation once metrics have been recorded.
            rube_operations = await self._dispatch_rube_actions(context, output)
            if rube_operations:
                executed_operations.extend(rube_operations)
                if isinstance(output, dict):
                    integrations = output.setdefault("integrations", {})
                    existing_ops = self._ensure_list(integrations, "rube")
                    for op in rube_operations:
                        if op not in existing_ops:
                            existing_ops.append(op)

            # Run post-execution hooks
            await self._run_hooks("post_execute", context)

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
                artifacts=context.results.get("artifacts", []),
                consensus=context.consensus_summary,
                behavior_mode=context.behavior_mode,
                status=derived_status,
            )

            # Record in history
            self.execution_history.append(result)

            return result

        except Exception as e:
            logger.error(f"Command execution failed: {e}")

            # Run error hooks
            if "on_error" in self.hooks:
                for hook in self.hooks["on_error"]:
                    try:
                        await hook(e, command_str)
                    except:
                        pass

            return CommandResult(
                success=False,
                command_name=parsed.name if "parsed" in locals() else "unknown",
                output=None,
                errors=[str(e)],
                execution_time=(datetime.now() - start_time).total_seconds(),
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
            cfg_path = os.path.join(base_dir, "Config", "mcp.yaml")
            if os.path.exists(cfg_path):
                if yaml is None:
                    logger.warning("PyYAML missing; skipping MCP config load")
                else:
                    with open(cfg_path, encoding="utf-8") as f:
                        mcp_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load MCP config: {e}")

        server_configs = (
            (mcp_config.get("servers") or {}) if isinstance(mcp_config, dict) else {}
        )

        def _record_warning(message: str) -> None:
            warnings_list = context.results.setdefault("warnings", [])
            if message not in warnings_list:
                warnings_list.append(message)

        for server_name in required_servers:
            if server_name in self.active_mcp_servers:
                context.mcp_servers.append(server_name)
                continue

            try:
                cfg = (
                    server_configs.get(server_name, {})
                    if isinstance(server_configs, dict)
                    else {}
                )
                if not isinstance(cfg, dict):
                    cfg = {}

                enabled_flag = cfg.get("enabled", True)
                if not self._is_truthy(enabled_flag):
                    logger.info(
                        f"Skipping MCP server '{server_name}' because it is disabled in configuration."
                    )
                    _record_warning(f"MCP server '{server_name}' disabled")
                    continue

                requires_network = bool(cfg.get("requires_network", False))
                network_mode = os.getenv("SC_NETWORK_MODE", "offline").strip().lower()
                network_allowed = network_mode in {"online", "mixed", "rube", "auto"}

                if requires_network and not network_allowed:
                    logger.info(
                        "Skipping MCP server '%s' because network mode '%s' disallows outbound access.",
                        server_name,
                        network_mode or "offline",
                    )
                    _record_warning(
                        f"MCP server '{server_name}' unavailable (network mode)"
                    )
                    continue

                # Instantiate the integration. Prefer passing config if accepted.
                try:
                    instance = get_mcp_integration(server_name, config=cfg)
                except TypeError:
                    instance = get_mcp_integration(server_name)

                # Attempt basic initialization hooks if present
                init = getattr(instance, "initialize", None)
                init_session = getattr(instance, "initialize_session", None)
                if callable(init):
                    maybe = init()
                    if hasattr(maybe, "__await__"):
                        await maybe
                if callable(init_session):
                    maybe = (
                        init_session()
                    )  # often async for UnifiedStore-backed sessions
                    if hasattr(maybe, "__await__"):
                        await maybe

                self.active_mcp_servers[server_name] = {
                    "status": "active",
                    "activated_at": datetime.now(),
                    "instance": instance,
                    "config": cfg,
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

        required_personas = context.active_personas or context.metadata.personas or []

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
            context.results["delegated_agents"] = delegated
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
            "architect": "system-architect",
            "frontend": "frontend-architect",
            "backend": "backend-architect",
            "security": "security-engineer",
            "qa-specialist": "quality-engineer",
            "performance": "performance-engineer",
            "devops": "devops-architect",
            "python": "python-expert",
            "refactoring": "refactoring-expert",
            "documentation": "technical-writer",
            "codex-implementer": "codex-implementer",
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
        if command_name == "implement":
            return await self._execute_implement(context)
        elif command_name == "analyze":
            return await self._execute_analyze(context)
        elif command_name == "test":
            return await self._execute_test(context)
        elif command_name == "build":
            return await self._execute_build(context)
        elif command_name == "git":
            return await self._execute_git(context)
        elif command_name == "workflow":
            return await self._execute_workflow(context)
        else:
            # Generic execution for other commands
            return await self._execute_generic(context)

    async def _execute_implement(self, context: CommandContext) -> Dict[str, Any]:
        """Execute implementation command."""
        agent_result = self._run_agent_pipeline(context)

        codex_output = None
        codex_agent_output = context.agent_outputs.get("codex-implementer")
        if isinstance(codex_agent_output, dict):
            codex_output = codex_agent_output.get("codex_suggestions")
            if codex_output:
                context.results["codex_suggestions"] = codex_output
                change_count = len(codex_output.get("changes") or [])
                self._record_fast_codex_event(
                    context,
                    "codex-suggestions",
                    f"Codex proposed {change_count} change{'s' if change_count != 1 else ''}.",
                    {
                        "summary": codex_output.get("summary"),
                        "change_count": change_count,
                    },
                )
            elif context.fast_codex_active or context.fast_codex_requested:
                self._record_fast_codex_event(
                    context,
                    "codex-suggestions",
                    "Codex did not produce actionable changes.",
                )
            cli_meta = codex_agent_output.get("codex_cli")
            if cli_meta:
                fast_state = context.results.setdefault("fast_codex", {})
                fast_state.setdefault("requested", context.fast_codex_requested)
                fast_state.setdefault("active", context.fast_codex_active)
                fast_state.setdefault("personas", list(context.active_personas))
                cli_snapshot = {
                    "duration_s": cli_meta.get("duration_s"),
                    "returncode": cli_meta.get("returncode"),
                    "stdout_preview": self._truncate_fast_codex_stream(
                        cli_meta.get("stdout")
                    ),
                    "stderr_preview": self._truncate_fast_codex_stream(
                        cli_meta.get("stderr")
                    ),
                }
                fast_state["cli"] = cli_snapshot
                context.results["fast_codex"] = fast_state
                context.results["fast_codex_cli"] = True
                self._record_fast_codex_event(
                    context,
                    "cli-finished",
                    "Codex CLI completed.",
                    cli_snapshot,
                )
                if self.monitor:
                    try:
                        self.monitor and self.monitor.record_event(
                            "commands.fast_codex.cli",
                            {
                                "timestamp": datetime.now().isoformat(),
                                "duration_s": cli_meta.get("duration_s"),
                                "returncode": cli_meta.get("returncode"),
                            },
                        )
                        self.monitor and self.monitor.record_metric(
                            "commands.fast_codex.cli.duration",
                            float(cli_meta.get("duration_s", 0.0)),
                            MetricType.TIMER,
                            tags={"mode": "fast-codex"},
                        )
                    except Exception:
                        logger.debug(
                            "Failed to record fast-codex CLI telemetry", exc_info=True
                        )

        summary_lines = [
            f"Implementation request for: {' '.join(context.command.arguments) or 'unspecified scope'}",
            f"Mode: {context.behavior_mode}",
            f"Execution mode: {'fast-codex' if context.fast_codex_active else 'standard'}",
            f"Agents engaged: {', '.join(context.agents) or 'none'}",
        ]

        if agent_result["notes"]:
            summary_lines.append("")
            summary_lines.append("Agent insights:")
            summary_lines.extend(f"- {note}" for note in agent_result["notes"])

        if agent_result["operations"]:
            summary_lines.append("")
            summary_lines.append("Planned or executed operations:")
            summary_lines.extend(f"- {op}" for op in agent_result["operations"])

        if agent_result["warnings"]:
            summary_lines.append("")
            summary_lines.append("Warnings:")
            summary_lines.extend(f"- {warn}" for warn in agent_result["warnings"])

        summary = "\n".join(summary_lines).strip()
        context.results["primary_summary"] = summary

        metadata = {
            "mode": context.behavior_mode,
            "agents": context.agents,
            "session_id": context.session_id,
            "mcp_servers": context.mcp_servers,
        }
        artifact_path = self._record_artifact(
            context,
            context.command.name,
            summary,
            operations=agent_result["operations"],
            metadata=metadata,
        )

        change_plan = self._derive_change_plan(context, agent_result)
        context.results["change_plan"] = change_plan
        if context.fast_codex_requested:
            self._record_fast_codex_event(
                context,
                "change-plan",
                f"Derived change plan with {len(change_plan)} step{'s' if len(change_plan) != 1 else ''}.",
                {"steps": len(change_plan)},
            )

        if not change_plan:
            error = "Implementation aborted: no concrete change plan was generated."
            context.errors.append(error)
            warnings_list = context.results.setdefault("worktree_warnings", [])
            if error not in warnings_list:
                warnings_list.append(error)
            context.results["status"] = "failed"
            if context.fast_codex_requested:
                self._record_fast_codex_event(
                    context,
                    "change-plan-missing",
                    "Fast-codex run produced no change plan; aborting.",
                )

            output = {
                "status": "failed",
                "summary": summary,
                "agents": context.agents,
                "mcp_servers": context.mcp_servers,
                "parameters": context.command.parameters,
                "artifact": artifact_path,
                "agent_notes": agent_result["notes"],
                "agent_warnings": agent_result["warnings"],
                "mode": context.behavior_mode,
                "execution_mode": "fast-codex"
                if context.fast_codex_active
                else "standard",
                "codex_suggestions": codex_output,
                "change_plan": [],
                "applied_files": [],
                "errors": [error],
            }
            output["fast_codex"] = context.results.get("fast_codex")
            if context.results.get("fast_codex_log"):
                output["fast_codex_log"] = context.results["fast_codex_log"]
            return output

        change_result = self._apply_change_plan(context, change_plan)
        change_warnings = change_result.get("warnings") or []
        applied_files = change_result.get("applied") or []
        if applied_files:
            applied_files = list(dict.fromkeys(applied_files))
        if context.fast_codex_requested:
            detail = {
                "applied_files": applied_files[:5],
                "applied_count": len(applied_files),
            }
            message = f"Applied {len(applied_files)} file{'s' if len(applied_files) != 1 else ''} to worktree."
            if not applied_files:
                message = "Codex change plan produced no applied files."
            self._record_fast_codex_event(context, "worktree-apply", message, detail)

        if change_warnings:
            warnings_list = context.results.setdefault("worktree_warnings", [])
            warnings_list.extend(change_warnings)
            context.results["worktree_warnings"] = self._deduplicate(warnings_list)

        if applied_files:
            applied_list = context.results.setdefault("applied_changes", [])
            applied_list.extend(f"apply {path}" for path in applied_files)
            context.results["applied_changes"] = self._deduplicate(applied_list)
        else:
            error = "Implementation produced a change plan but no repository updates were applied."
            context.errors.append(error)
            context.results.setdefault("worktree_warnings", []).append(error)

        context.results["worktree_session"] = change_result.get("session")

        status = "executed" if applied_files else "failed"

        output = {
            "status": status,
            "summary": summary,
            "agents": context.agents,
            "mcp_servers": context.mcp_servers,
            "parameters": context.command.parameters,
            "artifact": artifact_path,
            "agent_notes": agent_result["notes"],
            "agent_warnings": agent_result["warnings"],
            "mode": context.behavior_mode,
            "execution_mode": "fast-codex" if context.fast_codex_active else "standard",
            "codex_suggestions": codex_output,
            "change_plan": change_plan,
            "applied_files": applied_files,
            "worktree_session": change_result.get("session"),
        }
        output["fast_codex"] = context.results.get("fast_codex")
        if context.results.get("fast_codex_log"):
            output["fast_codex_log"] = context.results["fast_codex_log"]

        base_path = change_result.get("base_path")
        if base_path:
            output["worktree_base_path"] = base_path

        if change_warnings:
            output["worktree_warnings"] = self._deduplicate(change_warnings)

        if artifact_path:
            output["executed_operations"] = context.results.get("agent_operations", [])

        return output

    async def _execute_analyze(self, context: CommandContext) -> Dict[str, Any]:
        """Execute analysis command."""
        return {
            "status": "analysis_started",
            "scope": context.command.parameters.get("scope", "project"),
            "focus": context.command.parameters.get("focus", "all"),
            "mode": context.behavior_mode,
        }

    async def _execute_test(self, context: CommandContext) -> Dict[str, Any]:
        """Execute test command."""
        coverage = context.command.parameters.get("coverage", True)
        test_type = str(context.command.parameters.get("type", "all") or "all").lower()
        linkup_requested = (
            context.command.flags.get("linkup")
            or self._is_truthy(context.command.parameters.get("linkup"))
            or context.command.flags.get("browser")
            or self._is_truthy(context.command.parameters.get("browser"))
        )

        output: Dict[str, Any] = {
            "status": "tests_started",
            "coverage": coverage,
            "type": test_type,
            "mode": context.behavior_mode,
        }

        if linkup_requested:
            linkup_result = await self._execute_linkup_queries(
                context, scenario_hint=test_type
            )
            output["linkup"] = linkup_result
            status = linkup_result.get("status")
            if status == "linkup_failed":
                output["status"] = "tests_failed"
            else:
                output["status"] = "tests_with_linkup"

        return output

    async def _execute_linkup_queries(
        self, context: CommandContext, scenario_hint: str
    ) -> Dict[str, Any]:
        entry = self.active_mcp_servers.get("rube")
        if not entry:
            message = "LinkUp search requires the Rube MCP server to be active."
            context.errors.append(message)
            return {"status": "linkup_failed", "error": message}

        rube = entry.get("instance")
        if rube is None:
            message = "Rube MCP instance missing from activation registry."
            context.errors.append(message)
            return {"status": "linkup_failed", "error": message}

        queries = self._extract_linkup_queries(context)
        if not queries:
            message = (
                "LinkUp web search requires at least one query. "
                "Provide --linkup-query/--query or positional input."
            )
            context.errors.append(message)
            return {"status": "linkup_failed", "error": message}

        # Use RubeIntegration's built-in linkup_batch_search
        responses = await rube.linkup_batch_search(queries)

        aggregated: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []

        for idx, result in enumerate(responses):
            query_text = queries[idx]
            if isinstance(result, dict) and result.get("status") == "failed":
                error_message = str(result.get("error", "LinkUp request failed"))
                failures.append({"query": query_text, "error": error_message})
                aggregated.append(
                    {"query": query_text, "status": "failed", "error": error_message}
                )
                context.errors.append(f"LinkUp query failed: {error_message}")
                continue

            aggregated.append(
                {"query": query_text, "status": "completed", "response": result}
            )

        successes = sum(1 for item in aggregated if item.get("status") == "completed")
        status = "linkup_completed"
        if successes == 0:
            status = "linkup_failed"
        elif failures:
            status = "linkup_partial"

        exec_ops = context.results.setdefault("executed_operations", [])
        label = "linkup:search"
        if label not in exec_ops:
            exec_ops.append(label)

        context.results.setdefault("linkup_queries", []).extend(aggregated)
        if failures:
            context.results.setdefault("linkup_failures", []).extend(failures)

        return {
            "status": status,
            "scenario": scenario_hint.lower(),
            "queries": aggregated,
            "failures": failures,
        }

    def _extract_linkup_queries(self, context: CommandContext) -> List[str]:
        candidates: List[str] = []
        params = context.command.parameters or {}

        def _append(value: Any) -> None:
            if value is None:
                return
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    _append(item)
                return
            text = str(value).strip()
            if text:
                candidates.append(text)

        for key in ("linkup_query", "linkup_queries", "query", "queries"):
            _append(params.get(key))

        # Backward compatibility: treat --url as a query string.
        _append(params.get("url"))

        for argument in context.command.arguments:
            if isinstance(argument, str) and argument.startswith(
                ("http://", "https://")
            ):
                candidates.append(argument.strip())

        seen: Set[str] = set()
        ordered: List[str] = []
        for item in candidates:
            if item not in seen:
                seen.add(item)
                ordered.append(item)

        return ordered

    async def _execute_build(self, context: CommandContext) -> Dict[str, Any]:
        """Execute build command."""
        repo_root = Path(self.repo_root or Path.cwd())
        params = context.command.parameters

        explicit_target = (
            context.command.arguments[0] if context.command.arguments else None
        )
        if explicit_target and explicit_target.startswith("--"):
            explicit_target = None

        target = explicit_target or params.get("target") or "project"
        build_type = str(params.get("type", "production") or "production").lower()
        optimize = self._flag_present(context.command, "optimize") or self._is_truthy(
            params.get("optimize")
        )
        clean_requested = self._flag_present(
            context.command, "clean"
        ) or self._is_truthy(params.get("clean"))

        operations: List[str] = []
        warnings: List[str] = []
        cleaned = []

        if clean_requested:
            cleaned, clean_errors = self._clean_build_artifacts(repo_root)
            if cleaned:
                operations.extend(f"removed {path}" for path in cleaned)
                cleanup_evidence = context.results.setdefault("applied_changes", [])
                for path in cleaned:
                    entry = f"delete {path}"
                    if entry not in cleanup_evidence:
                        cleanup_evidence.append(entry)
            if clean_errors:
                warnings.extend(clean_errors)

        pipeline = self._plan_build_pipeline(build_type, target, optimize)
        build_logs: List[Dict[str, Any]] = []
        step_errors: List[str] = []

        for step in pipeline:
            result = self._run_command(step["command"], cwd=step.get("cwd"))
            build_logs.append(
                {
                    "description": step["description"],
                    "command": result.get("command"),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "exit_code": result.get("exit_code"),
                    "duration_s": result.get("duration_s"),
                    "error": result.get("error"),
                }
            )
            op_label = f"{step['description']} (exit {result.get('exit_code')})"
            operations.append(op_label)
            if result.get("error"):
                stderr = result.get("stderr") or result.get("error")
                step_errors.append(f"{step['description']}: {stderr}")

        if not pipeline:
            step_errors.append("No build steps available for this project.")

        if step_errors:
            warnings.extend(step_errors)
            context.errors.extend(step_errors)

        operations = self._deduplicate(operations)
        if operations:
            exec_ops = context.results.setdefault("executed_operations", [])
            exec_ops.extend(op for op in operations if op not in exec_ops)

        if operations and not step_errors:
            evidence_log = context.results.setdefault("applied_changes", [])
            for op in operations:
                entry = f"build:{op}"
                if entry not in evidence_log:
                    evidence_log.append(entry)

        summary_lines = [
            f"Build type: {build_type or 'default'}",
            f"Target: {target}",
            f"Optimizations: {'enabled' if optimize else 'disabled'}",
            f"Cleaned: {', '.join(cleaned) if cleaned else 'none'}",
            "",
            "## Steps",
        ]
        if build_logs:
            for idx, entry in enumerate(build_logs, start=1):
                summary_lines.append(
                    f"{idx}. {entry['description']} — exit {entry['exit_code']}"
                )
                if entry.get("stderr"):
                    summary_lines.append(
                        f"   stderr: {self._truncate_output(entry['stderr'])}"
                    )
        else:
            summary_lines.append("No build commands were executed.")

        if warnings:
            summary_lines.append("")
            summary_lines.append("## Warnings")
            summary_lines.extend(f"- {warning}" for warning in warnings)

        artifact = self._record_artifact(
            context,
            "build",
            "\n".join(summary_lines).strip(),
            operations=operations,
            metadata={
                "type": build_type,
                "target": target,
                "optimize": optimize,
                "status": "success" if not step_errors else "failed",
            },
        )

        success = not step_errors
        status = "build_succeeded" if success else "build_failed"

        if warnings:
            warning_list = context.results.setdefault("build_warnings", [])
            warning_list.extend(warnings)
            context.results["build_warnings"] = self._deduplicate(warning_list)

        output: Dict[str, Any] = {
            "status": status,
            "build_type": build_type,
            "target": target,
            "optimize": optimize,
            "steps": build_logs,
            "cleared_artifacts": cleaned,
            "mode": context.behavior_mode,
        }
        if artifact:
            output["artifact"] = artifact
        if warnings:
            output["warnings"] = warnings
        return output

    async def _execute_git(self, context: CommandContext) -> Dict[str, Any]:
        """Execute git command."""
        repo_root = Path(self.repo_root or Path.cwd())
        if not (repo_root / ".git").exists():
            message = "Git repository not found; initialize Git before using /sc:git."
            context.errors.append(message)
            return {
                "status": "git_failed",
                "error": message,
                "mode": context.behavior_mode,
            }

        operation = (
            context.command.arguments[0] if context.command.arguments else "status"
        )
        operation = operation.lower()
        extra_args = context.command.arguments[1:]

        apply_changes = self._flag_present(context.command, "apply") or self._is_truthy(
            context.command.parameters.get("apply")
        )
        smart_commit = (
            self._flag_present(context.command, "smart-commit")
            or self._flag_present(context.command, "smart_commit")
            or self._is_truthy(context.command.parameters.get("smart-commit"))
            or self._is_truthy(context.command.parameters.get("smart_commit"))
        )
        commit_message = context.command.parameters.get(
            "message"
        ) or context.command.parameters.get("msg")

        operations: List[str] = []
        logs: List[Dict[str, Any]] = []
        warnings: List[str] = []

        def _record(result: Dict[str, Any], description: str) -> None:
            logs.append(
                {
                    "description": description,
                    "command": result.get("command"),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "exit_code": result.get("exit_code"),
                    "duration_s": result.get("duration_s"),
                    "error": result.get("error"),
                }
            )
            operations.append(description)
            if result.get("error"):
                stderr = result.get("stderr") or result.get("error")
                warnings.append(f"{description}: {stderr}")

        status_summary: Dict[str, Any] = {}

        if operation == "status":
            status_result = self._run_command(
                ["git", "status", "--short", "--branch"], cwd=repo_root
            )
            _record(status_result, "git status --short --branch")
            stdout = status_result.get("stdout", "")
            lines = [
                line
                for line in stdout.splitlines()
                if line and not line.startswith("##")
            ]
            staged = sum(
                1
                for line in lines
                if line
                and not line.startswith("??")
                and (
                    (line[0] not in {" ", "?"})
                    or (len(line) > 1 and line[1] not in {" ", "?"})
                )
            )
            unstaged = sum(
                1 for line in lines if len(line) > 1 and line[1] not in {" ", "?"}
            )
            untracked = sum(1 for line in lines if line.startswith("??"))
            status_summary = {
                "branch": next(
                    (
                        line[2:].strip()
                        for line in stdout.splitlines()
                        if line.startswith("##")
                    ),
                    "",
                ),
                "staged_changes": staged,
                "unstaged_changes": unstaged,
                "untracked_files": untracked,
            }
        elif operation == "diff":
            diff_result = self._run_command(["git", "diff", "--stat"], cwd=repo_root)
            _record(diff_result, "git diff --stat")
        elif operation == "log":
            log_result = self._run_command(
                ["git", "log", "--oneline", "-5"], cwd=repo_root
            )
            _record(log_result, "git log --oneline -5")
        elif operation == "branch":
            branch_result = self._run_command(
                ["git", "branch", "--show-current"], cwd=repo_root
            )
            _record(branch_result, "git branch --show-current")
            status_summary = {"branch": branch_result.get("stdout", "").strip()}
        elif operation == "add":
            targets = extra_args or ["."]
            add_result = self._run_command(["git", "add", *targets], cwd=repo_root)
            _record(add_result, f"git add {' '.join(targets)}")
        elif operation == "commit":
            if smart_commit or not commit_message:
                commit_message = self._generate_commit_message(repo_root)
            if not commit_message:
                commit_message = "chore: update workspace"
            command_args = ["git", "commit", "-m", commit_message]
            if not apply_changes:
                command_args.insert(2, "--dry-run")
            commit_result = self._run_command(command_args, cwd=repo_root)
            _record(commit_result, " ".join(command_args))
            status_summary["commit_message"] = commit_message
        else:
            generic_cmd = ["git", operation, *extra_args]
            result = self._run_command(generic_cmd, cwd=repo_root)
            _record(result, " ".join(generic_cmd))

        if warnings:
            context.errors.extend(warnings)

        operations = self._deduplicate(operations)
        if operations:
            exec_ops = context.results.setdefault("executed_operations", [])
            exec_ops.extend(op for op in operations if op not in exec_ops)

        summary_lines = [
            f"Operation: {operation}",
            f"Apply changes: {'yes' if apply_changes else 'no'}",
        ]
        if status_summary:
            summary_lines.append("")
            summary_lines.append("## Highlights")
            for key, value in status_summary.items():
                summary_lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        summary_lines.append("")
        summary_lines.append("## Commands")
        for entry in logs:
            summary_lines.append(
                f"- {entry['description']} — exit {entry['exit_code']}"
            )

        if warnings:
            summary_lines.append("")
            summary_lines.append("## Warnings")
            summary_lines.extend(f"- {warning}" for warning in warnings)

        artifact = self._record_artifact(
            context,
            "git",
            "\n".join(summary_lines).strip(),
            operations=operations,
            metadata={
                "operation": operation,
                "apply": apply_changes,
                "smart_commit": smart_commit,
            },
        )

        status = "git_completed" if not warnings else "git_failed"
        output: Dict[str, Any] = {
            "status": status,
            "operation": operation,
            "logs": logs,
            "summary": status_summary,
            "mode": context.behavior_mode,
        }
        if artifact:
            output["artifact"] = artifact
        if warnings:
            output["warnings"] = warnings
        return output

    async def _execute_workflow(self, context: CommandContext) -> Dict[str, Any]:
        """Execute workflow command."""
        repo_root = Path(self.repo_root or Path.cwd())
        raw_argument = " ".join(context.command.arguments).strip()
        params = context.command.parameters

        strategy = str(params.get("strategy", "systematic") or "systematic").lower()
        depth = str(params.get("depth", "normal") or "normal").lower()
        parallel = self._flag_present(context.command, "parallel") or self._is_truthy(
            params.get("parallel")
        )

        source_path: Optional[Path] = None
        source_text = ""
        if raw_argument:
            candidate = (repo_root / raw_argument).resolve()
            try:
                if candidate.exists() and candidate.is_file():
                    source_path = candidate
                    source_text = candidate.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                logger.debug(f"Unable to read workflow source {candidate}: {exc}")

        if not source_text:
            inline_spec = params.get("input") or raw_argument
            if inline_spec:
                source_text = inline_spec

        sections = self._extract_heading_titles(source_text) if source_text else []
        features = self._extract_feature_list(source_text) if source_text else []

        steps = self._generate_workflow_steps(
            context,
            strategy=strategy,
            depth=depth,
            parallel=parallel,
            sections=sections,
            features=features or ([raw_argument] if raw_argument else []),
        )

        if not steps:
            message = "Unable to generate workflow steps from the provided input."
            context.errors.append(message)
            return {
                "status": "workflow_failed",
                "error": message,
                "mode": context.behavior_mode,
            }

        operations = [f"{step['id']}: {step['title']}" for step in steps]
        context.results.setdefault("applied_changes", []).append(
            f"workflow generated for {source_path.name if source_path else (raw_argument or 'adhoc request')}"
        )
        exec_ops = context.results.setdefault("executed_operations", [])
        for op in operations:
            if op not in exec_ops:
                exec_ops.append(op)

        summary_lines = [
            f"Strategy: {strategy}",
            f"Depth: {depth}",
            f"Parallel enabled: {'yes' if parallel else 'no'}",
            f"Source: {str(source_path.relative_to(repo_root)) if source_path else (raw_argument or 'inline request')}",
            "",
            "## Workflow Steps",
        ]
        for step in steps:
            summary_lines.append(
                f"- {step['id']} [{step['phase']}] {step['title']} — owner: {step['owner']}"
            )
            if step.get("dependencies"):
                summary_lines.append(
                    f"  dependencies: {', '.join(step['dependencies'])}"
                )
            if step.get("deliverables"):
                summary_lines.append(
                    f"  deliverables: {', '.join(step['deliverables'])}"
                )

        artifact = self._record_artifact(
            context,
            "workflow",
            "\n".join(summary_lines).strip(),
            operations=operations,
            metadata={
                "strategy": strategy,
                "depth": depth,
                "parallel": parallel,
                "source": str(source_path.relative_to(repo_root))
                if source_path
                else raw_argument or "",
            },
        )

        output: Dict[str, Any] = {
            "status": "workflow_generated",
            "strategy": strategy,
            "depth": depth,
            "parallel": parallel,
            "steps": steps,
            "mode": context.behavior_mode,
            "sections": sections,
            "features": features,
        }
        if artifact:
            output["artifact"] = artifact
        if source_path:
            output["source_path"] = str(source_path.relative_to(repo_root))
        return output

    def _ensure_worktree_manager(self) -> Optional[WorktreeManager]:
        """Ensure a worktree manager instance is available."""
        if getattr(self, "worktree_manager", None) is None:
            try:
                self.worktree_manager = WorktreeManager(
                    str(self.repo_root or Path.cwd())
                )
            except Exception as exc:
                logger.debug(f"Unable to instantiate worktree manager: {exc}")
                self.worktree_manager = None
        return self.worktree_manager

    def _derive_change_plan(
        self,
        context: CommandContext,
        agent_result: Dict[str, Any],
        *,
        label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Build a change plan from agent output or fall back to a default."""
        plan: List[Dict[str, Any]] = []

        for agent_output in context.agent_outputs.values():
            for key in (
                "proposed_changes",
                "generated_files",
                "file_updates",
                "changes",
            ):
                plan.extend(self._extract_agent_change_specs(agent_output.get(key)))

        return plan

    def _extract_agent_change_specs(self, candidate: Any) -> List[Dict[str, Any]]:
        """Normalise agent-proposed change structures into change descriptors."""
        proposals: List[Dict[str, Any]] = []
        if candidate is None:
            return proposals

        if isinstance(candidate, dict):
            if "path" in candidate and "content" in candidate:
                proposals.append(self._normalize_change_descriptor(candidate))
            else:
                for key, value in candidate.items():
                    if isinstance(value, dict) and "content" in value:
                        descriptor = dict(value)
                        descriptor.setdefault("path", key)
                        proposals.append(self._normalize_change_descriptor(descriptor))
                    else:
                        proposals.append(
                            self._normalize_change_descriptor(
                                {
                                    "path": str(key),
                                    "content": value,
                                    "mode": "replace",
                                }
                            )
                        )
        elif isinstance(candidate, (list, tuple, set)):
            for item in candidate:
                proposals.extend(self._extract_agent_change_specs(item))

        return proposals

    def _normalize_change_descriptor(
        self, descriptor: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensure change descriptors retain metadata flags like auto_stub."""
        return {
            "path": str(descriptor.get("path")),
            "content": descriptor.get("content", ""),
            "mode": descriptor.get("mode", "replace"),
        }

    def _assess_stub_requirement(
        self,
        context: CommandContext,
        agent_result: Dict[str, Any],
        *,
        default_reason: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Decide whether to emit an auto-generated stub or queue a follow-up action.

        Returns:
            Tuple of (action, reason) where action is 'stub', 'followup', or 'none'.
        """
        applied_changes = context.results.get("applied_changes") or []
        if applied_changes:
            return "none", None

        status = str(agent_result.get("status") or "").lower()
        if status == "executed":
            return "none", None

        explicit_followup = agent_result.get("requires_followup")
        if isinstance(explicit_followup, str):
            return "followup", explicit_followup
        if explicit_followup:
            return "followup", default_reason or "Agent requested follow-up handling."

        errors = agent_result.get("errors") or []
        if errors:
            return "followup", errors[0]

        if context.metadata.requires_evidence:
            return "stub", default_reason or "Command requires implementation evidence."

        if status == "plan-only":
            return (
                "followup",
                default_reason
                or "Plan-only response provided without concrete changes.",
            )

        return (
            "followup",
            default_reason or "Automation unable to produce concrete changes.",
        )

    def _queue_followup(
        self,
        context: CommandContext,
        reason: str,
        *,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queue a follow-up item for manual resolution."""
        entry = {
            "type": "followup",
            "command": context.command.name,
            "session": context.session_id,
            "reason": reason,
            "source": source,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        followups = context.results.setdefault("requires_followup", [])
        existing = next(
            (
                item
                for item in followups
                if item.get("reason") == reason and item.get("source") == source
            ),
            None,
        )
        if existing:
            return existing

        followups.append(entry)

        if self.monitor:
            tags = {"command": context.command.name, "source": source}
            self.monitor and self.monitor.record_event("commands.followup", entry)
            self.monitor and self.monitor.record_metric(
                "commands.followup.queued", 1, MetricType.COUNTER, tags
            )

        return entry

    def _build_default_change_plan(
        self,
        context: CommandContext,
        agent_result: Dict[str, Any],
        *,
        label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Produce deterministic fallback artifacts when no agent plan exists."""
        slug_source = " ".join(context.command.arguments) or context.command.name
        slug = self._slugify(slug_source)[:48]
        session_fragment = context.session_id.replace("-", "")[:8]
        label_suffix = f"-{self._slugify(label)}" if label else ""

        plan: List[Dict[str, Any]] = []

        action, reason = self._assess_stub_requirement(
            context,
            agent_result,
            default_reason="Agent did not provide concrete changes.",
        )

        if action == "stub":
            stub_entry = self._build_auto_stub_entry(
                context,
                agent_result,
                slug=slug,
                session_fragment=session_fragment,
                label_suffix=label_suffix,
            )
            if stub_entry:
                plan.append(stub_entry)

            evidence_entry = self._build_default_evidence_entry(
                context,
                agent_result,
                slug=slug,
                session_fragment=session_fragment,
                label_suffix=label_suffix,
            )
            if evidence_entry:
                plan.append(evidence_entry)
        elif action == "followup":
            self._queue_followup(
                context,
                reason or "Agent output lacked actionable change plan.",
                source="default-change-plan",
                metadata={"label": label},
            )

        return plan

    def _build_default_evidence_entry(
        self,
        context: CommandContext,
        agent_result: Dict[str, Any],
        *,
        slug: str,
        session_fragment: str,
        label_suffix: str,
    ) -> Dict[str, Any]:
        rel_path = (
            Path("SuperClaude")
            / "Implementation"
            / f"{slug}-{session_fragment}{label_suffix}.md"
        )

        content = self._render_default_evidence_document(context, agent_result)
        return {
            "path": str(rel_path),
            "content": content,
            "mode": "replace",
            "auto_stub": True,
        }

    def _build_generic_stub_change(
        self, context: CommandContext, summary: str
    ) -> Dict[str, Any]:
        """Create a minimal stub change plan so generic commands leave evidence."""
        timestamp = datetime.now().isoformat()
        command_name = context.command.name or "generic"
        slug = self._slugify(command_name)
        session_fragment = (context.session_id or "session")[:8]
        file_name = f"{slug}-{session_fragment}.md"
        rel_path = (
            Path("SuperClaude") / "Implementation" / "Auto" / "generic" / file_name
        )

        lines = [
            f"# Generic Change Plan — /sc:{command_name}",
            "",
            f"- session: {context.session_id}",
            f"- generated: {timestamp}",
            f"- command: /sc:{command_name}",
            "",
            "## Summary",
            summary,
            "",
            "## Next Steps",
            "- Replace this autogenerated stub with concrete implementation details.",
            "- Capture resulting diffs to upgrade this placeholder plan.",
        ]

        return {
            "path": str(rel_path),
            "content": "\n".join(lines).strip() + "\n",
            "mode": "replace",
            "auto_stub": True,
        }

    def _render_default_evidence_document(
        self, context: CommandContext, agent_result: Dict[str, Any]
    ) -> str:
        """Render a fallback implementation evidence markdown document."""
        title = " ".join(context.command.arguments) or context.command.name
        timestamp = datetime.now().isoformat()
        lines: List[str] = [
            f"# Implementation Evidence — {title}",
            "",
            f"- session: {context.session_id}",
            f"- generated: {timestamp}",
            f"- command: /sc:{context.command.name}",
            "",
        ]

        summary = context.results.get("primary_summary")
        if summary:
            lines.extend(["## Summary", summary, ""])

        operations = context.results.get("agent_operations") or []
        if operations:
            lines.append("## Planned Operations")
            lines.extend(f"- {op}" for op in operations)
            lines.append("")

        notes = agent_result.get("notes") or []
        if notes:
            lines.append("## Agent Notes")
            lines.extend(f"- {note}" for note in notes)
            lines.append("")

        warnings = agent_result.get("warnings") or []
        if warnings:
            lines.append("## Agent Warnings")
            lines.extend(f"- {warning}" for warning in warnings)
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _build_auto_stub_entry(
        self,
        context: CommandContext,
        agent_result: Dict[str, Any],
        *,
        slug: str,
        session_fragment: str,
        label_suffix: str,
    ) -> Optional[Dict[str, Any]]:
        extension = self._infer_auto_stub_extension(context, agent_result)
        category = self._infer_auto_stub_category(context)
        if not extension:
            return None

        file_name = f"{slug}-{session_fragment}{label_suffix}.{extension}"
        rel_path = (
            Path("SuperClaude") / "Implementation" / "Auto" / category / file_name
        )

        content = self._render_auto_stub_content(
            context,
            agent_result,
            extension=extension,
            slug=slug,
            session_fragment=session_fragment,
        )

        return {
            "path": str(rel_path),
            "content": content,
            "mode": "replace",
            "auto_stub": True,
        }

    def _infer_auto_stub_extension(
        self, context: CommandContext, agent_result: Dict[str, Any]
    ) -> str:
        parameters = context.command.parameters
        language_hint = str(parameters.get("language") or "").lower()
        framework_hint = str(parameters.get("framework") or "").lower()
        request_blob = " ".join(
            [
                " ".join(context.command.arguments).lower(),
                language_hint,
                framework_hint,
                " ".join(parameters.get("targets", []) or []),
            ]
        )

        def has_any(*needles: str) -> bool:
            return any(needle in request_blob for needle in needles)

        if has_any("readme", "docs", "documentation", "spec", "adr"):
            return "md"
        if has_any("component", "frontend", "ui", "tsx", "react") or framework_hint in {
            "react",
            "next",
            "nextjs",
        }:
            return "tsx"
        if has_any("typescript", "ts", "lambda", "api") or framework_hint in {
            "express",
            "node",
        }:
            return "ts"
        if has_any("javascript", "linkup"):
            return "js"
        if has_any("vue") or framework_hint == "vue":
            return "vue"
        if has_any("svelte") or framework_hint in {"svelte", "solid"}:
            return "svelte"
        if has_any("rust") or framework_hint == "rust":
            return "rs"
        if has_any("golang", " go") or framework_hint in {"go", "golang"}:
            return "go"
        if has_any("java", "spring") or framework_hint == "java":
            return "java"
        if has_any("csharp", "c#", ".net", "dotnet") or framework_hint in {
            "csharp",
            ".net",
            "dotnet",
        }:
            return "cs"
        if has_any("yaml", "config", "manifest"):
            return "yaml"

        default_ext = agent_result.get("default_extension")
        if isinstance(default_ext, str) and default_ext:
            return default_ext

        return "py"

    def _infer_auto_stub_category(self, context: CommandContext) -> str:
        command = context.command.name
        if command in {"test", "improve", "cleanup", "reflect"}:
            return "quality"
        if command in {"build", "workflow", "git"}:
            return "engineering"
        return "engineering" if command == "implement" else "general"

    def _render_auto_stub_content(
        self,
        context: CommandContext,
        agent_result: Dict[str, Any],
        *,
        extension: str,
        slug: str,
        session_fragment: str,
    ) -> str:
        title = " ".join(context.command.arguments) or context.command.name
        timestamp = datetime.now().isoformat()
        operations = (
            agent_result.get("operations")
            or context.results.get("agent_operations")
            or []
        )
        notes = agent_result.get("notes") or context.results.get("agent_notes") or []

        if not operations:
            operations = [
                "Review requirements and confirm scope with stakeholders",
                "Implement the planned changes in code",
                "Add or update tests to cover the new behavior",
            ]

        deduped_operations = self._deduplicate(operations)
        deduped_notes = self._deduplicate(notes)

        def format_ops(prefix: str = "#") -> str:
            return "\n".join(f"{prefix}  - {op}" for op in deduped_operations)

        def format_notes(prefix: str = "#") -> str:
            if not notes:
                return ""
            return "\n".join(f"{prefix}  - {note}" for note in deduped_notes)

        function_name = slug.replace("-", "_") or f"auto_task_{session_fragment}"
        if not function_name[0].isalpha():
            function_name = f"auto_task_{session_fragment}"

        if extension == "py":
            ops_literal = repr(deduped_operations)
            notes_literal = repr(deduped_notes)
            body = textwrap.dedent(
                f'''
                """Auto-generated implementation plan for {title}.

                Generated by the SuperClaude auto-implementation pipeline on {timestamp}.
                The function records the captured plan so it can be actioned later.
                """

                from __future__ import annotations

                import json
                import os
                from datetime import datetime
                from pathlib import Path
                from typing import Any, Dict


                def {function_name}() -> Dict[str, Any]:
                    """Record and return the auto-generated implementation plan."""
                    plan: Dict[str, Any] = {{
                        "title": {json.dumps(title)},
                        "session": {json.dumps(context.session_id or "")},
                        "generated_at": {json.dumps(timestamp)},
                        "operations": {ops_literal},
                        "notes": {notes_literal},
                    }}

                    metrics_root = Path(os.getenv("SUPERCLAUDE_METRICS_DIR", ".superclaude_metrics"))
                    metrics_root.mkdir(parents=True, exist_ok=True)
                    log_path = metrics_root / "auto_implementation_plans.jsonl"
                    with log_path.open("a", encoding="utf-8") as handle:
                        entry = {{
                            **plan,
                            "recorded_at": datetime.utcnow().isoformat() + "Z",
                        }}
                        handle.write(json.dumps(entry) + "\n")

                    return plan


                # Planned operations
                {format_ops()}

                # Additional context
                {format_notes() or "#  - No additional agent notes recorded"}
                '''
            ).strip()
            return body + "\n"

        if extension in {"ts", "tsx", "js"}:
            plan_literal = json.dumps(deduped_operations, indent=2)
            notes_literal_ts = json.dumps(deduped_notes, indent=2)
            import_block = (
                """import fs from 'node:fs';\nimport path from 'node:path';"""
            )
            if extension == "js":
                export_signature = (
                    f"export async function {function_name}()"  # JS without types
                )
            else:
                export_signature = f"export async function {function_name}(): Promise<Record<string, unknown>>"

            body = textwrap.dedent(
                f"""
                {import_block}

                {export_signature} {{
                  const plan = {{
                    title: {json.dumps(title)},
                    session: {json.dumps(context.session_id or "")},
                    generatedAt: {json.dumps(timestamp)},
                    operations: {plan_literal},
                    notes: {notes_literal_ts},
                  }};

                  const metricsDir = process.env.SUPERCLAUDE_METRICS_DIR ?? '.superclaude_metrics';
                  await fs.promises.mkdir(metricsDir, {{ recursive: true }});
                  const logPath = path.join(metricsDir, 'auto_implementation_plans.jsonl');
                  const entry = {{ ...plan, recordedAt: new Date().toISOString() }};
                  await fs.promises.appendFile(logPath, JSON.stringify(entry) + '\n', {{ encoding: 'utf8' }});

                  return plan;
                }}

                // Planned operations
                {format_ops("//")}

                {format_notes("//") or "//  - No additional agent notes recorded"}
                """
            ).strip()
            return body + "\n"

        if extension == "md":
            lines = [
                f"# Auto-generated Implementation Stub — {title}",
                "",
                f"- session: {context.session_id}",
                f"- generated: {timestamp}",
                f"- command: /sc:{context.command.name}",
                "",
                "## Planned Operations",
            ]
            lines.extend(f"- {op}" for op in self._deduplicate(operations))
            if notes:
                lines.append("")
                lines.append("## Agent Notes")
                lines.extend(f"- {note}" for note in self._deduplicate(notes))
            return "\n".join(lines).strip() + "\n"

        comment_prefix = (
            "//" if extension in {"java", "cs", "rs", "go", "vue", "svelte"} else "#"
        )

        body = textwrap.dedent(
            f"""
            {comment_prefix} Auto-generated implementation stub for {title}.
            {comment_prefix} Generated on {timestamp}. Replace with real implementation after completing the plan.

            {comment_prefix} Planned operations
            {format_ops(comment_prefix)}

            {format_notes(comment_prefix) or f"{comment_prefix}  - No additional agent notes recorded"}
            """
        ).strip()
        return body + "\n"

    def _apply_change_plan(
        self, context: CommandContext, change_plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply the change plan using the worktree manager or a fallback writer."""
        if not change_plan:
            return {
                "applied": [],
                "warnings": ["No change entries provided to apply."],
                "base_path": str(self.repo_root or Path.cwd()),
                "session": "empty",
            }

        safe_apply_requested = self._safe_apply_requested(context)
        if safe_apply_requested:
            snapshot = self._write_safe_apply_snapshot(context, change_plan)
            warning = "Safe-apply requested; changes saved to scratch directory without modifying the repository."
            result: Dict[str, Any] = {
                "applied": [],
                "warnings": [warning],
                "base_path": str(self.repo_root or Path.cwd()),
                "session": "safe-apply",
            }
            if snapshot:
                result["safe_apply_directory"] = snapshot["directory"]
                result["safe_apply_files"] = snapshot.get("files", [])
            return result

        try:
            manager = self._ensure_worktree_manager()
            if manager:
                result = manager.apply_changes(change_plan)
            else:
                result = self._apply_changes_fallback(change_plan)
        except Exception as exc:
            logger.error(f"Failed to apply change plan: {exc}")
            context.errors.append(f"Failed to apply change plan: {exc}")
            return {
                "applied": [],
                "warnings": [str(exc)],
                "base_path": str(self.repo_root or Path.cwd()),
                "session": "error",
            }

        result.setdefault("warnings", [])
        result.setdefault("applied", [])
        if "base_path" not in result:
            result["base_path"] = str(self.repo_root or Path.cwd())
        return result

    def _apply_changes_fallback(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply changes directly to the repository when the manager is unavailable."""
        base_path = Path(self.repo_root or Path.cwd())
        applied: List[str] = []
        warnings: List[str] = []

        for change in changes:
            rel_path = change.get("path")
            if not rel_path:
                warnings.append("Change missing path")
                continue

            rel_path = Path(rel_path)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                warnings.append(f"Invalid path outside repository: {rel_path}")
                continue

            target_path = (base_path / rel_path).resolve()
            try:
                target_path.relative_to(base_path)
            except ValueError:
                warnings.append(f"Path escapes repository: {rel_path}")
                continue

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                mode = change.get("mode", "replace")
                content = change.get("content", "")
                if mode == "append" and target_path.exists():
                    with target_path.open("a", encoding="utf-8") as handle:
                        handle.write(str(content))
                else:
                    target_path.write_text(str(content), encoding="utf-8")
            except Exception as exc:
                warnings.append(f"Failed writing {rel_path}: {exc}")
                continue

            applied.append(str(target_path.relative_to(base_path)))

        return {
            "applied": applied,
            "warnings": warnings,
            "base_path": str(base_path),
            "session": "direct",
        }

    def _slugify(self, value: str) -> str:
        """Create a filesystem-safe slug from arbitrary text."""
        sanitized = "".join(
            ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.lower()
        )
        sanitized = "-".join(part for part in sanitized.split("-") if part)
        return sanitized or "implementation"

    def _quality_loop_improver(
        self, context: CommandContext, current_output: Any, loop_context: Dict[str, Any]
    ) -> Any:
        """Remediation improver used by the quality loop."""
        iteration_index = int(loop_context.get("iteration", 0))

        try:
            return self._run_quality_remediation_iteration(
                context, current_output, loop_context, iteration_index
            )
        except Exception as exc:
            logger.warning(f"Quality remediation iteration failed: {exc}")
            loop_context.setdefault("errors", []).append(str(exc))
            context.results.setdefault("quality_loop_warnings", []).append(str(exc))
            return current_output

    def _run_quality_remediation_iteration(
        self,
        context: CommandContext,
        current_output: Any,
        loop_context: Dict[str, Any],
        iteration_index: int,
    ) -> Any:
        """Perform a single remediation iteration for the quality loop."""
        improvements = list(loop_context.get("improvements_needed") or [])
        loop_context.setdefault("notes", []).append(
            f"Remediation iteration {iteration_index + 1} focusing on: {', '.join(improvements) or 'general improvements'}"
        )

        self._prepare_remediation_agents(
            context, ["quality-engineer", "refactoring-expert", "general-purpose"]
        )

        previous_hint = context.command.parameters.get("quality_improvements")
        context.command.parameters["quality_improvements"] = improvements

        try:
            agent_result = self._run_agent_pipeline(context)
        finally:
            if previous_hint is None:
                context.command.parameters.pop("quality_improvements", None)
            else:
                context.command.parameters["quality_improvements"] = previous_hint

        change_plan = self._derive_change_plan(
            context, agent_result, label=f"iteration-{iteration_index + 1}"
        )

        apply_result = self._apply_change_plan(context, change_plan)
        applied_files = apply_result.get("applied", []) or []
        warnings = apply_result.get("warnings", []) or []

        if not applied_files:
            message = "Quality remediation produced no repository changes."
            loop_context.setdefault("errors", []).append(message)
            warnings.append(message)

        if warnings:
            quality_warnings = context.results.setdefault("quality_loop_warnings", [])
            for warning in warnings:
                if warning not in quality_warnings:
                    quality_warnings.append(warning)

        if applied_files:
            applied_list = context.results.setdefault("applied_changes", [])
            for path in applied_files:
                entry = f"loop iteration {iteration_index + 1}: apply {path}"
                if entry not in applied_list:
                    applied_list.append(entry)
            self._record_loop_review_target(context, applied_files, iteration_index)

        tests = self._run_requested_tests(context.command)
        tests_summary = self._summarize_test_results(tests)

        operations = context.results.setdefault("executed_operations", [])
        operations.append(f"quality loop iteration {iteration_index + 1}")
        operations.append(tests_summary)
        context.results["executed_operations"] = self._deduplicate(operations)

        quality_tests = context.results.setdefault("quality_loop_tests", [])
        quality_tests.append(tests)

        iteration_record = {
            "iteration": iteration_index,
            "improvements_requested": improvements,
            "agents_invoked": sorted(set(context.agents)),
            "change_plan": change_plan,
            "applied_files": applied_files,
            "warnings": warnings,
            "tests": {
                "passed": tests.get("passed"),
                "command": tests.get("command"),
                "coverage": tests.get("coverage"),
                "summary": tests.get("summary"),
                "exit_code": tests.get("exit_code"),
            },
        }

        if not applied_files and not tests.get("passed"):
            iteration_record["status"] = "no-changes-tests-failed"
        elif not applied_files:
            iteration_record["status"] = "no-changes"
        elif not tests.get("passed"):
            iteration_record["status"] = "tests-failed"
            loop_context.setdefault("errors", []).append(
                "Tests failed during remediation iteration."
            )
        else:
            iteration_record["status"] = "improved"

        quality_iterations = context.results.setdefault("quality_loop_iterations", [])
        quality_iterations.append(iteration_record)

        improved_output = (
            copy.deepcopy(current_output)
            if isinstance(current_output, dict)
            else current_output
        )
        if isinstance(improved_output, dict):
            loop_payload = {
                "iteration": iteration_index,
                "improvements": improvements,
                "applied_files": applied_files,
                "test_results": tests,
                "warnings": warnings,
                "status": iteration_record["status"],
            }
            improved_output.setdefault("quality_loop", []).append(loop_payload)
        return improved_output

    def _record_loop_review_target(
        self, context: CommandContext, applied_files: List[str], iteration_index: int
    ) -> None:
        """Capture diffs for later Zen reviews when loop iterations make changes."""
        if not context.zen_review_enabled or not applied_files:
            return

        diff_blob = self._collect_file_diffs(applied_files)
        if not diff_blob:
            return

        targets = context.results.setdefault("zen_review_targets", [])
        targets.append(
            {
                "iteration": iteration_index + 1,
                "files": sorted(set(applied_files)),
                "diff": diff_blob,
                "captured_at": datetime.now().isoformat(),
            }
        )

    def _collect_file_diffs(self, applied_files: Sequence[str]) -> str:
        """Generate unified diffs for the provided repository-relative paths."""
        repo_root = Path(self.repo_root or Path.cwd())
        seen: Set[str] = set()
        diff_chunks: List[str] = []

        for rel_path in applied_files:
            if not rel_path:
                continue
            normalized = str(rel_path).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)

            file_path = (repo_root / normalized).resolve()
            try:
                file_path.relative_to(repo_root)
            except ValueError:
                continue
            if not file_path.exists():
                continue

            if self._is_tracked_file(normalized):
                command = ["git", "diff", "--no-color", "--unified=3", "--", normalized]
            else:
                command = [
                    "git",
                    "diff",
                    "--no-color",
                    "--unified=3",
                    "--no-index",
                    "/dev/null",
                    str(file_path),
                ]

            result = self._run_command(command, cwd=repo_root)
            diff_text = (result.get("stdout") or "").strip()
            if diff_text:
                diff_chunks.append(f"### {normalized}\n{diff_text}")

        return "\n\n".join(diff_chunks)

    def _is_tracked_file(self, rel_path: str) -> bool:
        """Return True if the given path is tracked by git."""
        repo_root = Path(self.repo_root or Path.cwd())
        result = self._run_command(
            ["git", "ls-files", "--error-unmatch", rel_path], cwd=repo_root
        )
        return result.get("exit_code") == 0

    def _enable_primary_zen_quality(
        self, context: CommandContext
    ) -> Optional[Callable[[], None]]:
        """Promote GPT-backed evaluation to the primary quality scorer path."""
        zen_instance = self._get_active_mcp_instance("zen")
        if not zen_instance:
            return None

        def _primary_evaluator(
            _: Any, eval_context: Dict[str, Any], iteration: int
        ) -> Optional[Dict[str, Any]]:
            diff_blob = self._collect_full_repo_diff()
            if not diff_blob.strip():
                return None

            files = eval_context.get("changed_files") or self._list_changed_files()
            metadata = {
                "reason": "quality-loop-primary",
                "loop_requested": context.results.get("loop_requested", False),
                "iteration": iteration,
                "think_level": context.think_level,
            }

            try:
                review_payload = self._invoke_zen_review_sync(
                    zen_instance,
                    diff_blob,
                    files=files,
                    metadata=metadata,
                    model=context.zen_review_model or "gpt-5",
                )
            except Exception as exc:
                context.results.setdefault("zen_review_errors", []).append(str(exc))
                return None

            metrics = self._convert_zen_payload_to_metrics(review_payload)
            if not metrics:
                return None

            improvements = (
                review_payload.get("improvements")
                or review_payload.get("recommendations")
                or []
            )
            meta = {"zen_review": review_payload}
            return {
                "metrics": metrics,
                "improvements": improvements,
                "metadata": meta,
            }

        self.quality_scorer.set_primary_evaluator(_primary_evaluator)

        def _cleanup():
            if self.quality_scorer.primary_evaluator is _primary_evaluator:
                self.quality_scorer.clear_primary_evaluator()

        return _cleanup

    def _collect_full_repo_diff(self) -> str:
        repo_root = Path(self.repo_root or Path.cwd())
        result = self._run_command(["git", "diff", "--no-color"], cwd=repo_root)
        return (result.get("stdout") or "").strip()

    def _list_changed_files(self) -> List[str]:
        repo_root = Path(self.repo_root or Path.cwd())
        result = self._run_command(["git", "status", "--short"], cwd=repo_root)
        files: List[str] = []
        stdout = result.get("stdout") or ""
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1].strip())
        return files

    def _convert_zen_payload_to_metrics(
        self, payload: Dict[str, Any]
    ) -> List[QualityMetric]:
        metrics: List[QualityMetric] = []
        dimensions = payload.get("dimensions") or {}
        summary = payload.get("summary") or "Zen review summary unavailable."
        overall_score = float(payload.get("score", 0.0))

        if isinstance(dimensions, dict) and dimensions:
            for name, data in dimensions.items():
                try:
                    dimension = QualityDimension(name)
                except ValueError:
                    continue
                if not isinstance(data, dict):
                    continue
                score = float(data.get("score", overall_score))
                issues = data.get("issues") or payload.get("issues") or []
                suggestions = (
                    data.get("suggestions") or payload.get("recommendations") or []
                )
                weight = self.quality_scorer.default_weights.get(dimension, 0.1)
                metrics.append(
                    QualityMetric(
                        dimension=dimension,
                        score=max(0.0, min(100.0, score)),
                        weight=weight,
                        details=summary,
                        issues=issues[:6] if isinstance(issues, list) else [],
                        suggestions=suggestions[:6]
                        if isinstance(suggestions, list)
                        else [],
                    )
                )

        if not metrics:
            issues = []
            for issue in payload.get("issues") or []:
                if isinstance(issue, dict):
                    issues.append(issue.get("title") or issue.get("details") or "")
                else:
                    issues.append(str(issue))
            suggestions = payload.get("recommendations") or []
            weight = self.quality_scorer.default_weights.get(
                QualityDimension.ZEN_REVIEW, 0.1
            )
            metrics.append(
                QualityMetric(
                    dimension=QualityDimension.ZEN_REVIEW,
                    score=max(0.0, min(100.0, overall_score)),
                    weight=weight,
                    details=summary,
                    issues=[text for text in issues if text][:6],
                    suggestions=suggestions[:6]
                    if isinstance(suggestions, list)
                    else [],
                )
            )

        return metrics

    def _invoke_zen_review_sync(
        self,
        zen_instance: Any,
        diff_blob: str,
        *,
        files: Sequence[str],
        metadata: Dict[str, Any],
        model: str,
    ) -> Dict[str, Any]:
        async def _call_review():
            return await zen_instance.review_code(
                diff_blob, files=list(files), metadata=metadata, model=model
            )

        return self._run_async_function(_call_review)

    def _run_async_function(self, async_callable: Callable[[], Any]) -> Any:
        """Execute an async callable from synchronous code using a dedicated event loop."""
        result: Dict[str, Any] = {}
        error: Dict[str, Exception] = {}

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result["value"] = loop.run_until_complete(async_callable())
            except Exception as exc:
                error["exc"] = exc
            finally:
                loop.close()

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()

        if error:
            raise error["exc"]
        return result.get("value", {})

    def _prepare_remediation_agents(
        self, context: CommandContext, agents: Iterable[str]
    ) -> None:
        """Ensure remediation-focused agents are available for the quality loop."""
        loader = self.agent_loader or AgentLoader()
        for agent_name in agents:
            if agent_name in context.agent_instances:
                continue
            try:
                agent_instance = loader.load_agent(agent_name)
            except Exception as exc:
                warning = f"Failed to load remediation agent {agent_name}: {exc}"
                logger.debug(warning)
                context.results.setdefault("quality_loop_warnings", []).append(warning)
                continue
            if agent_instance:
                context.agent_instances[agent_name] = agent_instance
                if agent_name not in context.agents:
                    context.agents.append(agent_name)

    async def _execute_generic(self, context: CommandContext) -> Dict[str, Any]:
        """Execute fallback logic for commands without bespoke handlers."""
        command = context.command
        argument_text = " ".join(command.arguments) if command.arguments else "none"
        flags_text = ", ".join(sorted(command.flags.keys())) or "none"
        summary_lines = [
            f"Command: /sc:{command.name}",
            f"Mode: {context.behavior_mode}",
            f"Arguments: {argument_text}",
            f"Flags: {flags_text}",
        ]
        if command.parameters:
            summary_lines.append("Parameters:")
            for key, value in sorted(command.parameters.items()):
                summary_lines.append(f"- {key}: {value}")

        summary = "\n".join(summary_lines).strip()

        operations = [
            f"fallback-handler executed for /sc:{command.name}",
        ]

        artifact = self._record_artifact(
            context,
            command.name,
            summary,
            operations=operations,
            metadata={
                "mode": context.behavior_mode,
                "fallback": True,
            },
        )

        fallback_reason = f"Generic fallback handler invoked for /sc:{command.name}"
        decision, decision_reason = self._assess_stub_requirement(
            context,
            {
                "status": "plan-only",
                "requires_followup": False,
                "errors": [],
            },
            default_reason=fallback_reason,
        )

        change_plan_entries: List[Dict[str, Any]] = []
        applied_files: List[str] = []
        change_warnings: List[str] = []
        followup_record: Optional[Dict[str, Any]] = None

        if decision == "stub":
            change_entry = self._build_generic_stub_change(context, summary)
            change_plan_entries.append(change_entry)

            apply_result = self._apply_change_plan(context, change_plan_entries)
            applied_files = apply_result.get("applied", [])
            change_warnings = apply_result.get("warnings", []) or []
            if change_warnings:
                context.errors.extend(change_warnings)

            if applied_files:
                applied_log = context.results.setdefault("applied_changes", [])
                for path in applied_files:
                    applied_log.append(f"apply {path}")
                context.results["applied_changes"] = self._deduplicate(applied_log)

            plan_entries = context.results.setdefault("change_plan", [])
            if not any(
                isinstance(existing, dict)
                and existing.get("path") == change_entry.get("path")
                for existing in plan_entries
            ):
                plan_entries.append(change_entry)
        else:
            followup_record = self._queue_followup(
                context,
                decision_reason or fallback_reason,
                source="generic-fallback",
                metadata={
                    "arguments": command.arguments,
                    "flags": list(command.flags.keys()),
                },
            )
            if followup_record:
                change_warnings.append(followup_record["reason"])

        context.results.setdefault("executed_operations", [])
        context.results["executed_operations"].extend(operations)
        context.results["executed_operations"] = self._deduplicate(
            context.results["executed_operations"]
        )

        status = "executed" if applied_files else "plan-only"

        output: Dict[str, Any] = {
            "status": status,
            "command": command.name,
            "parameters": command.parameters,
            "arguments": command.arguments,
            "mode": context.behavior_mode,
            "summary": summary,
            "change_plan": change_plan_entries,
            "applied_files": applied_files,
        }
        if artifact:
            output["artifact"] = artifact
        if change_warnings:
            output["warnings"] = change_warnings
        if followup_record:
            output["followup"] = followup_record
        return output

    def _generate_workflow_steps(
        self,
        context: CommandContext,
        *,
        strategy: str,
        depth: str,
        parallel: bool,
        sections: Sequence[str],
        features: Sequence[str],
    ) -> List[Dict[str, Any]]:
        """Generate structured workflow steps."""
        steps: List[Dict[str, Any]] = []
        step_counter = 0

        def add_step(
            phase: str,
            title: str,
            owner: str,
            *,
            dependencies: Optional[Sequence[str]] = None,
            deliverables: Optional[Sequence[str]] = None,
            notes: Optional[str] = None,
            parallelizable: bool = False,
        ) -> str:
            nonlocal step_counter
            step_counter += 1
            step_id = f"S{step_counter:02d}"
            steps.append(
                {
                    "id": step_id,
                    "phase": phase,
                    "title": title,
                    "owner": owner,
                    "dependencies": list(dependencies or []),
                    "deliverables": list(deliverables or []),
                    "notes": notes or "",
                    "parallel": bool(parallelizable and parallel),
                }
            )
            return step_id

        analysis_owner = "requirements-analyst"
        architecture_owner = "system-architect"
        quality_owner = "quality-engineer"
        release_owner = "devops-architect"

        analysis_id = add_step(
            "Analysis",
            "Clarify scope, stakeholders, and success criteria",
            analysis_owner,
            deliverables=["Requirements brief", "Success metrics checklist"],
            notes="Synthesize PRD sections and confirm acceptance criteria.",
        )

        design_id = add_step(
            "Architecture",
            "Establish architecture and integration boundaries",
            architecture_owner,
            dependencies=[analysis_id],
            deliverables=["Architecture baseline", "Interface contracts"],
            notes="Align with existing decisions and stack documented in product roadmap.",
        )

        planning_owner = "project-manager"
        planning_notes = "Define execution cadence and align with delivery strategy."
        if strategy in {"agile", "scrum"}:
            planning_title = "Plan sprint backlog and iteration cadence"
        elif strategy in {"enterprise"}:
            planning_title = "Align governance checkpoints and stakeholder approvals"
        else:
            planning_title = "Sequence implementation milestones and owners"

        planning_id = add_step(
            "Planning",
            planning_title,
            planning_owner,
            dependencies=[analysis_id, design_id],
            deliverables=["Execution plan", "Owner assignments"],
            notes=planning_notes,
            parallelizable=True,
        )

        implementation_dependencies = [design_id, planning_id]
        feature_steps: List[str] = []

        feature_items = features or ["Core feature implementation"]
        for item in feature_items:
            owner = self._select_feature_owner(item)
            feature_steps.append(
                add_step(
                    "Implementation",
                    f"Deliver feature: {item}",
                    owner,
                    dependencies=implementation_dependencies,
                    deliverables=[
                        f"{item} implementation",
                        "Linked documentation updates",
                    ],
                    notes="Coordinate with delegated agents when specialization is required.",
                    parallelizable=True,
                )
            )

        if depth in {"deep", "enterprise"}:
            security_step = add_step(
                "Quality",
                "Run security and compliance review",
                "security-engineer",
                dependencies=feature_steps or implementation_dependencies,
                deliverables=["Security checklist", "Risk register updates"],
                notes="Ensure authentication, authorization, and data handling meet standards.",
                parallelizable=parallel,
            )
            performance_step = add_step(
                "Quality",
                "Validate performance and scalability benchmarks",
                "performance-engineer",
                dependencies=feature_steps or [security_step],
                deliverables=["Performance test results", "Optimization backlog"],
                notes="Stress critical paths; capture regression budgets.",
                parallelizable=parallel,
            )
            qa_dependencies = feature_steps + [security_step, performance_step]
        else:
            qa_dependencies = feature_steps

        qa_step = add_step(
            "Quality",
            "Execute automated tests and acceptance validation",
            quality_owner,
            dependencies=qa_dependencies or implementation_dependencies,
            deliverables=[
                "Test evidence",
                "Coverage summary",
                "Go/No-go recommendation",
            ],
            notes="Include regression, integration, and smoke suites.",
            parallelizable=False,
        )

        release_dependencies = [qa_step]
        release_notes = (
            "Package artifacts, update changelog, and prepare rollout checklist."
        )
        release_step = add_step(
            "Release",
            "Prepare deployment and rollout communications",
            release_owner,
            dependencies=release_dependencies,
            deliverables=["Deployment plan", "Rollback steps", "Release notes draft"],
            notes=release_notes,
            parallelizable=False,
        )

        if strategy in {"enterprise", "systematic"}:
            add_step(
                "Governance",
                "Capture learnings and update long-term roadmap",
                "requirements-analyst",
                dependencies=[release_step],
                deliverables=["Retrospective summary", "Roadmap adjustments"],
                notes="Feed outcomes into product artifacts for cross-team awareness.",
                parallelizable=False,
            )

        return steps

    def _normalize_repo_root(self, repo_root: Optional[Path]) -> Optional[Path]:
        """Normalize desired repo root, falling back to detected git root."""
        env_root = os.environ.get("SUPERCLAUDE_REPO_ROOT")
        if repo_root is None and env_root:
            repo_root = Path(env_root).expanduser()

        if repo_root is not None:
            try:
                return Path(repo_root).resolve()
            except Exception:
                return Path(repo_root)

        return self._detect_repo_root()

    def _detect_repo_root(self) -> Optional[Path]:
        """Locate the git repository root, if available."""
        try:
            current = Path.cwd().resolve()
        except Exception:
            return None

        for candidate in [current, *current.parents]:
            if (candidate / ".git").exists():
                return candidate
        return None

    def _snapshot_repo_changes(self) -> Set[str]:
        """Capture current git worktree changes for comparison."""
        if not self.repo_root or not (self.repo_root / ".git").exists():
            return set()

        snapshot: Set[str] = set()
        commands = [
            ["git", "diff", "--name-status"],
            ["git", "diff", "--name-status", "--cached"],
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd, cwd=self.repo_root, capture_output=True, text=True, check=False
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
                check=False,
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

    def _partition_change_entries(
        self, entries: Iterable[str]
    ) -> Tuple[List[str], List[str]]:
        """Separate artifact-only changes from potential evidence."""
        artifact_entries: List[str] = []
        evidence_entries: List[str] = []

        for entry in entries:
            if self._is_artifact_change(entry):
                artifact_entries.append(entry)
            else:
                evidence_entries.append(entry)

        return artifact_entries, evidence_entries

    def _is_artifact_change(self, entry: str) -> bool:
        """Heuristically detect whether a change originates from command artifacts."""
        parts = entry.split("\t")
        if len(parts) < 2:
            return False

        # git name-status formats place the path in the last column
        candidate = parts[-1].strip()
        return candidate.startswith("SuperClaude/Generated/") or candidate.startswith(
            ".worktrees/"
        )

    def _format_change_entry(self, entry: str) -> str:
        """Convert a git name-status entry into a human readable description."""
        parts = entry.split("\t")
        if not parts:
            return entry

        code = parts[0]
        code_letter = code[0] if code else "?"

        if code.startswith("??") and len(parts) >= 2:
            return f"add {parts[1]}"

        if code_letter == "M" and len(parts) >= 2:
            return f"modify {parts[1]}"

        if code_letter == "A" and len(parts) >= 2:
            return f"add {parts[1]}"

        if code_letter == "D" and len(parts) >= 2:
            return f"delete {parts[1]}"

        if code_letter == "R" and len(parts) >= 3:
            return f"rename {parts[1]} -> {parts[2]}"

        if code_letter == "C" and len(parts) >= 3:
            return f"copy {parts[1]} -> {parts[2]}"

        if len(parts) >= 2:
            return f"{code_letter.lower()} {parts[1]}"

        return entry

    def _run_command(
        self,
        command: Sequence[str],
        *,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a system command and capture its output.

        Returns:
            Dictionary containing command metadata, stdout, stderr, exit code, duration,
            and an optional error indicator.
        """
        args = [str(part) for part in command]
        working_dir = Path(cwd or self.repo_root or Path.cwd())
        runtime_env = os.environ.copy()
        runtime_env.setdefault("PYENV_DISABLE_REHASH", "1")
        if env:
            runtime_env.update({str(key): str(value) for key, value in env.items()})

        start = datetime.now()
        try:
            result = subprocess.run(
                args,
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                env=runtime_env,
                timeout=timeout,
                check=False,
            )
            duration = (datetime.now() - start).total_seconds()
            stdout_text = (result.stdout or "").strip()
            stderr_text = (result.stderr or "").strip()
            output = {
                "command": " ".join(args),
                "args": args,
                "cwd": str(working_dir),
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": result.returncode,
                "duration_s": duration,
            }
            if result.returncode != 0:
                output["error"] = f"exit code {result.returncode}"
            return output
        except subprocess.TimeoutExpired as exc:
            duration = (datetime.now() - start).total_seconds()
            stdout_text = getattr(exc, "stdout", "") or ""
            stderr_text = getattr(exc, "stderr", "") or ""
            return {
                "command": " ".join(args),
                "args": args,
                "cwd": str(working_dir),
                "stdout": stdout_text.strip(),
                "stderr": (stderr_text or "Command timed out").strip(),
                "exit_code": None,
                "duration_s": duration,
                "error": "timeout",
            }
        except Exception as exc:
            duration = (datetime.now() - start).total_seconds()
            return {
                "command": " ".join(args),
                "args": args,
                "cwd": str(working_dir),
                "stdout": "",
                "stderr": str(exc),
                "exit_code": None,
                "duration_s": duration,
                "error": str(exc),
            }

    def _collect_diff_stats(self) -> List[str]:
        """Collect diff statistics for working and staged changes."""
        if not self.repo_root or not (self.repo_root / ".git").exists():
            return []

        stats: List[str] = []
        commands = [
            ("working", ["git", "diff", "--stat"]),
            ("staged", ["git", "diff", "--stat", "--cached"]),
        ]

        for label, cmd in commands:
            try:
                result = subprocess.run(
                    cmd, cwd=self.repo_root, capture_output=True, text=True, check=False
                )
            except Exception as exc:
                logger.debug(f"Failed to gather diff stats ({label}): {exc}")
                continue

            output = result.stdout.strip()
            if output:
                stats.append(f"diff --stat ({label}): {self._truncate_output(output)}")

        return stats

    def _clean_build_artifacts(self, repo_root: Path) -> Tuple[List[str], List[str]]:
        """Remove common build artifacts when a clean build is requested."""
        removed: List[str] = []
        errors: List[str] = []
        targets = [
            "build",
            "dist",
            "htmlcov",
            ".pytest_cache",
            "SuperClaude.egg-info",
        ]

        for target in targets:
            path = repo_root / target
            if not path.exists():
                continue
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed.append(str(path.relative_to(repo_root)))
            except Exception as exc:
                errors.append(f"{target}: {exc}")

        return removed, errors

    def _git_has_modifications(self, file_path: Path) -> bool:
        """Check whether git reports pending changes for the path (excluding untracked files)."""
        if not self.repo_root or not (self.repo_root / ".git").exists():
            return False

        try:
            rel_path = file_path.relative_to(self.repo_root)
        except ValueError:
            # File sits outside repo root; treat as unmanaged.
            return False

        try:
            result = subprocess.run(
                ["git", "status", "--short", "--", str(rel_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return False

        if result.returncode != 0:
            return False

        output = result.stdout.strip()
        if not output:
            return False

        status = output.splitlines()[0][:2]
        if status == "??":
            return False
        return True

    def _plan_build_pipeline(
        self, build_type: str, target: Optional[str], optimize: bool
    ) -> List[Dict[str, Any]]:
        """Determine the build steps required for the current repository."""
        repo_root = Path(self.repo_root or Path.cwd())
        pipeline: List[Dict[str, Any]] = []

        has_pyproject = (repo_root / "pyproject.toml").exists()
        has_setup = (repo_root / "setup.py").exists()
        has_package_json = (repo_root / "package.json").exists()

        if has_package_json and shutil.which("npm"):
            pipeline.append(
                {
                    "description": "Install npm dependencies",
                    "command": ["npm", "install"],
                    "cwd": repo_root,
                }
            )
            build_cmd: List[str] = ["npm", "run", "build"]
            if build_type and build_type not in {"production", "prod"}:
                build_cmd.extend(["--", f"--mode={build_type}"])
            elif optimize:
                build_cmd.extend(["--", "--mode=production"])
            pipeline.append(
                {
                    "description": f"Run npm build ({build_type or 'default'})",
                    "command": build_cmd,
                    "cwd": repo_root,
                }
            )

        if has_pyproject or has_setup:
            if importlib.util.find_spec("build"):
                build_args = ["python", "-m", "build"]
                if optimize:
                    build_args.append("--wheel")
                    build_args.append("--sdist")
                pipeline.append(
                    {
                        "description": "Build Python distributions",
                        "command": build_args,
                        "cwd": repo_root,
                    }
                )
            elif has_setup:
                pipeline.append(
                    {
                        "description": "Build Python source distribution",
                        "command": ["python", "setup.py", "sdist"],
                        "cwd": repo_root,
                    }
                )

        superclaude_path = repo_root / "SuperClaude"
        if superclaude_path.exists():
            pipeline.append(
                {
                    "description": "Compile Python sources",
                    "command": ["python", "-m", "compileall", str(superclaude_path)],
                    "cwd": repo_root,
                }
            )

        return pipeline

    def _extract_changed_paths(
        self, repo_entries: List[str], applied_changes: List[str]
    ) -> List[Path]:
        """Derive candidate file paths that were reported as changed."""
        if not self.repo_root:
            return []

        candidates: List[str] = []

        for entry in repo_entries:
            parts = entry.split("\t")
            if not parts:
                continue
            code = parts[0]
            if code.startswith("??") and len(parts) >= 2:
                candidates.append(parts[1])
            elif (code.startswith("R") or code.startswith("C")) and len(parts) >= 3:
                candidates.append(parts[2])
            elif len(parts) >= 2:
                candidates.append(parts[1])

        for change in applied_changes:
            tokens = change.split()
            if not tokens:
                continue
            verb = tokens[0].lower()
            if (verb in {"add", "modify", "delete"} and len(tokens) >= 2) or (
                verb in {"rename", "copy"} and len(tokens) >= 3
            ):
                candidates.append(tokens[-1])

        seen: Set[str] = set()
        paths: List[Path] = []
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate or candidate.startswith("diff"):
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
                issues.append(
                    f"{rel_path}: file reported as changed but not found on disk"
                )
                continue

            if path.suffix == ".py":
                try:
                    py_compile.compile(str(path), doraise=True)
                except py_compile.PyCompileError as exc:
                    message = getattr(exc, "msg", str(exc))
                    issues.append(f"{rel_path}: python syntax error — {message}")
                except Exception as exc:
                    issues.append(f"{rel_path}: python validation failed — {exc}")
                else:
                    issues.extend(self._python_semantic_issues(path, rel_path))
            elif path.suffix == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    issues.append(f"{rel_path}: invalid JSON — {exc}")
                except Exception as exc:
                    issues.append(f"{rel_path}: json validation failed — {exc}")
            elif path.suffix in {".yaml", ".yml"}:
                if yaml is None:
                    issues.append(
                        f"{rel_path}: skipped YAML validation (PyYAML not installed)"
                    )
                    continue
                try:
                    yaml.safe_load(path.read_text(encoding="utf-8"))
                except yaml.YAMLError as exc:
                    issues.append(f"{rel_path}: invalid YAML — {exc}")
                except Exception as exc:
                    issues.append(f"{rel_path}: yaml validation failed — {exc}")

        return issues

    def _python_semantic_issues(self, path: Path, rel_path: str) -> List[str]:
        """Run lightweight semantic checks for Python files."""
        try:
            source = path.read_text(encoding="utf-8")
        except Exception as exc:
            return [f"{rel_path}: unable to read file for semantic validation — {exc}"]

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            # Already handled by py_compile, no extra issues here.
            return []

        analyzer = _PythonSemanticAnalyzer(path, self.repo_root)
        analyzer.visit(tree)
        return [f"{rel_path}: {issue}" for issue in analyzer.report()]

    def _generate_commit_message(self, repo_root: Path) -> str:
        """Generate a conventional commit message based on repository changes."""
        status_result = self._run_command(["git", "status", "--short"], cwd=repo_root)
        stdout = status_result.get("stdout", "")
        if not stdout.strip():
            return "chore: update workspace"

        scopes: Set[str] = set()
        doc_only = True
        test_only = True

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                continue
            path_fragment = parts[1]
            path = Path(path_fragment)
            if path.parts:
                scopes.add(path.parts[0])
            suffix = path.suffix.lower()
            if suffix not in {".md", ".rst"}:
                doc_only = False
            if "test" not in path.parts and not path.parts[0].startswith("test"):
                test_only = False

        scope_text = "/".join(sorted(scopes)) if scopes else "project"
        if doc_only and not test_only:
            prefix = "docs"
        elif test_only and not doc_only:
            prefix = "test"
        else:
            prefix = "chore"

        return f"{prefix}: update {scope_text}"

    def _extract_heading_titles(self, source_text: str) -> List[str]:
        """Extract top-level headings from a document."""
        titles: List[str] = []
        for line in source_text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            level = len(stripped) - len(stripped.lstrip("#"))
            if level > 3:
                continue
            title = stripped.lstrip("#").strip()
            if title:
                titles.append(title)
        return titles[:12]

    def _extract_feature_list(self, source_text: str) -> List[str]:
        """Extract feature-like bullet items from a document."""
        features: List[str] = []
        for line in source_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped[0] in {"-", "*"}:
                candidate = stripped[1:].strip(" -*\t")
                if candidate:
                    features.append(candidate)
        return features[:12]

    def _select_feature_owner(self, description: str) -> str:
        """Choose an agent owner for a workflow item based on keywords."""
        text = description.lower()
        if any(
            keyword in text for keyword in ("frontend", "ui", "ux", "react", "view")
        ):
            return "frontend-architect"
        if any(
            keyword in text for keyword in ("backend", "api", "service", "database")
        ):
            return "backend-architect"
        if any(
            keyword in text
            for keyword in ("security", "auth", "permission", "compliance")
        ):
            return "security-engineer"
        if any(keyword in text for keyword in ("testing", "qa", "quality")):
            return "quality-engineer"
        if any(
            keyword in text
            for keyword in ("deployment", "infrastructure", "devops", "ci")
        ):
            return "devops-architect"
        return "general-purpose"

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
        data["timestamp"] = assessment.timestamp.isoformat()

        metrics = data.get("metrics", [])
        for metric in metrics:
            dimension = metric.get("dimension")
            if hasattr(dimension, "value"):
                metric["dimension"] = dimension.value

        return data

    def _maybe_run_quality_loop(
        self, context: CommandContext, output: Any
    ) -> Optional[Dict[str, Any]]:
        """Execute the quality scorer's agentic loop when requested."""
        if context.results.get("loop_assessment"):
            return None

        max_iterations = context.loop_iterations or self.quality_scorer.MAX_ITERATIONS
        min_improvement = context.loop_min_improvement

        evaluation_context = dict(context.results)

        def _remediation_improver(
            current_output: Any, loop_context: Dict[str, Any]
        ) -> Any:
            return self._quality_loop_improver(context, current_output, loop_context)

        zen_cleanup = None
        if context.zen_review_enabled:
            zen_cleanup = self._enable_primary_zen_quality(context)

        try:
            improved_output, final_assessment, iteration_history = (
                self.quality_scorer.agentic_loop(
                    output,
                    evaluation_context,
                    improver_func=_remediation_improver,
                    max_iterations=max_iterations,
                    min_improvement=min_improvement,
                )
            )
        except Exception as exc:
            logger.warning(f"Agentic loop execution failed: {exc}")
            context.results["loop_error"] = str(exc)
            return None
        finally:
            if zen_cleanup:
                zen_cleanup()

        context.results["loop_iterations_executed"] = len(iteration_history)
        context.results["loop_assessment"] = self._serialize_assessment(
            final_assessment
        )
        iteration_dicts: List[Dict[str, Any]] = []
        remediation_records = context.results.get("quality_loop_iterations", [])
        for idx, item in enumerate(iteration_history):
            data = asdict(item)
            if idx < len(remediation_records):
                data["remediation"] = remediation_records[idx]
            iteration_dicts.append(data)
        if iteration_dicts:
            context.results["quality_iteration_history"] = iteration_dicts
            if isinstance(improved_output, dict):
                improved_output.setdefault("quality_iteration_history", iteration_dicts)
                if remediation_records:
                    improved_output["quality_loop_iterations"] = remediation_records
        context.results.setdefault("loop_notes", []).append(
            "Quality loop executed with remediation pipeline."
        )

        return {"output": improved_output, "assessment": final_assessment}

    async def _run_zen_reviews(self, context: CommandContext, output: Any) -> None:
        """Execute deferred Zen MCP reviews for loop iterations."""
        if not context.zen_review_enabled:
            return

        targets = context.results.pop("zen_review_targets", []) or []
        if not targets:
            return

        zen_instance = self._get_active_mcp_instance("zen")
        if not zen_instance:
            context.results.setdefault("warnings", []).append(
                "Zen MCP unavailable; loop review skipped."
            )
            return

        review_method = getattr(zen_instance, "review_code", None)
        if not callable(review_method):
            context.results.setdefault("warnings", []).append(
                "Zen MCP missing review_code capability; skipping zen-review."
            )
            return

        reviews: List[Dict[str, Any]] = []
        for target in targets:
            diff_blob = target.get("diff")
            if not diff_blob:
                continue
            try:
                review_payload = await self._execute_zen_review(
                    review_method,
                    context,
                    diff_blob,
                    files=target.get("files") or [],
                    iteration=target.get("iteration"),
                )
            except Exception as exc:
                logger.warning(f"Zen review failed: {exc}")
                context.results.setdefault("zen_review_errors", []).append(str(exc))
                continue

            reviews.append(
                {
                    "iteration": target.get("iteration"),
                    "files": target.get("files") or [],
                    "result": review_payload,
                }
            )

        if reviews:
            context.results.setdefault("zen_reviews", []).extend(reviews)
            if isinstance(output, dict):
                output["zen_reviews"] = context.results["zen_reviews"]

    async def _execute_zen_review(
        self,
        review_method: Callable[..., Any],
        context: CommandContext,
        diff_blob: str,
        *,
        files: List[str],
        iteration: Optional[int],
    ) -> Dict[str, Any]:
        """Invoke the zen review coroutine and normalize its response."""
        metadata = {
            "command": context.command.raw_string,
            "iteration": iteration,
            "loop_requested": context.results.get("loop_requested", False),
        }

        result = await review_method(
            diff_blob,
            files=files,
            model=context.zen_review_model or "gpt-5",
            metadata=metadata,
        )

        if isinstance(result, dict):
            return result
        return {"summary": str(result), "model": context.zen_review_model or "gpt-5"}

    def _get_active_mcp_instance(self, name: str) -> Optional[Any]:
        entry = self.active_mcp_servers.get(name)
        if not entry:
            return None
        return entry.get("instance")

    def _evaluate_quality_gate(
        self,
        context: CommandContext,
        output: Any,
        changed_paths: List[Path],
        status: str,
        precomputed: Optional[QualityAssessment] = None,
    ) -> Optional[QualityAssessment]:
        """Run quality scoring against the command result."""
        evaluation_context = dict(context.results)
        evaluation_context["status"] = status
        evaluation_context["changed_files"] = [
            self._relative_to_repo_path(path) for path in changed_paths
        ]

        try:
            assessment = precomputed or self.quality_scorer.evaluate(
                output, evaluation_context
            )
            if assessment and not assessment.passed:
                if precomputed:
                    return assessment

                def _remediation_improver(current_output, loop_context):
                    return self._quality_loop_improver(
                        context, current_output, loop_context
                    )

                (remediated_output, loop_assessment, iteration_history) = (
                    self.quality_scorer.agentic_loop(
                        output, evaluation_context, improver_func=_remediation_improver
                    )
                )

                output = remediated_output
                if iteration_history:
                    remediation_records = context.results.get(
                        "quality_loop_iterations", []
                    )
                    serialized = []
                    for idx, item in enumerate(iteration_history):
                        data = asdict(item)
                        if idx < len(remediation_records):
                            data["remediation"] = remediation_records[idx]
                        serialized.append(data)
                    context.results["quality_iteration_history"] = serialized

                return loop_assessment

            return assessment
        except Exception as exc:
            logger.warning(f"Quality scoring failed: {exc}")
            context.results["quality_assessment_error"] = str(exc)
            return None

    def _record_requires_evidence_metrics(
        self,
        command_name: str,
        requires_evidence: bool,
        derived_status: str,
        success: bool,
        assessment: Optional[QualityAssessment],
        static_issues: List[str],
        consensus: Optional[Dict[str, Any]],
        context_snapshot: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send telemetry for requires-evidence command outcomes."""
        if not requires_evidence or not self.monitor:
            return

        snapshot = context_snapshot or {}
        execution_mode = str(snapshot.get("execution_mode") or "standard")

        tags = {
            "command": command_name,
            "status": derived_status,
            "mode": execution_mode,
        }

        base = "commands.requires_evidence"
        self.monitor and self.monitor.record_metric(f"{base}.invocations", 1, MetricType.COUNTER, tags)

        if derived_status == "plan-only":
            self.monitor and self.monitor.record_metric(f"{base}.plan_only", 1, MetricType.COUNTER, tags)
            self.monitor and self.monitor.record_metric(
                f"{base}.missing_evidence", 1, MetricType.COUNTER, tags
            )

        if static_issues:
            issue_tags = dict(tags)
            issue_tags["issue_count"] = str(len(static_issues))
            self.monitor and self.monitor.record_metric(
                f"{base}.static_validation_fail",
                len(static_issues),
                MetricType.COUNTER,
                issue_tags,
            )
            self.monitor and self.monitor.record_metric(
                f"{base}.static_issue_count",
                len(static_issues),
                MetricType.GAUGE,
                issue_tags,
            )

        if assessment:
            score_value = assessment.overall_score
            if derived_status == "plan-only":
                score_value = min(score_value, assessment.threshold - 10.0, 69.0)

            score_tags = dict(tags)
            score_tags["score"] = f"{score_value:.1f}"
            score_tags["threshold"] = f"{assessment.threshold:.1f}"
            self.monitor and self.monitor.record_metric(
                f"{base}.quality_score", score_value, MetricType.GAUGE, score_tags
            )
            assessment_passed = bool(assessment.passed)
            if derived_status == "plan-only":
                assessment_passed = False
            metric_name = (
                f"{base}.quality_pass" if assessment_passed else f"{base}.quality_fail"
            )
            self.monitor and self.monitor.record_metric(metric_name, 1, MetricType.COUNTER, score_tags)

        fast_codex_state = {}
        raw_fast_codex = snapshot.get("fast_codex")
        if isinstance(raw_fast_codex, dict):
            fast_codex_state = raw_fast_codex

        if fast_codex_state:
            fast_tags = {
                "command": command_name,
                "mode": execution_mode,
                "active": str(bool(fast_codex_state.get("active"))),
            }
            self.monitor and self.monitor.record_metric(
                "commands.fast_codex.requested", 1, MetricType.COUNTER, fast_tags
            )
            if fast_codex_state.get("active"):
                self.monitor and self.monitor.record_metric(
                    "commands.fast_codex.active", 1, MetricType.COUNTER, fast_tags
                )

            else:
                blocked = fast_codex_state.get("blocked") or []
                blocked_tags = dict(fast_tags)
                if blocked:
                    blocked_tags["blocked"] = ",".join(
                        sorted(str(reason) for reason in blocked)
                    )
                self.monitor and self.monitor.record_metric(
                    "commands.fast_codex.blocked", 1, MetricType.COUNTER, blocked_tags
                )

        if snapshot.get("fast_codex_cli"):
            cli_tags = {
                "command": command_name,
                "mode": execution_mode,
            }
            self.monitor and self.monitor.record_metric(
                "commands.fast_codex.cli.used",
                1,
                MetricType.COUNTER,
                cli_tags,
            )
            cli_state = snapshot.get("fast_codex") or {}
            cli_detail = cli_state.get("cli") or {}
            try:
                duration_value = float(cli_detail.get("duration_s", 0.0))
            except (TypeError, ValueError):
                duration_value = 0.0
            if duration_value:
                self.monitor and self.monitor.record_metric(
                    "commands.fast_codex.cli.duration",
                    duration_value,
                    MetricType.TIMER,
                    cli_tags,
                )

        event_payload = {
            "timestamp": datetime.now().isoformat(),
            "command": command_name,
            "requires_evidence": requires_evidence,
            "status": derived_status,
            "success": success,
            "static_issues": static_issues,
            "static_issue_count": len(static_issues),
            "consensus_reached": bool(consensus.get("consensus_reached"))
            if isinstance(consensus, dict)
            else None,
            "quality_score": assessment.overall_score if assessment else None,
            "quality_threshold": assessment.threshold if assessment else None,
            "consensus_vote_type": snapshot.get("consensus_vote_type"),
            "consensus_quorum": snapshot.get("consensus_quorum_size"),
            "plan_only": derived_status == "plan-only",
            "execution_mode": execution_mode,
            "fast_codex": snapshot.get("fast_codex"),
            "fast_codex_cli": snapshot.get("fast_codex_cli"),
        }
        try:
            self.monitor and self.monitor.record_event("hallucination.guardrail", event_payload)
        except Exception:
            logger.debug("Failed to record hallucination event payload", exc_info=True)
        else:
            self.monitor and self.monitor.record_metric(
                f"{base}.quality_missing", 1, MetricType.COUNTER, tags
            )

        if consensus:
            consensus_tags = dict(tags)
            consensus_tags["consensus"] = str(consensus.get("consensus_reached", False))
            decision = consensus.get("final_decision")
            if decision is not None:
                consensus_tags["decision"] = str(decision)
            self.monitor and self.monitor.record_metric(
                f"{base}.consensus", 1, MetricType.COUNTER, consensus_tags
            )
            if not consensus.get("consensus_reached", False):
                self.monitor and self.monitor.record_metric(
                    f"{base}.consensus_failed", 1, MetricType.COUNTER, consensus_tags
                )

        outcome_metric = f"{base}.success" if success else f"{base}.failure"
        self.monitor and self.monitor.record_metric(outcome_metric, 1, MetricType.COUNTER, tags)

    def _attach_plan_only_guidance(
        self, context: CommandContext, output: Optional[Dict[str, Any]]
    ) -> None:
        guidance: List[str] = []

        change_plan = context.results.get("change_plan") or []
        suggested_paths: List[str] = []
        for entry in change_plan:
            path = entry.get("path") if isinstance(entry, dict) else None
            if not path:
                continue
            path_str = str(path)
            if path_str not in suggested_paths:
                suggested_paths.append(path_str)

        if suggested_paths:
            preview = ", ".join(suggested_paths[:3])
            remaining = len(suggested_paths) - 3
            if remaining > 0:
                preview = f"{preview} (+{remaining} more)"
            guidance.append(f"Suggested file targets: {preview}")

        safe_directory = context.results.get("safe_apply_directory")
        if safe_directory:
            guidance.append(f"Inspect safe-apply snapshot at {safe_directory}")

        safe_files = context.results.get("safe_apply_files") or []
        if safe_files and len(safe_files) <= 3:
            guidance.append(
                "Safe-apply files staged: "
                + ", ".join(str(path) for path in safe_files)
            )

        if not guidance:
            return

        existing = context.results.setdefault("plan_only_guidance", [])
        for line in guidance:
            if line not in existing:
                existing.append(line)

        if isinstance(output, dict):
            guidance_block = output.setdefault("guidance", {})
            plan_list = guidance_block.setdefault("plan_only", [])
            if isinstance(plan_list, list):
                for line in guidance:
                    if line not in plan_list:
                        plan_list.append(line)

        for line in guidance:
            if line not in context.errors:
                context.errors.append(line)

    def _safe_apply_requested(self, context: CommandContext) -> bool:
        flags = context.command.flags
        parameters = context.command.parameters
        return any(
            [
                self._is_truthy(flags.get("safe-apply")),
                self._is_truthy(flags.get("safe_apply")),
                self._is_truthy(parameters.get("safe-apply")),
                self._is_truthy(parameters.get("safe_apply")),
            ]
        )

    def _should_auto_trigger_quality_loop(
        self, context: CommandContext, derived_status: str
    ) -> bool:
        if derived_status != "plan-only":
            return False
        if context.loop_enabled:
            return False
        if not self._safe_apply_requested(context):
            return False
        if context.results.get("changed_files"):
            return False
        if context.results.get("safe_apply_snapshots") or context.results.get(
            "safe_apply_directory"
        ):
            return True
        return False

    def _write_safe_apply_snapshot(
        self, context: CommandContext, stubs: Sequence[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        import tempfile; metrics_dir = Path(tempfile.gettempdir()) / "superclaude_metrics"
        base_dir = metrics_dir / "safe_apply" / context.session_id
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        snapshot_dir = base_dir / timestamp

        saved_files: List[str] = []
        created_any = False

        for entry in stubs:
            raw_path = entry.get("path")
            content = entry.get("content", "")
            if not raw_path or not isinstance(content, str):
                continue

            raw_string = str(raw_path).strip()
            if not raw_string:
                continue

            rel_parts = [
                part for part in Path(raw_string).parts if part not in ("", ".")
            ]
            if not rel_parts:
                continue
            if rel_parts[0] == ".." or any(part == ".." for part in rel_parts):
                continue

            if raw_string.startswith(("/", "\\")) and len(rel_parts) > 1:
                rel_parts = rel_parts[1:]

            rel_path = Path(*rel_parts)

            target = snapshot_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_text(content, encoding="utf-8")
            except Exception as exc:
                logger.debug("Failed to write safe-apply stub %s: %s", target, exc)
                continue

            created_any = True
            saved_files.append(str(target.relative_to(snapshot_dir)))

        if not created_any:
            return None

        manifest = {
            "directory": str(snapshot_dir),
            "files": saved_files,
        }

        context.results.setdefault("safe_apply_snapshots", []).append(manifest)
        context.results["safe_apply_directory"] = manifest["directory"]
        context.results["safe_apply_files"] = saved_files

        self._prune_safe_apply_snapshots(base_dir)

        return manifest

    def _prune_safe_apply_snapshots(self, session_root: Path, keep: int = 3) -> None:
        try:
            candidates = [path for path in session_root.iterdir() if path.is_dir()]
        except FileNotFoundError:
            return

        candidates.sort(key=lambda path: path.name, reverse=True)
        for obsolete in candidates[keep:]:
            try:
                shutil.rmtree(obsolete)
            except Exception as exc:
                logger.debug("Safe-apply cleanup skipped for %s: %s", obsolete, exc)

    def _maybe_record_plan_only_event(
        self,
        parsed: ParsedCommand,
        context: CommandContext,
        derived_status: str,
        requires_evidence: bool,
    ) -> None:
        if derived_status != "plan-only":
            return

        event: Dict[str, Any] = {
            "command": parsed.name,
            "arguments": list(parsed.arguments),
            "flags": sorted(parsed.flags.keys()),
            "requires_evidence": requires_evidence,
            "status": derived_status,
            "session_id": context.session_id,
            "missing_evidence": bool(context.results.get("missing_evidence")),
            "plan_only_agents": list(context.results.get("plan_only_agents", [])),
            "guidance": list(context.results.get("plan_only_guidance", [])),
            "safe_apply_requested": self._safe_apply_requested(context),
        }

        change_plan = context.results.get("change_plan") or []
        if change_plan:
            summary: List[Dict[str, Any]] = []
            for entry in change_plan[:10]:
                if not isinstance(entry, dict):
                    continue
                summary.append(
                    {
                        "path": entry.get("path"),
                        "intent": entry.get("intent"),
                        "description": entry.get("description")
                        or entry.get("summary")
                        or entry.get("title"),
                    }
                )
            event["change_plan"] = summary
            event["change_plan_count"] = len(change_plan)
        else:
            event["change_plan_count"] = 0

        consensus = (
            context.consensus_summary
            if isinstance(context.consensus_summary, dict)
            else None
        )
        if consensus:
            event["consensus"] = {
                "consensus_reached": consensus.get("consensus_reached"),
                "models": consensus.get("models"),
                "decision": consensus.get("final_decision"),
            }
        else:
            event["consensus"] = None

        errors = context.errors[:5]
        if errors:
            event["errors"] = errors

        if context.results.get("retrieved_context"):
            event["retrieval_hits"] = len(context.results["retrieved_context"])

        snapshots = context.results.get("safe_apply_snapshots") or []
        if snapshots:
            event["safe_apply_snapshot"] = snapshots[-1]
        if context.results.get("safe_apply_directory"):
            event["safe_apply_directory"] = context.results["safe_apply_directory"]

        # Monitoring removed - plan_only_event logging disabled
        pass

    async def _dispatch_rube_actions(
        self, context: CommandContext, output: Any
    ) -> List[str]:
        """Send orchestration data to Rube MCP when available."""
        if "rube" not in context.mcp_servers:
            return []

        rube_entry = self.active_mcp_servers.get("rube")
        if not rube_entry:
            return []

        instance = rube_entry.get("instance")
        if instance is None or not hasattr(instance, "invoke"):
            return []

        request = self._build_rube_request(context, output)
        if not request:
            return []

        tool = request["tool"]
        payload = request["payload"]

        try:
            response = await instance.invoke(tool, payload)
            context.results["rube_response"] = response
            status = (
                response.get("status", "ok") if isinstance(response, dict) else "ok"
            )

            if self.monitor:
                base = "commands.rube"
                tags = {"command": context.command.name, "status": status}
                self.monitor and self.monitor.record_metric(
                    f"{base}.invocations", 1, MetricType.COUNTER, tags
                )
                metric = f"{base}.dry_run" if status == "dry-run" else f"{base}.success"
                self.monitor and self.monitor.record_metric(metric, 1, MetricType.COUNTER, tags)

            return [f"rube:{tool}:{status}"]
        except Exception as exc:  # pragma: no cover - network behaviour
            message = f"Rube automation failed: {exc}"
            logger.warning(message)
            context.errors.append(message)
            if self.monitor:
                tags = {"command": context.command.name}
                self.monitor and self.monitor.record_metric(
                    "commands.rube.failure", 1, MetricType.COUNTER, tags
                )
            return [f"rube:{tool}:error"]

    def _build_rube_request(
        self, context: CommandContext, output: Any
    ) -> Optional[Dict[str, Any]]:
        """Construct a payload describing the action for Rube MCP."""
        command_name = context.command.name
        tool_map = {
            "task": "workflow.dispatch",
            "workflow": "workflow.dispatch",
            "spawn": "workflow.dispatch",
            "improve": "automation.log",
            "implement": "automation.log",
        }

        tool = tool_map.get(command_name)
        if not tool:
            return None

        payload: Dict[str, Any] = {
            "command": command_name,
            "session_id": context.session_id,
            "summary": self._summarize_rube_context(command_name, output, context),
            "metadata": {
                "status": context.results.get("status", context.command.name),
                "requires_evidence": context.metadata.requires_evidence,
                "errors": list(context.errors),
            },
        }

        if context.command.arguments:
            payload["arguments"] = list(context.command.arguments)
        if context.command.parameters:
            payload["parameters"] = dict(context.command.parameters)

        return {"tool": tool, "payload": payload}

    def _summarize_rube_context(
        self,
        command_name: str,
        output: Any,
        context: CommandContext,
    ) -> str:
        """Generate a short summary for Rube automation payloads."""
        if isinstance(output, dict):
            summary = (
                output.get("summary")
                or output.get("description")
                or output.get("title")
            )
            if isinstance(summary, str) and summary.strip():
                return summary.strip()[:400]

        applied = context.results.get("applied_changes") or context.results.get(
            "change_plan"
        )
        if isinstance(applied, list) and applied:
            return f"{command_name} touched {len(applied)} files."

        return f"{command_name} executed with status {context.results.get('status', 'unknown')}"

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
        return metadata.name in {"implement"}

    def _is_truthy(self, value: Any) -> bool:
        """Interpret diverse flag representations as boolean truthy values."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"1", "true", "yes", "on", "enabled"}
        return False

    def _should_run_tests(self, parsed: ParsedCommand) -> bool:
        """Determine if automated tests should be executed."""
        keys = ("with-tests", "with_tests", "run-tests", "run_tests")

        for key in keys:
            if self._is_truthy(parsed.flags.get(key)):
                return True
            if self._is_truthy(parsed.parameters.get(key)):
                return True

        # Always run when invoking the dedicated test command.
        return parsed.name == "test"

    def _run_requested_tests(self, parsed: ParsedCommand) -> Dict[str, Any]:
        """Execute project tests and capture results."""
        pytest_args: List[str] = ["-q"]
        markers: List[str] = []
        targets: List[str] = []

        parameters = parsed.parameters
        flags = parsed.flags

        coverage_enabled = self._is_truthy(flags.get("coverage")) or self._is_truthy(
            parameters.get("coverage")
        )
        if coverage_enabled:
            cov_target = parameters.get("cov")
            if not isinstance(cov_target, str) or not cov_target.strip():
                cov_target = "SuperClaude"
            pytest_args.extend(
                [
                    f"--cov={cov_target.strip()}",
                    "--cov-report=term-missing",
                    "--cov-report=html",
                ]
            )

        type_param = parameters.get("type")
        if isinstance(type_param, str):
            normalized_type = type_param.strip().lower()
            if normalized_type in {"unit", "integration", "e2e"}:
                markers.append(normalized_type)

        if self._is_truthy(flags.get("e2e")) or self._is_truthy(parameters.get("e2e")):
            markers.append("e2e")

        def _extend_markers(raw: Any) -> None:
            if raw is None:
                return
            values: Iterable[str]
            if isinstance(raw, str):
                values = [
                    token.strip() for token in re.split(r"[\s,]+", raw) if token.strip()
                ]
            elif isinstance(raw, (list, tuple, set)):
                values = [str(item).strip() for item in raw if str(item).strip()]
            else:
                values = [str(raw).strip()]
            for value in values:
                markers.append(value)

        _extend_markers(parameters.get("marker"))
        _extend_markers(parameters.get("markers"))

        def _looks_like_test_target(argument: str) -> bool:
            if not argument or not isinstance(argument, str):
                return False
            if argument.startswith("-"):
                return False
            if "/" in argument or "\\" in argument:
                return True
            if "::" in argument:
                return True
            suffixes = (
                ".py",
                ".ts",
                ".tsx",
                ".js",
                ".rs",
                ".go",
                ".java",
                ".kt",
                ".cs",
            )
            return argument.endswith(suffixes)

        for argument in parsed.arguments or []:
            if _looks_like_test_target(str(argument)):
                targets.append(str(argument))
        target_param = parameters.get("target")
        if isinstance(target_param, str) and target_param.strip():
            targets.append(target_param.strip())

        unique_markers: List[str] = []
        seen_markers: Set[str] = set()
        for marker in markers:
            normalized = marker.strip()
            if not normalized:
                continue
            if normalized not in seen_markers:
                seen_markers.add(normalized)
                unique_markers.append(normalized)

        command: List[str] = ["pytest", *pytest_args]
        if unique_markers:
            marker_expression = " or ".join(unique_markers)
            command.extend(["-m", marker_expression])
        if targets:
            command.extend(targets)

        env = os.environ.copy()
        env.setdefault("PYENV_DISABLE_REHASH", "1")

        start = datetime.now()
        try:
            result = subprocess.run(
                command,
                cwd=str(self.repo_root or Path.cwd()),
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            logger.warning(f"Test runner not available: {exc}")
            return {
                "command": " ".join(command),
                "args": command,
                "passed": False,
                "pass_rate": 0.0,
                "stdout": "",
                "stderr": str(exc),
                "duration_s": 0.0,
                "error": "pytest_not_found",
                "coverage": None,
                "markers": unique_markers,
                "targets": targets,
            }
        except Exception as exc:
            logger.error(f"Unexpected error running tests: {exc}")
            return {
                "command": " ".join(command),
                "args": command,
                "passed": False,
                "pass_rate": 0.0,
                "stdout": "",
                "stderr": str(exc),
                "duration_s": 0.0,
                "error": "test_execution_error",
                "coverage": None,
                "markers": unique_markers,
                "targets": targets,
            }

        duration = (datetime.now() - start).total_seconds()
        passed = result.returncode == 0
        stdout_text = result.stdout or ""
        stderr_text = result.stderr or ""
        metrics = self._parse_pytest_output(stdout_text, stderr_text)

        pass_rate = metrics.get("pass_rate")
        if pass_rate is None:
            pass_rate = 1.0 if passed else 0.0

        output = {
            "command": " ".join(command),
            "args": command,
            "passed": passed,
            "pass_rate": pass_rate,
            "stdout": self._truncate_output(stdout_text.strip()),
            "stderr": self._truncate_output(stderr_text.strip()),
            "duration_s": duration,
            "exit_code": result.returncode,
            "coverage": metrics.get("coverage"),
            "summary": metrics.get("summary"),
            "tests_passed": metrics.get("tests_passed", 0),
            "tests_failed": metrics.get("tests_failed", 0),
            "tests_errored": metrics.get("tests_errored", 0),
            "tests_skipped": metrics.get("tests_skipped", 0),
            "tests_collected": metrics.get("tests_collected"),
            "markers": unique_markers,
            "targets": targets,
        }

        if metrics.get("errors"):
            output["errors"] = metrics["errors"]

        return output

    def _summarize_test_results(self, test_results: Dict[str, Any]) -> str:
        """Create a concise summary string for executed tests."""
        command = test_results.get("command", "tests")
        status = "pass" if test_results.get("passed") else "fail"
        duration = test_results.get("duration_s")
        duration_part = (
            f" in {duration:.2f}s" if isinstance(duration, (int, float)) else ""
        )
        return f"{command} ({status}{duration_part})"

    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Extract structured metrics from pytest stdout/stderr."""
        combined = "\n".join(part for part in (stdout, stderr) if part)

        metrics: Dict[str, Any] = {
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_errored": 0,
            "tests_skipped": 0,
            "tests_collected": None,
            "pass_rate": None,
            "summary": None,
            "coverage": None,
            "errors": [],
        }

        if not combined:
            return metrics

        for line in combined.splitlines():
            stripped = line.strip()
            if re.match(r"=+\s+.+\s+=+", stripped):
                metrics["summary"] = stripped

        collected_match = re.search(r"collected\s+(\d+)\s+items?", combined)
        if collected_match:
            metrics["tests_collected"] = int(collected_match.group(1))

        for count, label in re.findall(
            r"(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed)", combined
        ):
            value = int(count)
            normalized = label.rstrip("s")
            if normalized == "passed":
                metrics["tests_passed"] += value
            elif normalized == "failed":
                metrics["tests_failed"] += value
            elif normalized == "error":
                metrics["tests_errored"] += value
            elif normalized == "skipped" or normalized == "xfailed":
                metrics["tests_skipped"] += value
            elif normalized == "xpassed":
                metrics["tests_passed"] += value

        executed = (
            metrics["tests_passed"] + metrics["tests_failed"] + metrics["tests_errored"]
        )
        if executed:
            metrics["pass_rate"] = metrics["tests_passed"] / executed

        coverage_match = re.search(r"TOTAL\s+(?:\d+\s+){1,4}(\d+(?:\.\d+)?)%", combined)
        if not coverage_match:
            coverage_match = re.search(
                r"coverage[:\s]+(\d+(?:\.\d+)?)%", combined, re.IGNORECASE
            )
        if coverage_match:
            try:
                metrics["coverage"] = float(coverage_match.group(1)) / 100.0
            except (TypeError, ValueError):
                metrics["coverage"] = None

        failure_entries = re.findall(r"FAILED\s+([^\s]+)\s+-\s+(.+)", combined)
        for test_name, message in failure_entries:
            metrics["errors"].append(f"{test_name} - {message.strip()}")

        return metrics

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
            "command": parsed.name,
            "flags": " ".join(sorted(parsed.flags.keys())),
            "task": " ".join(parsed.arguments),
            "parameters": json.dumps(parsed.parameters, sort_keys=True, default=str)
            if parsed.parameters
            else "",
        }

        # Always reset to normal before detection to avoid state bleed.
        self.behavior_manager.switch_mode(
            BehavioralMode.NORMAL, detection_context, trigger="reset"
        )

        detected_mode = self.behavior_manager.detect_mode_from_context(
            detection_context
        )
        if detected_mode:
            self.behavior_manager.switch_mode(
                detected_mode, detection_context, trigger="auto"
            )

        applied = self.behavior_manager.apply_mode_behaviors(detection_context)
        return {
            "mode": self.behavior_manager.get_current_mode().value,
            "context": applied,
        }

    def _apply_execution_flags(self, context: CommandContext) -> None:
        """Apply execution flags such as think depth, loops, consensus, and delegation."""
        parsed = context.command

        think_info = self._resolve_think_level(parsed)
        context.think_level = think_info["level"]
        context.results["think_level"] = think_info["level"]
        context.results["think_requested"] = think_info["requested"]

        loop_info = self._resolve_loop_request(parsed)
        context.loop_enabled = loop_info["enabled"]
        context.loop_iterations = loop_info["iterations"]
        context.loop_min_improvement = loop_info["min_improvement"]
        if loop_info["enabled"]:
            context.results["loop_requested"] = True
            if loop_info["iterations"] is not None:
                context.results["loop_iterations_requested"] = loop_info["iterations"]
            if loop_info["min_improvement"] is not None:
                context.results["loop_min_improvement_requested"] = loop_info[
                    "min_improvement"
                ]

        zen_review = self._resolve_zen_review_request(parsed, loop_info["enabled"])
        context.zen_review_enabled = zen_review["enabled"]
        context.zen_review_model = zen_review["model"]
        context.results["zen_review_enabled"] = context.zen_review_enabled
        if zen_review["model"]:
            context.results["zen_review_model"] = zen_review["model"]
        if context.zen_review_enabled:
            servers = list(context.metadata.mcp_servers or [])
            if "zen" not in servers:
                servers.append("zen")
            context.metadata.mcp_servers = servers

        context.consensus_forced = self._flag_present(parsed, "consensus")
        context.results["consensus_forced"] = context.consensus_forced

        self._apply_auto_delegation(context)
        self._apply_fast_codex_mode(context)

    def _resolve_think_level(self, parsed: ParsedCommand) -> Dict[str, Any]:
        """Resolve requested think level (1-3) from command flags/parameters."""
        default_level = 2
        requested = self._flag_present(parsed, "think")

        candidate_keys = ["think", "think_level", "think-depth", "think_depth", "depth"]
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

        return {"level": level, "requested": requested or value is not None}

    def _resolve_loop_request(self, parsed: ParsedCommand) -> Dict[str, Any]:
        """Determine whether agentic loop is requested and capture limits."""
        enabled = self._flag_present(parsed, "loop")
        iterations = None
        min_improvement = None

        iteration_keys = ["loop", "loop_iterations", "loop-count", "loop_count"]
        for key in iteration_keys:
            if key in parsed.parameters:
                iterations = self._clamp_int(
                    parsed.parameters[key],
                    1,
                    self.quality_scorer.MAX_ITERATIONS,
                    self.quality_scorer.MAX_ITERATIONS,
                )
                enabled = True
                break

        min_keys = ["loop-min", "loop_min", "loop-improvement", "loop_improvement"]
        for key in min_keys:
            if key in parsed.parameters:
                min_improvement = self._coerce_float(parsed.parameters[key], None)
                enabled = True
                break

        return {
            "enabled": enabled,
            "iterations": iterations,
            "min_improvement": min_improvement,
        }

    def _resolve_zen_review_request(
        self, parsed: ParsedCommand, loop_requested: bool
    ) -> Dict[str, Any]:
        """Resolve whether zen-review should run and which model to use."""
        enabled = loop_requested or self._flag_present(parsed, "zen-review")
        model = None

        model_keys = ["zen-model", "zen_model", "zen-review-model", "zen_model_name"]
        for key in model_keys:
            if key in parsed.parameters:
                model = str(parsed.parameters[key]).strip() or None
                enabled = True
                break

        if not model:
            model = "gpt-5"

        return {"enabled": enabled, "model": model}

    def _apply_auto_delegation(self, context: CommandContext) -> None:
        """Handle --delegate and related auto-delegation flags."""
        parsed = context.command

        explicit_targets = self._extract_delegate_targets(parsed)
        if explicit_targets:
            selected = self._deduplicate(explicit_targets)
            context.delegated_agents.extend(selected)
            context.delegated_agents = self._deduplicate(context.delegated_agents)
            context.delegation_strategy = "explicit"
            context.results["delegation"] = {
                "requested": True,
                "strategy": "explicit",
                "selected_agent": selected[0] if selected else None,
                "selected_agents": selected,
            }
            context.results["delegated_agents"] = context.delegated_agents
            return

        delegate_flags = [
            "delegate",
            "delegate_core",
            "delegate-core",
            "delegate_extended",
            "delegate-extended",
            "delegate_debug",
            "delegate-debug",
            "delegate_refactor",
            "delegate-refactor",
            "delegate_search",
            "delegate-search",
        ]
        if not any(self._flag_present(parsed, flag) for flag in delegate_flags):
            return

        strategy = "auto"
        if self._flag_present(parsed, "delegate_extended") or self._flag_present(
            parsed, "delegate-extended"
        ):
            strategy = "extended"
        elif self._flag_present(parsed, "delegate_core") or self._flag_present(
            parsed, "delegate-core"
        ):
            strategy = "core"
        elif self._flag_present(parsed, "delegate_debug") or self._flag_present(
            parsed, "delegate-debug"
        ):
            strategy = "debug"
        elif self._flag_present(parsed, "delegate_refactor") or self._flag_present(
            parsed, "delegate-refactor"
        ):
            strategy = "refactor"
        elif self._flag_present(parsed, "delegate_search") or self._flag_present(
            parsed, "delegate-search"
        ):
            strategy = "search"

        category_hint = None
        for key, category in self.delegate_category_map.items():
            if self._flag_present(parsed, key):
                category_hint = category
                break

        selection_context = self._build_delegation_context(context)

        try:
            matches = self.extended_agent_loader.select_agent(
                selection_context, category_hint=category_hint, top_n=5
            )
        except Exception as exc:
            logger.warning(f"Delegation selection failed: {exc}")
            context.results["delegation"] = {
                "requested": True,
                "strategy": strategy,
                "error": str(exc),
            }
            return

        if strategy == "extended":
            matches = [
                match for match in matches if self._is_extended_agent(match.agent_id)
            ] or matches

        if not matches:
            context.results["delegation"] = {
                "requested": True,
                "strategy": strategy,
                "error": "No matching agents found",
            }
            return

        primary = matches[0]
        context.delegated_agents.append(primary.agent_id)
        context.delegated_agents = self._deduplicate(context.delegated_agents)
        context.delegation_strategy = strategy

        context.results["delegation"] = {
            "requested": True,
            "strategy": strategy,
            "selected_agent": primary.agent_id,
            "confidence": primary.confidence,
            "score": round(primary.total_score, 3),
            "matched_criteria": primary.matched_criteria,
            "candidates": [
                {
                    "agent": match.agent_id,
                    "score": round(match.total_score, 3),
                    "confidence": match.confidence,
                }
                for match in matches[:3]
            ],
            "selection_context": {
                "task": selection_context.get("task", "")[:120],
                "keywords": selection_context.get("keywords", [])[:5],
                "domains": selection_context.get("domains", [])[:5],
                "languages": selection_context.get("languages", [])[:5],
            },
        }
        context.results["delegated_agents"] = context.delegated_agents

    def _apply_fast_codex_mode(self, context: CommandContext) -> None:
        """Configure fast Codex execution mode when the flag is present."""
        parsed = context.command
        metadata = context.metadata

        context.results.setdefault("execution_mode", "standard")
        context.active_personas = list(metadata.personas or [])
        context.fast_codex_active = False
        context.fast_codex_blocked = []

        fast_state = context.results.setdefault(
            "fast_codex",
            {
                "requested": False,
                "active": False,
                "personas": list(context.active_personas),
            },
        )
        fast_state["personas"] = list(context.active_personas)

        supported = any(
            isinstance(flag, dict)
            and (flag.get("name") or "").replace("_", "-").lower() == "fast-codex"
            for flag in (metadata.flags or [])
        )
        requested = supported and (
            self._flag_present(parsed, "fast-codex")
            or self._flag_present(parsed, "fast_codex")
        )
        context.fast_codex_requested = requested

        if not requested:
            fast_state.update(
                {
                    "requested": False,
                    "active": False,
                }
            )
            fast_state.pop("blocked", None)
            return

        block_reasons: List[str] = []
        if context.consensus_forced:
            block_reasons.append("consensus-required")
        if self._flag_present(parsed, "safe") or self._flag_present(parsed, "security"):
            block_reasons.append("safety-requested")

        if block_reasons:
            context.fast_codex_blocked = block_reasons
            fast_state.update(
                {
                    "requested": True,
                    "active": False,
                    "blocked": block_reasons,
                }
            )
            self._record_fast_codex_event(
                context,
                "blocked",
                "Fast-codex disabled by guardrails.",
                {"reasons": block_reasons},
            )
            context.results["execution_mode"] = "standard"
            return

        fast_state["requested"] = True
        self._record_fast_codex_event(
            context,
            "flag-detected",
            "--fast-codex detected; preparing Codex implementer.",
            {"personas": context.active_personas},
        )

        if not CodexCLIClient.is_available():
            binary = CodexCLIClient.resolve_binary()
            self._record_fast_codex_event(
                context,
                "cli-missing",
                f"Codex CLI '{binary}' is not available on PATH.",
                {"binary": binary},
            )
            raise CodexCLIUnavailable(
                "Codex CLI is required for --fast-codex. Install the 'codex' CLI or "
                "set SUPERCLAUDE_CODEX_CLI to its path."
            )

        context.fast_codex_active = True
        context.active_personas = ["codex-implementer"]
        context.results["execution_mode"] = "fast-codex"
        fast_state.update(
            {
                "requested": True,
                "active": True,
                "personas": list(context.active_personas),
            }
        )
        fast_state.pop("blocked", None)
        self._record_fast_codex_event(
            context,
            "activated",
            "Codex implementer engaged for this run.",
            {"personas": context.active_personas},
        )

    def _record_fast_codex_event(
        self,
        context: CommandContext,
        phase: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a structured fast-codex event for TUI/telemetry surfaces."""

        if not (context.fast_codex_requested or phase == "cli-missing"):
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "message": message,
        }
        if details:
            entry["details"] = details

        log = context.results.setdefault("fast_codex_log", [])
        log.append(entry)

        fast_state = context.results.get("fast_codex")
        if isinstance(fast_state, dict):
            fast_state["events"] = log

    @staticmethod
    def _truncate_fast_codex_stream(payload: Optional[str], limit: int = 600) -> str:
        """Return a concise preview of Codex CLI stdout/stderr for display."""

        if not payload:
            return ""
        snippet = str(payload).strip()
        if len(snippet) <= limit:
            return snippet
        head = snippet[: limit // 2].rstrip()
        tail = snippet[-limit // 2 :].lstrip()
        return f"{head} … {tail}"

    def _build_delegation_context(self, context: CommandContext) -> Dict[str, Any]:
        """Construct context payload for delegate selection."""
        parsed = context.command
        task_text = " ".join(parsed.arguments).strip() or parsed.raw_string
        parameters = parsed.parameters

        languages = self._to_list(
            parameters.get("language")
            or parameters.get("languages")
            or parameters.get("lang")
        )
        domains = self._to_list(parameters.get("domain") or parameters.get("domains"))
        if context.metadata.category and context.metadata.category not in domains:
            domains.append(context.metadata.category)

        keywords = self._to_list(parameters.get("keywords") or parameters.get("tags"))
        if task_text:
            keywords.extend(
                [
                    word.strip(",.").lower()
                    for word in task_text.split()
                    if len(word) > 3
                ]
            )

        files = self._extract_files_from_parameters(parameters)

        return {
            "task": task_text,
            "languages": languages,
            "domains": domains,
            "keywords": self._deduplicate(keywords),
            "files": files,
            "mode": context.behavior_mode,
        }

    def _extract_files_from_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Extract file or path hints from command parameters."""
        files: List[str] = []
        keys = [
            "file",
            "files",
            "path",
            "paths",
            "target",
            "targets",
            "module",
            "modules",
        ]
        for key in keys:
            if key in parameters:
                files.extend(self._to_list(parameters[key]))
        return self._deduplicate([f for f in files if f])

    def _extract_delegate_targets(self, parsed: ParsedCommand) -> List[str]:
        """Extract explicit delegate targets provided by the user."""
        values: List[str] = []
        keys = [
            "delegate",
            "delegate_to",
            "delegate-to",
            "delegate_agent",
            "delegate-agent",
            "agents",
        ]
        for key in keys:
            if key in parsed.parameters:
                raw = parsed.parameters[key]
                if isinstance(raw, list):
                    values.extend(str(item) for item in raw)
                elif raw is not None:
                    values.extend(str(part).strip() for part in str(raw).split(","))
        return [value for value in (v.strip() for v in values) if value]

    def _flag_present(self, parsed: ParsedCommand, name: str) -> bool:
        """Check whether a flag or parameter is present and truthy."""
        if name in parsed.flags:
            return bool(parsed.flags[name])
        alias = name.replace("-", "_")
        if alias in parsed.flags:
            return bool(parsed.flags[alias])

        for lookup in (name, alias):
            if lookup in parsed.parameters:
                value = parsed.parameters[lookup]
                if isinstance(value, bool):
                    return value
                if isinstance(value, (int, float)):
                    return bool(value)
                if isinstance(value, str) and value.lower() in {
                    "true",
                    "yes",
                    "1",
                    "force",
                    "auto",
                }:
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
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip()]
        return [text]

    def _is_extended_agent(self, agent_id: str) -> bool:
        """Determine if an agent belongs to the extended catalogue."""
        metadata = getattr(self.extended_agent_loader, "_agent_metadata", {}).get(
            agent_id
        )
        if not metadata:
            return False
        return metadata.category != AgentCategory.CORE_DEVELOPMENT

    def _run_agent_pipeline(self, context: CommandContext) -> Dict[str, List[str]]:
        """Execute loaded agents and aggregate their outputs."""
        if not context.agent_instances:
            return {"operations": [], "notes": [], "warnings": []}

        task_description = " ".join(context.command.arguments).strip()
        if not task_description:
            task_description = context.command.raw_string

        aggregated_operations: List[str] = []
        aggregated_notes: List[str] = []
        aggregated_warnings: List[str] = []

        agent_payload = {
            "task": task_description,
            "command": context.command.name,
            "flags": sorted(context.command.flags.keys()),
            "parameters": context.command.parameters,
            "mode": context.behavior_mode,
            "mode_context": context.results.get("mode", {}),
            "repo_root": str(self.repo_root or Path.cwd()),
        }

        retrieved_context = []
        if self.retriever and task_description:
            retrieved_context = [
                hit.__dict__
                for hit in self.retriever.retrieve(task_description, limit=5)
            ]
            if retrieved_context:
                agent_payload["retrieved_context"] = retrieved_context
                context.results["retrieved_context"] = retrieved_context
                if self.monitor:
                    try:
                        self.monitor and self.monitor.record_event(
                            "hallucination.retrieval",
                            {
                                "timestamp": datetime.now().isoformat(),
                                "command": context.command.name,
                                "query": task_description[:120],
                                "hit_count": len(retrieved_context),
                            },
                        )
                    except Exception:
                        logger.debug(
                            "Failed to record retrieval telemetry", exc_info=True
                        )

        for agent_name, agent in list(context.agent_instances.items()):
            try:
                result = agent.execute(agent_payload)
            except Exception as exc:
                if context.fast_codex_active and agent_name == "codex-implementer":
                    raise RuntimeError(
                        "Codex CLI invocation failed in fast-codex mode. "
                        "Install or repair the codex CLI to continue."
                    ) from exc
                warning = f"{agent_name}: execution error — {exc}"
                logger.error(warning)
                context.errors.append(warning)
                aggregated_warnings.append(warning)
                continue

            context.agent_outputs[agent_name] = result
            agent_usage_tracker.record_execution(agent_name)

            status = self._ingest_agent_result(
                context,
                agent_name,
                result,
                aggregated_operations,
                aggregated_notes,
                aggregated_warnings,
            )

            if status == "plan-only":
                self._record_agent_plan_only([agent_name])
                self._maybe_escalate_with_strategist(
                    context,
                    agent_payload,
                    aggregated_operations,
                    aggregated_notes,
                    aggregated_warnings,
                )

        dedup_ops = self._deduplicate(aggregated_operations)
        dedup_notes = self._deduplicate(aggregated_notes)
        dedup_warnings = self._deduplicate(aggregated_warnings)

        context.results.setdefault("agent_operations", []).extend(dedup_ops)
        context.results.setdefault("agent_notes", []).extend(dedup_notes)
        if dedup_warnings:
            context.results.setdefault("agent_warnings", []).extend(dedup_warnings)

        return {
            "operations": dedup_ops,
            "notes": dedup_notes,
            "warnings": dedup_warnings,
        }

    def _ingest_agent_result(
        self,
        context: CommandContext,
        agent_name: str,
        result: Dict[str, Any],
        operations: List[str],
        notes: List[str],
        warnings: List[str],
    ) -> str:
        """Normalize an agent's raw result into aggregated collections."""
        actions = self._normalize_evidence_value(result.get("actions_taken"))
        plans = self._normalize_evidence_value(result.get("planned_actions"))
        warning_entries = self._normalize_evidence_value(result.get("warnings"))

        operations.extend(actions)
        operations.extend(plans)
        warnings.extend(warning_entries)

        output_text = str(result.get("output") or "").strip()
        note = output_text or "; ".join(plans) or "Provided guidance only."
        notes.append(f"{agent_name}: {note}")

        status = str(result.get("status") or "").lower()
        if status == "plan-only":
            plan_only_agents = context.results.setdefault("plan_only_agents", [])
            if agent_name not in plan_only_agents:
                plan_only_agents.append(agent_name)

        return status

    def _record_agent_plan_only(self, agents: Iterable[str]) -> None:
        """Persist plan-only telemetry for each agent."""
        registry = getattr(self.agent_loader, "registry", None)
        for agent in agents:
            source = None
            if registry:
                try:
                    cfg = registry.get_agent_config(agent) or {}
                    source = "core" if cfg.get("is_core") else "extended"
                except Exception:
                    source = None
            try:
                agent_usage_tracker.record_plan_only(agent, source=source)
            except Exception:
                continue

    def _maybe_escalate_with_strategist(
        self,
        context: CommandContext,
        payload: Dict[str, Any],
        operations: List[str],
        notes: List[str],
        warnings: List[str],
    ) -> None:
        """Attempt to load and execute a strategist-tier fallback agent."""
        if context.results.get("escalation_performed"):
            return

        context.consensus_forced = True

        registry = getattr(self.agent_loader, "registry", None)
        if not registry:
            return

        active_agents = set(context.agent_instances.keys())
        candidate = self._select_strategist_candidate(
            payload.get("task", ""), registry, active_agents
        )
        if not candidate:
            return

        try:
            strategist = self.agent_loader.load_agent(candidate)
        except Exception as exc:
            warning = f"{candidate}: escalation load failed — {exc}"
            warnings.append(warning)
            context.errors.append(warning)
            return

        if not strategist:
            warning = f"{candidate}: escalation load returned no agent instance"
            warnings.append(warning)
            context.errors.append(warning)
            return

        context.results["escalation_performed"] = True
        context.results.setdefault("escalations", []).append(
            {
                "trigger": "plan-only",
                "agent": candidate,
            }
        )

        if candidate not in context.agent_instances:
            context.agent_instances[candidate] = strategist
        if candidate not in context.agents:
            context.agents.append(candidate)

        retry_payload = dict(payload)
        retry_payload["retry_count"] = (
            int(context.results.get("escalation_attempts", 0)) + 1
        )
        context.results["escalation_attempts"] = retry_payload["retry_count"]

        try:
            result = strategist.execute(retry_payload)
        except Exception as exc:
            warning = f"{candidate}: escalation execution error — {exc}"
            warnings.append(warning)
            context.errors.append(warning)
            return

        context.agent_outputs[candidate] = result
        agent_usage_tracker.record_execution(candidate)

        status = self._ingest_agent_result(
            context, candidate, result, operations, notes, warnings
        )

        if status == "plan-only":
            self._record_agent_plan_only([candidate])
        else:
            context.results.setdefault("escalation_success", True)

    def _select_strategist_candidate(
        self, task: str, registry: AgentRegistry, exclude: Iterable[str]
    ) -> Optional[str]:
        """
        Choose a strategist-tier agent for escalation based on the task context.
        """
        lowered = (task or "").lower()
        exclude_set = set(exclude)

        fallback_order: List[str] = []
        frontend_signals = ["frontend", "ui", "react", "component", "next.js", "nextjs"]
        backend_signals = [
            "backend",
            "api",
            "service",
            "endpoint",
            "database",
            "schema",
        ]

        if any(sig in lowered for sig in frontend_signals) and any(
            sig in lowered for sig in backend_signals
        ):
            fallback_order.append("fullstack-developer")

        fallback_order.extend(
            [
                "system-architect",
                "backend-architect",
                "frontend-architect",
                "quality-engineer",
            ]
        )

        for candidate in fallback_order:
            if candidate in exclude_set:
                continue
            cfg = registry.get_agent_config(candidate)
            if not cfg:
                continue
            if registry.get_capability_tier(candidate) == "strategist":
                return candidate

        for name in registry.get_all_agents():
            if name in exclude_set:
                continue
            if registry.get_capability_tier(name) == "strategist":
                return name

        return None

    def _record_test_artifact(
        self,
        context: CommandContext,
        parsed: ParsedCommand,
        test_results: Dict[str, Any],
    ) -> Optional[str]:
        """Persist a test outcome artifact and return its relative path."""
        if not test_results:
            return None

        status = "pass" if test_results.get("passed") else "fail"
        summary = [
            f"Test command: {test_results.get('command', 'pytest')}",
            f"Status: {status.upper()}",
        ]
        duration = test_results.get("duration_s")
        if isinstance(duration, (int, float)):
            summary.append(f"Duration: {duration:.2f}s")
        stdout = test_results.get("stdout")
        if stdout:
            summary.append("\n## Stdout\n" + stdout)
        stderr = test_results.get("stderr")
        if stderr:
            summary.append("\n## Stderr\n" + stderr)

        metadata = {
            "command": parsed.name,
            "status": status,
            "exit_code": test_results.get("exit_code"),
            "pass_rate": test_results.get("pass_rate"),
        }

        operations = [self._summarize_test_results(test_results)]
        return self._record_artifact(
            context,
            f"{parsed.name}-tests",
            "\n\n".join(summary).strip(),
            operations=operations,
            metadata=metadata,
        )

    def _record_quality_artifact(
        self, context: CommandContext, assessment: QualityAssessment
    ) -> Optional[str]:
        """Persist a quality assessment artifact summarising scores."""
        metrics_lines = [
            f"Overall: {assessment.overall_score:.1f} (threshold {assessment.threshold:.1f})",
            f"Passed: {'yes' if assessment.passed else 'no'}",
            "",
            "## Dimensions",
        ]
        for metric in assessment.metrics:
            metrics_lines.append(
                f"- {metric.dimension.value}: {metric.score:.1f} — issues: {len(metric.issues)}"
            )

        if assessment.improvements_needed:
            metrics_lines.append("")
            metrics_lines.append("## Improvements Needed")
            metrics_lines.extend(f"- {item}" for item in assessment.improvements_needed)

        metadata = {
            "threshold": assessment.threshold,
            "passed": assessment.passed,
            "iteration": assessment.iteration,
        }

        operations = [
            f"quality_overall {assessment.overall_score:.1f}/{assessment.threshold:.1f}",
        ]

        return self._record_artifact(
            context,
            "quality-assessment",
            "\n".join(metrics_lines).strip(),
            operations=operations,
            metadata=metadata,
        )

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
            command_name, summary, operations=operations, metadata=metadata or {}
        )

        if not record:
            return None

        rel_path = self._relative_to_repo_path(record.path)
        context.results.setdefault("artifacts", []).append(rel_path)
        context.results.setdefault("executed_operations", []).append(
            f"artifact created: {rel_path}"
        )
        context.artifact_records.append(
            {
                "path": rel_path,
                "metadata": record.metadata,
            }
        )
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
            summary = str(output.get("summary") or output.get("output") or "")
        if not summary:
            summary = str(context.results.get("primary_summary") or "")
        if not summary:
            summary = context.command.raw_string
        lines.append("Summary:")
        lines.append(summary.strip())

        agent_notes = context.results.get("agent_notes") or []
        if agent_notes:
            lines.append("Agent Findings:")
            lines.extend(f"- {note}" for note in agent_notes)

        operations = context.results.get("agent_operations") or []
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
        task_type: str = "consensus",
    ) -> Dict[str, Any]:
        """Run consensus builder and attach the result to the context."""
        prompt = self._build_consensus_prompt(context, output)
        policy = self._resolve_consensus_policy(
            context.command.name if context.command else None
        )
        vote_type = policy.get("vote_type", VoteType.MAJORITY)
        quorum_size = max(2, int(policy.get("quorum_size", 2)))
        try:
            result = await self.consensus_facade.run_consensus(
                prompt,
                vote_type=vote_type,
                quorum_size=quorum_size,
                context=context.results,
                think_level=think_level,
                task_type=task_type,
            )
        except Exception as exc:
            message = f"Consensus evaluation failed: {exc}"
            logger.error(message)
            context.errors.append(message)
            result = {"consensus_reached": False, "error": str(exc)}

        context.consensus_summary = result
        context.results["consensus"] = result
        context.results["consensus_vote_type"] = (
            vote_type.value if isinstance(vote_type, VoteType) else str(vote_type)
        )
        context.results["consensus_quorum_size"] = quorum_size
        if result.get("routing_decision"):
            context.results["routing_decision"] = result["routing_decision"]
        if result.get("models"):
            context.results["consensus_models"] = result["models"]
        if result.get("think_level") is not None:
            context.results["consensus_think_level"] = result["think_level"]
        if "offline" in result:
            context.results["consensus_offline"] = bool(result["offline"])

        if enforce and not result.get("consensus_reached", False):
            message = "Consensus not reached; additional review required."
            if result.get("error"):
                message = f"Consensus failed: {result['error']}"
            context.errors.append(message)
            context.results["consensus_failed"] = True
            if result.get("error"):
                context.results["consensus_error"] = result["error"]
            if isinstance(output, dict):
                warnings_list = self._ensure_list(output, "warnings")
                if message not in warnings_list:
                    warnings_list.append(message)

        return result

    def _load_consensus_policies(self) -> Dict[str, Any]:
        """Load consensus policies from configuration."""
        base_dir = Path(__file__).resolve().parent.parent
        cfg_path = base_dir / "Config" / "consensus_policies.yaml"
        if yaml is None or not cfg_path.exists():
            if yaml is None:
                logger.warning("PyYAML missing; using default consensus policies")
            return {
                "defaults": {"vote_type": VoteType.MAJORITY, "quorum_size": 2},
                "commands": {},
            }

        try:
            with cfg_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:
            logger.warning(
                "Failed to load consensus policy config %s: %s", cfg_path, exc
            )
            data = {}

        defaults = data.get("defaults") or {}
        commands = data.get("commands") or {}

        def _normalize_vote(value):
            if isinstance(value, VoteType):
                return value
            try:
                return VoteType[str(value).upper()]
            except Exception:
                return VoteType.MAJORITY

        defaults_normalized = {
            "vote_type": _normalize_vote(defaults.get("vote_type", VoteType.MAJORITY)),
            "quorum_size": int(defaults.get("quorum_size", 2) or 2),
        }

        command_maps: Dict[str, Dict[str, Any]] = {}
        for name, cfg in commands.items():
            if not isinstance(cfg, dict):
                continue
            vote_raw = cfg.get("vote_type", defaults_normalized["vote_type"])
            quorum_raw = cfg.get("quorum_size", defaults_normalized["quorum_size"])
            command_maps[name] = {
                "vote_type": _normalize_vote(vote_raw),
                "quorum_size": int(quorum_raw or defaults_normalized["quorum_size"]),
            }

        return {
            "defaults": defaults_normalized,
            "commands": command_maps,
        }

    def _resolve_consensus_policy(self, command_name: Optional[str]) -> Dict[str, Any]:
        """Resolve consensus policy for a command name."""
        defaults = self.consensus_policies.get("defaults", {})
        commands = self.consensus_policies.get("commands", {})
        if command_name and command_name in commands:
            policy = dict(defaults)
            policy.update(commands[command_name])
            return policy
        return dict(defaults)

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
        import hashlib
        from datetime import datetime

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
        results: List[CommandResult] = []
        skip_next_test = False

        for command_str in commands:
            command_name: Optional[str] = None
            try:
                command_name = self.parser.parse(command_str).name
            except Exception:
                command_name = None

            if skip_next_test and command_name == "test":
                skip_next_test = False
                continue

            result = await self.execute(command_str)
            results.append(result)

            if not result.success:
                logger.warning(f"Command chain stopped due to failure: {command_str}")
                skip_next_test = False
                break

            test_results = None
            if isinstance(result.output, dict):
                test_results = result.output.get("test_results")
            if isinstance(test_results, dict) and test_results.get("passed"):
                skip_next_test = True
            else:
                skip_next_test = False

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
                final_results.append(
                    CommandResult(
                        success=False,
                        command_name="unknown",
                        output=None,
                        errors=[str(result)],
                    )
                )
            else:
                final_results.append(result)

        return final_results


class _PythonSemanticAnalyzer(ast.NodeVisitor):
    """Very lightweight semantic analyzer for Python files."""

    _BUILTINS = set(dir(builtins)) | {
        "self",
        "cls",
        "__name__",
        "__file__",
        "__package__",
        "__doc__",
        "__all__",
        "__annotations__",
    }

    def __init__(self, file_path: Path, repo_root: Optional[Path]):
        self.file_path = Path(file_path)
        self.repo_root = Path(repo_root) if repo_root else self.file_path.parent
        self.scopes: List[Set[str]] = [set(self._BUILTINS)]
        self.missing_imports: List[str] = []
        self.unresolved_names: Set[str] = set()
        self.imported_symbols: Set[str] = set()
        self.module_name = self._derive_module_name()

    def _derive_module_name(self) -> Optional[str]:
        try:
            relative = self.file_path.relative_to(self.repo_root)
        except ValueError:
            return None
        parts = list(relative.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else None

    # Scope helpers --------------------------------------------------

    def _push_scope(self) -> None:
        self.scopes.append(set())

    def _pop_scope(self) -> None:
        if len(self.scopes) > 1:
            self.scopes.pop()

    def _define(self, name: str) -> None:
        if name:
            self.scopes[-1].add(name)

    def _is_defined(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self.scopes))

    # Visitors -------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._define(node.name)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._push_scope()
        self._define_arguments(node.args)
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._define(node.name)
        for base in node.bases:
            self.visit(base)
        self._push_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            defined = alias.asname or alias.name.split(".")[0]
            self._define(defined)
            self.imported_symbols.add(defined)
            self._validate_import(alias.name, level=0)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue
            defined = alias.asname or alias.name
            self._define(defined)
            self.imported_symbols.add(defined)
        self._validate_import(module, level=node.level or 0)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._define_target(target)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.target:
            self._define_target(node.target)
        if node.annotation:
            self.visit(node.annotation)
        if node.value:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.target)
        self.visit(node.value)

    def visit_For(self, node: ast.For) -> None:
        self.visit(node.iter)
        self._define_target(node.target)
        self._push_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.visit_For(node)  # type: ignore[arg-type]

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._define_target(item.optional_vars)
        self._push_scope()
        for stmt in node.body:
            self.visit(stmt)
        self._pop_scope()

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.visit_With(node)  # type: ignore[arg-type]

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if not self._is_defined(node.id) and node.id not in self.imported_symbols:
                self.unresolved_names.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Param)):
            self._define(node.id)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, node.elt)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.generators, node.elt)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node.generators, node.elt)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, node.key, node.value)

    def _visit_comprehension(
        self, generators: List[ast.comprehension], *exprs: ast.AST
    ) -> None:
        self._push_scope()
        for comp in generators:
            self.visit(comp.iter)
            self._define_target(comp.target)
            for if_clause in comp.ifs:
                self.visit(if_clause)
        for expr in exprs:
            self.visit(expr)
        self._pop_scope()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.visit(node.value)

    # Helper operations -----------------------------------------------

    def _define_arguments(self, args: ast.arguments) -> None:
        for arg in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
            self._define(arg.arg)
        if args.vararg:
            self._define(args.vararg.arg)
        if args.kwarg:
            self._define(args.kwarg.arg)

    def _define_target(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self._define(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._define_target(elt)
        elif isinstance(target, ast.Attribute):
            self.visit(target.value)
        elif isinstance(target, ast.Subscript):
            self.visit(target.value)
            self.visit(target.slice)

    def _validate_import(self, module: str, level: int) -> None:
        module = module or ""
        candidate = self._resolve_module_name(module, level)
        if not candidate:
            return

        if self._module_exists(candidate):
            return

        try:
            spec = importlib.util.find_spec(candidate)
        except Exception:
            spec = None

        if spec is None:
            self.missing_imports.append(f"missing import '{candidate}'")

    def _resolve_module_name(self, module: str, level: int) -> Optional[str]:
        if level == 0:
            return module

        if not self.module_name:
            return module

        parts = self.module_name.split(".")
        if level > len(parts):
            return module

        base = parts[:-level]
        if module:
            base.append(module)
        return ".".join(base) if base else module

    def _module_exists(self, module_name: str) -> bool:
        parts = module_name.split(".")
        candidate_dir = self.repo_root.joinpath(*parts)
        if candidate_dir.with_suffix(".py").exists():
            return True
        if candidate_dir.exists() and (candidate_dir / "__init__.py").exists():
            return True
        return False

    def report(self) -> List[str]:
        issues: List[str] = []
        issues.extend(self.missing_imports)
        unresolved = sorted(
            self.unresolved_names - self._BUILTINS - set(self.imported_symbols)
        )
        for name in unresolved:
            issues.append(f"unresolved symbol '{name}'")
        return issues
