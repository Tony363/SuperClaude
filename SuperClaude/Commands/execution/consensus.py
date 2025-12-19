"""
Consensus service for SuperClaude Commands.

Handles consensus policies and enforcement.
Note: Actual consensus is now handled via PAL MCP meta-prompting.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None  # type: ignore

from .context import CommandContext

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Consensus voting types."""

    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    QUORUM = "quorum"
    WEIGHTED = "weighted"


class ConsensusService:
    """
    Service for handling consensus policies and enforcement.

    Note: Actual consensus is now handled via PAL MCP meta-prompting.
    This service manages policy configuration and stub responses.
    """

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize consensus service.

        Args:
            config_dir: Directory containing consensus_policies.yaml
        """
        self.config_dir = config_dir or Path(__file__).resolve().parent.parent.parent / "Config"
        self.policies = self._load_policies()

    def _load_policies(self) -> dict[str, Any]:
        """Load consensus policies from configuration."""
        cfg_path = self.config_dir / "consensus_policies.yaml"
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
            logger.warning("Failed to load consensus policy config %s: %s", cfg_path, exc)
            data = {}

        defaults = data.get("defaults") or {}
        commands = data.get("commands") or {}

        defaults_normalized = {
            "vote_type": self._normalize_vote(defaults.get("vote_type", VoteType.MAJORITY)),
            "quorum_size": int(defaults.get("quorum_size", 2) or 2),
        }

        command_maps: dict[str, dict[str, Any]] = {}
        for name, cfg in commands.items():
            if not isinstance(cfg, dict):
                continue
            vote_raw = cfg.get("vote_type", defaults_normalized["vote_type"])
            quorum_raw = cfg.get("quorum_size", defaults_normalized["quorum_size"])
            command_maps[name] = {
                "vote_type": self._normalize_vote(vote_raw),
                "quorum_size": int(quorum_raw or defaults_normalized["quorum_size"]),
            }

        return {
            "defaults": defaults_normalized,
            "commands": command_maps,
        }

    def _normalize_vote(self, value: Any) -> VoteType:
        """Normalize a vote type value to VoteType enum."""
        if isinstance(value, VoteType):
            return value
        try:
            return VoteType[str(value).upper()]
        except Exception:
            return VoteType.MAJORITY

    def resolve_policy(self, command_name: str | None) -> dict[str, Any]:
        """
        Resolve consensus policy for a command name.

        Args:
            command_name: Name of the command

        Returns:
            Policy dictionary with vote_type and quorum_size
        """
        defaults = self.policies.get("defaults", {})
        commands = self.policies.get("commands", {})
        if command_name and command_name in commands:
            policy = dict(defaults)
            policy.update(commands[command_name])
            return policy
        return dict(defaults)

    def build_prompt(self, context: CommandContext, output: Any) -> str:
        """
        Construct a deterministic prompt for consensus evaluation.

        Args:
            context: Command execution context
            output: Command output

        Returns:
            Formatted prompt string
        """
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

    async def ensure_consensus(
        self,
        context: CommandContext,
        output: Any,
        *,
        enforce: bool = False,
        think_level: int | None = None,
        task_type: str = "consensus",
    ) -> dict[str, Any]:
        """
        Consensus stub - ModelRouter removed.

        Consensus is now handled via PAL MCP meta-prompting. See CLAUDE.md for:
        - mcp__pal__consensus for multi-model consensus
        - mcp__pal__codereview for code review validation
        - mcp__pal__thinkdeep for complex analysis

        Args:
            context: Command execution context
            output: Command output
            enforce: Whether to enforce consensus requirement
            think_level: Thinking depth level
            task_type: Type of consensus task

        Returns:
            Consensus result dictionary
        """
        policy = self.resolve_policy(context.command.name if context.command else None)
        vote_type = policy.get("vote_type", VoteType.MAJORITY)
        quorum_size = max(2, int(policy.get("quorum_size", 2)))

        # Return no-op result - actual consensus via PAL MCP meta-prompting
        result = {
            "consensus_reached": True,
            "offline": True,
            "note": "Consensus via PAL MCP - see mcp__pal__consensus",
        }

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
                warnings_list = output.setdefault("warnings", [])
                if isinstance(warnings_list, list) and message not in warnings_list:
                    warnings_list.append(message)

        return result
