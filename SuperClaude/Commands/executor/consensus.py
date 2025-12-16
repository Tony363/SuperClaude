"""
Consensus utilities for the SuperClaude Command Executor.

Provides helper functions for building consensus prompts, loading
and resolving policies, and formatting consensus results.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Vote type for consensus decisions."""

    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    QUORUM = "quorum"


def build_consensus_prompt(
    command_name: str,
    behavior_mode: str,
    flags: Dict[str, Any],
    arguments: List[str],
    output: Any,
    results: Optional[Dict[str, Any]] = None,
) -> str:
    """Construct a deterministic prompt for consensus evaluation.

    Args:
        command_name: Name of the command being executed.
        behavior_mode: Current behavioral mode.
        flags: Command flags dictionary.
        arguments: Command arguments list.
        output: Command output to include in prompt.
        results: Optional results dictionary for additional context.

    Returns:
        Formatted consensus prompt string.
    """
    results = results or {}

    lines = [
        f"Command: /sc:{command_name}",
        f"Mode: {behavior_mode}",
        f"Flags: {' '.join(sorted(flags.keys())) or 'none'}",
        f"Arguments: {' '.join(arguments) or 'none'}",
    ]

    summary = ""
    if isinstance(output, dict):
        summary = str(output.get("summary") or output.get("output") or "")
    if not summary:
        summary = str(results.get("primary_summary") or "")
    if not summary and arguments:
        summary = " ".join(arguments)

    lines.append("Summary:")
    lines.append(summary.strip())

    agent_notes = results.get("agent_notes") or []
    if agent_notes:
        lines.append("Agent Findings:")
        lines.extend(f"- {note}" for note in agent_notes)

    operations = results.get("agent_operations") or []
    if operations:
        lines.append("Operations:")
        lines.extend(f"- {op}" for op in operations)

    return "\n".join(lines)


def normalize_vote_type(value: Any) -> VoteType:
    """Normalize a vote type value to a VoteType enum.

    Args:
        value: Vote type value (VoteType, string, or other).

    Returns:
        Normalized VoteType enum value.
    """
    if isinstance(value, VoteType):
        return value
    try:
        return VoteType[str(value).upper()]
    except (KeyError, ValueError):
        return VoteType.MAJORITY


def load_consensus_policies(
    config_path: Optional[Path] = None,
    yaml_module: Any = None,
) -> Dict[str, Any]:
    """Load consensus policies from configuration.

    Args:
        config_path: Path to the consensus policies YAML file.
        yaml_module: Optional yaml module for loading.

    Returns:
        Dictionary with 'defaults' and 'commands' keys.
    """
    default_policies = {
        "defaults": {"vote_type": VoteType.MAJORITY, "quorum_size": 2},
        "commands": {},
    }

    if yaml_module is None:
        logger.debug("PyYAML not available; using default consensus policies")
        return default_policies

    if config_path is None or not config_path.exists():
        return default_policies

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml_module.safe_load(handle) or {}
    except Exception as exc:
        logger.warning(
            "Failed to load consensus policy config %s: %s", config_path, exc
        )
        return default_policies

    defaults = data.get("defaults") or {}
    commands = data.get("commands") or {}

    defaults_normalized = {
        "vote_type": normalize_vote_type(defaults.get("vote_type", VoteType.MAJORITY)),
        "quorum_size": int(defaults.get("quorum_size", 2) or 2),
    }

    command_maps: Dict[str, Dict[str, Any]] = {}
    for name, cfg in commands.items():
        if not isinstance(cfg, dict):
            continue
        vote_raw = cfg.get("vote_type", defaults_normalized["vote_type"])
        quorum_raw = cfg.get("quorum_size", defaults_normalized["quorum_size"])
        command_maps[name] = {
            "vote_type": normalize_vote_type(vote_raw),
            "quorum_size": int(quorum_raw or defaults_normalized["quorum_size"]),
        }

    return {
        "defaults": defaults_normalized,
        "commands": command_maps,
    }


def resolve_consensus_policy(
    command_name: Optional[str],
    policies: Dict[str, Any],
) -> Dict[str, Any]:
    """Resolve consensus policy for a command name.

    Args:
        command_name: Name of the command (may be None).
        policies: Loaded consensus policies dictionary.

    Returns:
        Resolved policy dictionary.
    """
    defaults = policies.get("defaults", {})
    commands = policies.get("commands", {})

    if command_name and command_name in commands:
        policy = dict(defaults)
        policy.update(commands[command_name])
        return policy

    return dict(defaults)


def format_consensus_result(
    result: Dict[str, Any],
    vote_type: VoteType,
    quorum_size: int,
) -> Dict[str, Any]:
    """Format a consensus result with metadata.

    Args:
        result: Raw consensus result.
        vote_type: Vote type used.
        quorum_size: Quorum size used.

    Returns:
        Formatted result dictionary.
    """
    formatted = dict(result)
    formatted["vote_type"] = (
        vote_type.value if isinstance(vote_type, VoteType) else str(vote_type)
    )
    formatted["quorum_size"] = quorum_size
    return formatted


def extract_consensus_metadata(
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """Extract key metadata from a consensus result.

    Args:
        result: Consensus result dictionary.

    Returns:
        Dictionary with extracted metadata.
    """
    metadata = {
        "consensus_reached": bool(result.get("consensus_reached", False)),
    }

    if result.get("routing_decision"):
        metadata["routing_decision"] = result["routing_decision"]
    if result.get("models"):
        metadata["models"] = result["models"]
    if result.get("think_level") is not None:
        metadata["think_level"] = result["think_level"]
    if "offline" in result:
        metadata["offline"] = bool(result["offline"])
    if result.get("error"):
        metadata["error"] = result["error"]

    return metadata


def consensus_failed_message(
    result: Dict[str, Any],
    default_message: str = "Consensus not reached; additional review required.",
) -> str:
    """Generate failure message from consensus result.

    Args:
        result: Consensus result dictionary.
        default_message: Default message if no specific error.

    Returns:
        Failure message string.
    """
    error = result.get("error")
    if error:
        return f"Consensus failed: {error}"
    return default_message


__all__ = [
    "VoteType",
    "build_consensus_prompt",
    "consensus_failed_message",
    "extract_consensus_metadata",
    "format_consensus_result",
    "load_consensus_policies",
    "normalize_vote_type",
    "resolve_consensus_policy",
]
