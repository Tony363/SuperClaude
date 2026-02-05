"""
Obsidian SDK Hooks for SuperClaude Orchestrator

Creates hooks that sync decision artifacts to Obsidian vault on Stop events.
"""

from pathlib import Path
from typing import Any, Awaitable, Callable

from .evidence import EvidenceCollector

# Type alias for SDK hook callbacks
HookCallback = Callable[
    [dict[str, Any], str | None, dict[str, Any]],
    Awaitable[dict[str, Any]],
]


def create_obsidian_hooks(
    project_root: Path,
    evidence: EvidenceCollector,
    project_name: str | None = None,
) -> dict[str, list[dict]]:
    """
    Create Obsidian integration hooks for the SDK.

    These hooks sync decision artifacts to the Obsidian vault when
    the agent session stops.

    Args:
        project_root: Root path of the project for config lookup.
        evidence: EvidenceCollector instance to extract decisions from.
        project_name: Optional project name override.

    Returns:
        Hook configuration dict for ClaudeAgentOptions.
    """

    async def sync_decisions_on_stop(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Stop hook: Extract and sync decisions to Obsidian vault.

        Parses tool invocations from evidence collector, extracts
        decisions from PAL consensus/thinkdeep calls, and writes
        them to the configured vault location.
        """
        if input_data.get("hook_event_name") != "Stop":
            return {}

        # Import here to avoid circular imports
        from setup.services.obsidian_artifact import (
            ObsidianArtifactWriter,
            extract_decisions_from_evidence,
        )
        from setup.services.obsidian_config import ObsidianConfigService

        # Check if Obsidian is configured
        config_service = ObsidianConfigService(project_root)
        if not config_service.config_exists():
            return {}

        config = config_service.load_config()
        if not config:
            return {}

        # Check if sync is enabled
        if config.artifacts.sync_on == "never":
            return {}

        # Get project name
        name = project_name or project_root.name

        # Get session ID from input or evidence
        session_id = input_data.get("session_id", "") or evidence.session_id

        # Extract decisions from evidence
        decisions = extract_decisions_from_evidence(
            tool_invocations=evidence.tool_invocations,
            project_name=name,
            session_id=session_id,
        )

        if not decisions:
            return {"obsidian_artifacts_written": []}

        # Write decisions to vault
        writer = ObsidianArtifactWriter(config=config)
        written_paths = []

        for decision in decisions:
            path = writer.write_decision(decision)
            if path:
                written_paths.append(str(path))

        return {
            "obsidian_artifacts_written": written_paths,
            "obsidian_decisions_count": len(written_paths),
        }

    return {
        "Stop": [{"hooks": [sync_decisions_on_stop]}],
    }


def merge_obsidian_hooks(
    existing_hooks: dict[str, list[dict]],
    obsidian_hooks: dict[str, list[dict]],
) -> dict[str, list[dict]]:
    """
    Merge Obsidian hooks with existing SDK hooks.

    Args:
        existing_hooks: Existing hook configuration.
        obsidian_hooks: Obsidian hook configuration.

    Returns:
        Merged hook configuration.
    """
    merged = {**existing_hooks}

    for event_name, matchers in obsidian_hooks.items():
        if event_name not in merged:
            merged[event_name] = []
        merged[event_name].extend(matchers)

    return merged
