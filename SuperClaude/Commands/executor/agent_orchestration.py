"""
Agent orchestration utilities for the SuperClaude Command Executor.

Provides helper functions for persona mapping, delegate target extraction,
agent payload building, and result ingestion without instance dependencies.
"""

import logging
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# Default persona to agent mapping
PERSONA_TO_AGENT: Dict[str, str] = {
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
}


# Task domain signals for strategist selection
FRONTEND_SIGNALS = frozenset(
    [
        "frontend",
        "ui",
        "react",
        "component",
        "next.js",
        "nextjs",
        "vue",
        "angular",
        "css",
        "html",
        "browser",
        "dom",
        "client-side",
    ]
)

BACKEND_SIGNALS = frozenset(
    [
        "backend",
        "api",
        "service",
        "endpoint",
        "database",
        "schema",
        "server",
        "rest",
        "graphql",
        "orm",
        "sql",
        "nosql",
    ]
)

STRATEGIST_FALLBACK_ORDER = [
    "system-architect",
    "backend-architect",
    "frontend-architect",
    "quality-engineer",
]


def map_persona_to_agent(
    persona: str,
    custom_mapping: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """Map a persona name to its corresponding agent name.

    Args:
        persona: Persona name from command.
        custom_mapping: Optional custom mapping to use instead of defaults.

    Returns:
        Agent name or None if no mapping exists.
    """
    mapping = custom_mapping if custom_mapping is not None else PERSONA_TO_AGENT
    return mapping.get(persona)


def detect_task_domain(task: str) -> Tuple[bool, bool]:
    """Detect if a task involves frontend and/or backend domains.

    Args:
        task: Task description text.

    Returns:
        Tuple of (has_frontend_signals, has_backend_signals).
    """
    lowered = (task or "").lower()
    has_frontend = any(sig in lowered for sig in FRONTEND_SIGNALS)
    has_backend = any(sig in lowered for sig in BACKEND_SIGNALS)
    return has_frontend, has_backend


def select_strategist_candidate(
    task: str,
    available_agents: Iterable[str],
    capability_tiers: Dict[str, str],
    exclude: Optional[Iterable[str]] = None,
) -> Optional[str]:
    """Choose a strategist-tier agent for escalation based on task context.

    Args:
        task: Task description for context-aware selection.
        available_agents: All available agent names.
        capability_tiers: Mapping of agent name to capability tier.
        exclude: Agent names to exclude from selection.

    Returns:
        Selected strategist agent name or None.
    """
    exclude_set = set(exclude or [])
    has_frontend, has_backend = detect_task_domain(task)

    fallback_order: List[str] = []

    # Prefer fullstack for mixed frontend/backend tasks
    if has_frontend and has_backend:
        fallback_order.append("fullstack-developer")

    fallback_order.extend(STRATEGIST_FALLBACK_ORDER)

    # Try preferred order first
    for candidate in fallback_order:
        if candidate in exclude_set:
            continue
        if capability_tiers.get(candidate) == "strategist":
            return candidate

    # Fall back to any strategist
    for name in available_agents:
        if name in exclude_set:
            continue
        if capability_tiers.get(name) == "strategist":
            return name

    return None


def extract_delegate_targets(
    parameters: Dict[str, Any],
    flags: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Extract explicit delegate targets provided by the user.

    Args:
        parameters: Command parameters dictionary.
        flags: Optional command flags dictionary.

    Returns:
        List of delegate target agent names.
    """
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
        if key in parameters:
            raw = parameters[key]
            if isinstance(raw, list):
                values.extend(str(item) for item in raw if item)
            elif raw is not None:
                values.extend(str(part).strip() for part in str(raw).split(","))

    # Deduplicate while preserving order
    seen: Set[str] = set()
    result: List[str] = []
    for v in values:
        normalized = v.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


def extract_files_from_parameters(parameters: Dict[str, Any]) -> List[str]:
    """Extract file or path hints from command parameters.

    Args:
        parameters: Command parameters dictionary.

    Returns:
        Deduplicated list of file paths.
    """
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
            raw = parameters[key]
            if isinstance(raw, list):
                files.extend(str(item).strip() for item in raw if item)
            elif raw is not None:
                files.append(str(raw).strip())

    # Deduplicate
    seen: Set[str] = set()
    result: List[str] = []
    for f in files:
        if f and f not in seen:
            seen.add(f)
            result.append(f)

    return result


def build_agent_payload(
    task_description: str,
    command_name: str,
    flags: Dict[str, Any],
    parameters: Dict[str, Any],
    behavior_mode: str,
    mode_context: Optional[Dict[str, Any]] = None,
    repo_root: Optional[str] = None,
    retrieved_context: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a payload dictionary for agent execution.

    Args:
        task_description: The task description text.
        command_name: Name of the command being executed.
        flags: Command flags.
        parameters: Command parameters.
        behavior_mode: Current behavioral mode.
        mode_context: Optional mode-specific context.
        repo_root: Optional repository root path.
        retrieved_context: Optional retrieval results.

    Returns:
        Agent payload dictionary.
    """
    payload: Dict[str, Any] = {
        "task": task_description,
        "command": command_name,
        "flags": sorted(flags.keys()),
        "parameters": parameters,
        "mode": behavior_mode,
        "mode_context": mode_context or {},
    }

    if repo_root:
        payload["repo_root"] = repo_root

    if retrieved_context:
        payload["retrieved_context"] = retrieved_context

    return payload


def build_delegation_context(
    task: str,
    parameters: Dict[str, Any],
    behavior_mode: str,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct context payload for delegate selection.

    Args:
        task: Task description text.
        parameters: Command parameters.
        behavior_mode: Current behavioral mode.
        category: Optional metadata category.

    Returns:
        Delegation context dictionary.
    """
    languages = _extract_list_param(parameters, ["language", "languages", "lang"])
    domains = _extract_list_param(parameters, ["domain", "domains"])

    if category and category not in domains:
        domains.append(category)

    keywords = _extract_list_param(parameters, ["keywords", "tags"])
    # Extract keywords from task
    if task:
        keywords.extend(
            [word.strip(",.").lower() for word in task.split() if len(word) > 3]
        )

    files = extract_files_from_parameters(parameters)

    return {
        "task": task,
        "languages": languages,
        "domains": domains,
        "keywords": _deduplicate_list(keywords),
        "files": files,
        "mode": behavior_mode,
    }


def ingest_agent_result(
    agent_name: str,
    result: Dict[str, Any],
) -> Tuple[List[str], List[str], List[str], str]:
    """Normalize an agent's raw result into aggregated collections.

    Args:
        agent_name: Name of the agent.
        result: Agent's raw result dictionary.

    Returns:
        Tuple of (operations, notes, warnings, status).
    """
    operations: List[str] = []
    notes: List[str] = []
    warnings: List[str] = []

    actions = _normalize_evidence_value(result.get("actions_taken"))
    plans = _normalize_evidence_value(result.get("planned_actions"))
    warning_entries = _normalize_evidence_value(result.get("warnings"))

    operations.extend(actions)
    operations.extend(plans)
    warnings.extend(warning_entries)

    output_text = str(result.get("output") or "").strip()
    note = output_text or "; ".join(plans) or "Provided guidance only."
    notes.append(f"{agent_name}: {note}")

    status = str(result.get("status") or "").lower()

    return operations, notes, warnings, status


def _extract_list_param(
    parameters: Dict[str, Any],
    keys: List[str],
) -> List[str]:
    """Extract list values from parameters for multiple possible keys."""
    result: List[str] = []
    for key in keys:
        if key in parameters:
            raw = parameters[key]
            if isinstance(raw, list):
                result.extend(str(item).strip() for item in raw if item)
            elif raw is not None:
                result.append(str(raw).strip())
    return result


def _deduplicate_list(items: List[str]) -> List[str]:
    """Deduplicate list while preserving order."""
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        normalized = item.strip().lower() if item else ""
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(item.strip())
    return result


def _normalize_evidence_value(value: Any) -> List[str]:
    """Normalize evidence values into a flat list of strings."""
    items: List[str] = []
    if value is None:
        return items

    if isinstance(value, list):
        for item in value:
            items.extend(_normalize_evidence_value(item))
        return items

    if isinstance(value, dict):
        for key, subvalue in value.items():
            sub_items = _normalize_evidence_value(subvalue)
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


__all__ = [
    "BACKEND_SIGNALS",
    "FRONTEND_SIGNALS",
    "PERSONA_TO_AGENT",
    "STRATEGIST_FALLBACK_ORDER",
    "build_agent_payload",
    "build_delegation_context",
    "detect_task_domain",
    "extract_delegate_targets",
    "extract_files_from_parameters",
    "ingest_agent_result",
    "map_persona_to_agent",
    "select_strategist_candidate",
]
