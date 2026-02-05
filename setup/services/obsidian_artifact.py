"""
Obsidian Artifact Writer for SuperClaude

Writes decision artifacts to Obsidian vault with YAML frontmatter.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..utils.logger import get_logger
from .obsidian_config import ObsidianConfig, ObsidianConfigService


@dataclass
class DecisionRecord:
    """Represents a decision to be written to Obsidian."""

    title: str
    summary: str
    decision_type: str  # "architecture", "consensus", "technical"
    context: str
    rationale: str
    source_notes: list[str] = field(default_factory=list)
    session_id: str = ""
    project: str = ""
    created: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_slug(self) -> str:
        """Generate URL-safe slug from title."""
        slug = self.title.lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug[:50].strip("-")

    def to_filename(self) -> str:
        """Generate filename with date prefix and hash suffix."""
        date_str = self.created.strftime("%Y-%m-%d")
        slug = self.to_slug()
        # Add short hash for uniqueness
        hash_input = f"{self.title}{self.created.isoformat()}"
        short_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:6]
        return f"{date_str}-{slug}-{short_hash}.md"


class ObsidianArtifactWriter:
    """Writes decision artifacts to Obsidian vault."""

    def __init__(
        self,
        config: ObsidianConfig | None = None,
        config_service: ObsidianConfigService | None = None,
    ):
        """
        Initialize ObsidianArtifactWriter.

        Args:
            config: ObsidianConfig to use directly.
            config_service: ObsidianConfigService to load config from.
        """
        self.logger = get_logger()
        self._config = config
        self._config_service = config_service or ObsidianConfigService()

    @property
    def config(self) -> ObsidianConfig | None:
        """Get the active configuration."""
        if self._config:
            return self._config
        return self._config_service.load_config()

    def write_decision(self, decision: DecisionRecord) -> Path | None:
        """
        Write a decision record to the Obsidian vault.

        Args:
            decision: DecisionRecord to write.

        Returns:
            Path to written file, None if failed or disabled.
        """
        config = self.config
        if not config:
            self.logger.debug("No Obsidian config available, skipping artifact write")
            return None

        # Check if decisions are enabled
        if "decisions" not in config.artifacts.types:
            self.logger.debug("Decision artifacts disabled in config")
            return None

        # Get output path
        output_dir = config.vault.path / config.artifacts.output_paths.get(
            "decisions", "Claude/Decisions/"
        )

        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate content
            filename = decision.to_filename()
            file_path = output_dir / filename
            content = self._generate_decision_content(decision, config)

            # Write file
            file_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Wrote decision artifact: {filename}")

            # Inject backlinks if enabled
            if config.artifacts.backlinks.enabled:
                self._inject_backlinks(decision, file_path, config)

            return file_path

        except Exception as e:
            self.logger.error(f"Failed to write decision artifact: {e}")
            return None

    def _generate_decision_content(
        self, decision: DecisionRecord, config: ObsidianConfig
    ) -> str:
        """Generate markdown content for a decision."""
        lines = []

        # Frontmatter
        frontmatter = self._build_frontmatter(decision, config)
        lines.append("---")
        lines.append(yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip())
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {decision.title}")
        lines.append("")

        # Decision type callout
        lines.append(f"> [!info] Decision Type: {decision.decision_type.title()}")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(decision.summary)
        lines.append("")

        # Context section
        if decision.context:
            lines.append("## Context")
            lines.append("")
            lines.append(decision.context)
            lines.append("")

        # Rationale section
        if decision.rationale:
            lines.append("## Rationale")
            lines.append("")
            lines.append(decision.rationale)
            lines.append("")

        # Related notes section
        if decision.source_notes:
            lines.append("## Related Notes")
            lines.append("")
            for note_path in decision.source_notes:
                lines.append(f"- [[{note_path}]]")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated by SuperClaude on {decision.created.strftime('%Y-%m-%d %H:%M')}*")

        return "\n".join(lines)

    def _build_frontmatter(
        self, decision: DecisionRecord, config: ObsidianConfig
    ) -> dict[str, Any]:
        """Build YAML frontmatter dictionary."""
        frontmatter: dict[str, Any] = {}

        # Build based on config includes
        includes = config.notes.frontmatter_include

        if "title" in includes:
            frontmatter["title"] = decision.title
        if "type" in includes:
            frontmatter["type"] = "decision"
        if "decision_type" in includes:
            frontmatter["decision_type"] = decision.decision_type
        if "project" in includes and decision.project:
            frontmatter["project"] = decision.project
        if "created" in includes:
            frontmatter["created"] = decision.created.isoformat()
        if "session_id" in includes and decision.session_id:
            frontmatter["session_id"] = decision.session_id
        if "tags" in includes:
            tags = ["decision", decision.decision_type]
            if decision.project:
                tags.append(decision.project.lower().replace(" ", "-"))
            frontmatter["tags"] = tags
        if "related" in includes and decision.source_notes:
            frontmatter["related"] = [
                f"[[{note}]]" for note in decision.source_notes
            ]

        # Add any extra metadata
        for key, value in decision.metadata.items():
            if key not in frontmatter:
                frontmatter[key] = value

        return frontmatter

    def _inject_backlinks(
        self,
        decision: DecisionRecord,
        decision_path: Path,
        config: ObsidianConfig,
    ) -> None:
        """Inject backlinks into source notes."""
        if not decision.source_notes:
            return

        vault_path = config.vault.path
        section_header = config.artifacts.backlinks.section
        decision_relative = str(decision_path.relative_to(vault_path))
        date_str = decision.created.strftime("%Y-%m-%d")

        for note_path in decision.source_notes:
            full_path = vault_path / note_path
            if not full_path.exists():
                self.logger.debug(f"Source note not found: {note_path}")
                continue

            try:
                content = full_path.read_text(encoding="utf-8")

                # Build backlink line
                backlink = f"- [[{decision_relative}|{decision.title}]] - {date_str}"

                # Check if section exists
                if section_header in content:
                    # Append to existing section
                    # Find section and add after it
                    lines = content.split("\n")
                    new_lines = []
                    in_section = False
                    added = False

                    for line in lines:
                        new_lines.append(line)
                        if line.strip() == section_header:
                            in_section = True
                        elif in_section and not added:
                            # Add after section header
                            if line.strip() == "" or line.startswith("- "):
                                # Skip until we find a non-list line or add at end of list
                                pass
                            else:
                                # Insert before this line
                                new_lines.insert(-1, backlink)
                                added = True
                                in_section = False

                    if not added:
                        # Add at end of file
                        new_lines.append(backlink)

                    content = "\n".join(new_lines)
                else:
                    # Add new section at end of file
                    content = content.rstrip() + "\n\n" + section_header + "\n\n" + backlink + "\n"

                full_path.write_text(content, encoding="utf-8")
                self.logger.debug(f"Injected backlink into {note_path}")

            except Exception as e:
                self.logger.debug(f"Failed to inject backlink into {note_path}: {e}")

    def should_sync(self) -> bool:
        """Check if artifact syncing is enabled."""
        config = self.config
        if not config:
            return False
        return config.artifacts.sync_on != "never"

    def get_output_dir(self, artifact_type: str = "decisions") -> Path | None:
        """Get the output directory for an artifact type."""
        config = self.config
        if not config:
            return None

        output_rel = config.artifacts.output_paths.get(artifact_type)
        if not output_rel:
            return None

        return config.vault.path / output_rel


def extract_decisions_from_evidence(
    tool_invocations: list[dict[str, Any]],
    project_name: str,
    session_id: str = "",
) -> list[DecisionRecord]:
    """
    Extract decision records from tool invocations.

    Looks for PAL consensus, thinkdeep, and architecture patterns.

    Args:
        tool_invocations: List of tool invocation records from EvidenceCollector.
        project_name: Project name for the decisions.
        session_id: Session ID for tracking.

    Returns:
        List of DecisionRecord objects.
    """
    decisions = []

    for invocation in tool_invocations:
        tool_name = invocation.get("tool_name", "")

        # Check for PAL consensus tool
        if "consensus" in tool_name.lower():
            decision = _parse_consensus_decision(
                invocation, project_name, session_id
            )
            if decision:
                decisions.append(decision)

        # Check for PAL thinkdeep tool
        elif "thinkdeep" in tool_name.lower():
            decision = _parse_thinkdeep_decision(
                invocation, project_name, session_id
            )
            if decision:
                decisions.append(decision)

        # Check for architecture patterns in other tools
        elif "architecture" in str(invocation.get("tool_input", {})).lower():
            decision = _parse_architecture_decision(
                invocation, project_name, session_id
            )
            if decision:
                decisions.append(decision)

    return decisions


def _parse_consensus_decision(
    invocation: dict[str, Any],
    project_name: str,
    session_id: str,
) -> DecisionRecord | None:
    """Parse a consensus tool invocation into a DecisionRecord."""
    tool_input = invocation.get("tool_input", {})
    tool_output = invocation.get("tool_output", "")

    # Extract question/topic as title
    question = tool_input.get("question", tool_input.get("prompt", ""))
    if not question:
        return None

    # Extract summary from output
    summary = str(tool_output)[:500] if tool_output else ""

    return DecisionRecord(
        title=f"Consensus: {question[:100]}",
        summary=summary,
        decision_type="consensus",
        context=f"Multi-model consensus requested for: {question}",
        rationale=str(tool_output) if tool_output else "",
        project=project_name,
        session_id=session_id,
    )


def _parse_thinkdeep_decision(
    invocation: dict[str, Any],
    project_name: str,
    session_id: str,
) -> DecisionRecord | None:
    """Parse a thinkdeep tool invocation into a DecisionRecord."""
    tool_input = invocation.get("tool_input", {})
    tool_output = invocation.get("tool_output", "")

    # Extract topic as title
    topic = tool_input.get("topic", tool_input.get("prompt", ""))
    if not topic:
        return None

    return DecisionRecord(
        title=f"Analysis: {topic[:100]}",
        summary=str(tool_output)[:500] if tool_output else "",
        decision_type="technical",
        context=f"Deep analysis requested for: {topic}",
        rationale=str(tool_output) if tool_output else "",
        project=project_name,
        session_id=session_id,
    )


def _parse_architecture_decision(
    invocation: dict[str, Any],
    project_name: str,
    session_id: str,
) -> DecisionRecord | None:
    """Parse an architecture-related invocation into a DecisionRecord."""
    tool_input = invocation.get("tool_input", {})
    tool_output = invocation.get("tool_output", "")

    # Try to extract meaningful title
    title = "Architecture Decision"
    for key in ["topic", "question", "prompt", "command"]:
        if key in tool_input:
            title = f"Architecture: {str(tool_input[key])[:80]}"
            break

    return DecisionRecord(
        title=title,
        summary=str(tool_output)[:500] if tool_output else "",
        decision_type="architecture",
        context=str(tool_input),
        rationale=str(tool_output) if tool_output else "",
        project=project_name,
        session_id=session_id,
    )
