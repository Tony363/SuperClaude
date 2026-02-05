"""
Obsidian Context Generator for SuperClaude

Generates @OBSIDIAN.md content from relevant vault notes.
"""

from datetime import datetime
from pathlib import Path

from ..utils.logger import get_logger
from .obsidian_config import ObsidianConfig, ObsidianConfigService
from .obsidian_vault import ObsidianNote, ObsidianVaultService


class ObsidianContextGenerator:
    """Generates context markdown from Obsidian vault notes."""

    def __init__(
        self,
        project_name: str,
        config: ObsidianConfig | None = None,
        config_service: ObsidianConfigService | None = None,
        vault_service: ObsidianVaultService | None = None,
    ):
        """
        Initialize ObsidianContextGenerator.

        Args:
            project_name: Name of the project to generate context for.
            config: ObsidianConfig to use directly.
            config_service: ObsidianConfigService to load config from.
            vault_service: ObsidianVaultService to use for reading notes.
        """
        self.project_name = project_name
        self.logger = get_logger()

        # Setup services
        self._config = config
        self._config_service = config_service or ObsidianConfigService()
        self._vault_service = vault_service or ObsidianVaultService(
            config=config, config_service=self._config_service
        )

    @property
    def config(self) -> ObsidianConfig | None:
        """Get the active configuration."""
        if self._config:
            return self._config
        return self._config_service.load_config()

    def generate_context(self) -> str:
        """
        Generate @OBSIDIAN.md content from relevant vault notes.

        Returns:
            Markdown content for @OBSIDIAN.md file.
        """
        config = self.config
        if not config:
            self.logger.debug("No Obsidian config available, skipping context generation")
            return ""

        # Get relevant notes
        notes = self._vault_service.get_relevant_notes(self.project_name)

        if not notes:
            self.logger.debug(f"No relevant notes found for project '{self.project_name}'")
            return self._generate_empty_context()

        return self._generate_full_context(notes, config)

    def _generate_empty_context(self) -> str:
        """Generate context when no notes are found."""
        return f"""\
# Obsidian Knowledge Context

Project: **{self.project_name}**
Generated: {datetime.now().isoformat()}

---

*No relevant notes found in Obsidian vault.*

To add context:
1. Create notes in your `Knowledge/` folder
2. Add frontmatter with `project: {self.project_name}`
3. Or tag notes with `#{self.project_name.lower().replace(" ", "-")}`
"""

    def _generate_full_context(self, notes: list[ObsidianNote], config: ObsidianConfig) -> str:
        """Generate full context from notes."""
        lines = [
            "# Obsidian Knowledge Context",
            "",
            f"Project: **{self.project_name}**",
            f"Generated: {datetime.now().isoformat()}",
            f"Source: `{config.vault.path}`",
            "",
            "---",
            "",
        ]

        # Group notes by category
        notes_by_category = self._group_by_category(notes)

        for category, category_notes in notes_by_category.items():
            lines.append(f"## {category}")
            lines.append("")

            for note in category_notes:
                lines.extend(self._format_note(note, config))
                lines.append("")

            lines.append("---")
            lines.append("")

        # Footer
        lines.append(f"*{len(notes)} relevant notes loaded from Obsidian vault*")

        return "\n".join(lines)

    def _group_by_category(self, notes: list[ObsidianNote]) -> dict[str, list[ObsidianNote]]:
        """Group notes by category."""
        grouped: dict[str, list[ObsidianNote]] = {}

        for note in notes:
            category = note.category or "Uncategorized"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(note)

        # Sort categories alphabetically, with "Uncategorized" last
        sorted_grouped: dict[str, list[ObsidianNote]] = {}
        for key in sorted(grouped.keys()):
            if key != "Uncategorized":
                sorted_grouped[key] = grouped[key]
        if "Uncategorized" in grouped:
            sorted_grouped["Uncategorized"] = grouped["Uncategorized"]

        return sorted_grouped

    def _format_note(self, note: ObsidianNote, config: ObsidianConfig) -> list[str]:
        """Format a single note for context output."""
        lines = [f"### {note.title}"]

        # Build metadata line
        metadata_parts = []
        if note.tags:
            tags_str = ", ".join(note.tags[:5])  # Limit to 5 tags
            metadata_parts.append(f"tags: {tags_str}")

        # Add extracted fields from frontmatter
        for field in config.context.extract_fields:
            if field in ("tags", "summary"):
                continue  # Handled separately
            value = note.frontmatter.get(field)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value[:3])
                metadata_parts.append(f"{field}: {value}")

        if metadata_parts:
            lines.append(f"*{' | '.join(metadata_parts)}*")

        lines.append("")

        # Add summary
        summary = note.summary
        if summary:
            # Limit summary to reasonable length
            if len(summary) > 400:
                summary = summary[:400] + "..."
            lines.append(summary)
            lines.append("")

        # Add source link
        lines.append(f"*Source: [[{note.relative_path}]]*")

        return lines

    def should_regenerate(self, existing_content: str) -> bool:
        """
        Check if context should be regenerated.

        Args:
            existing_content: Current @OBSIDIAN.md content.

        Returns:
            True if regeneration needed, False otherwise.
        """
        if not existing_content:
            return True

        # Check if project name changed
        if f"Project: **{self.project_name}**" not in existing_content:
            return True

        # Check if vault has changed (by comparing note count)
        notes = self._vault_service.get_relevant_notes(self.project_name)
        current_count = len(notes)

        # Extract count from existing content
        import re

        match = re.search(r"\*(\d+) relevant notes loaded", existing_content)
        if match:
            existing_count = int(match.group(1))
            if existing_count != current_count:
                return True
        else:
            # Can't determine, regenerate to be safe
            return True

        return False

    def get_note_count(self) -> int:
        """Get the number of relevant notes."""
        notes = self._vault_service.get_relevant_notes(self.project_name)
        return len(notes)

    def get_categories(self) -> list[str]:
        """Get list of categories from relevant notes."""
        notes = self._vault_service.get_relevant_notes(self.project_name)
        categories = set()
        for note in notes:
            if note.category:
                categories.add(note.category)
        return sorted(categories)


def generate_obsidian_context(
    project_name: str,
    project_root: Path | None = None,
) -> str:
    """
    Convenience function to generate Obsidian context.

    Args:
        project_name: Name of the project.
        project_root: Project root for config lookup.

    Returns:
        Generated @OBSIDIAN.md content.
    """
    config_service = ObsidianConfigService(project_root)
    generator = ObsidianContextGenerator(
        project_name=project_name,
        config_service=config_service,
    )
    return generator.generate_context()
