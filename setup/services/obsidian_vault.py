"""
Obsidian Vault Service for SuperClaude

Reads and parses Obsidian vault notes with frontmatter extraction.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as _yaml_err:
    raise ImportError(
        "Obsidian integration requires PyYAML. Install with: pip install pyyaml"
    ) from _yaml_err

from ..utils.logger import get_logger
from .obsidian_config import ObsidianConfig, ObsidianConfigService


@dataclass
class ObsidianNote:
    """Represents a parsed Obsidian note."""

    path: Path
    relative_path: str
    title: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    content: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def project(self) -> str | None:
        """Get project from frontmatter."""
        return self.frontmatter.get("project")

    @property
    def category(self) -> str | None:
        """Get category from frontmatter."""
        return self.frontmatter.get("category")

    @property
    def summary(self) -> str | None:
        """Get summary from frontmatter or first paragraph."""
        if "summary" in self.frontmatter:
            return self.frontmatter["summary"]
        # Extract first paragraph as summary
        lines = self.content.strip().split("\n\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:500]  # Limit summary length
        return None

    def matches_project(self, project_name: str) -> bool:
        """
        Check if note matches the given project name.

        Matches against:
        1. frontmatter 'project' field
        2. tags containing project name
        3. path containing project name
        """
        project_lower = project_name.lower()

        # Check frontmatter project field
        if self.project and project_lower in self.project.lower():
            return True

        # Check tags
        for tag in self.tags:
            if project_lower in tag.lower():
                return True

        # Check path
        if project_lower in self.relative_path.lower():
            return True

        return False


class ObsidianVaultService:
    """Service for reading and parsing Obsidian vault notes."""

    # Regex to match YAML frontmatter block
    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

    # Regex to extract inline tags (#tag)
    TAG_PATTERN = re.compile(r"(?:^|\s)#([a-zA-Z0-9_/-]+)")

    def __init__(
        self,
        config: ObsidianConfig | None = None,
        config_service: ObsidianConfigService | None = None,
    ):
        """
        Initialize ObsidianVaultService.

        Args:
            config: ObsidianConfig to use directly.
            config_service: ObsidianConfigService to load config from.
        """
        self.logger = get_logger()
        self._config = config
        self._config_service = config_service

    @property
    def config(self) -> ObsidianConfig | None:
        """Get the active configuration."""
        if self._config:
            return self._config
        if self._config_service:
            return self._config_service.load_config()
        return None

    def scan_knowledge_folder(self) -> list[ObsidianNote]:
        """
        Scan configured knowledge folders for markdown notes.

        Returns:
            List of parsed ObsidianNote objects.
        """
        config = self.config
        if not config:
            self.logger.warning("No Obsidian config available")
            return []

        vault_path = config.vault.path
        if not vault_path.exists():
            self.logger.warning(f"Vault path does not exist: {vault_path}")
            return []

        notes = []
        for read_path in config.vault.read_paths:
            folder = vault_path / read_path
            if not folder.exists():
                self.logger.debug(f"Read path does not exist: {folder}")
                continue

            self.logger.debug(f"Scanning folder: {folder}")
            for md_file in folder.rglob("*.md"):
                note = self._parse_note(md_file, vault_path)
                if note:
                    notes.append(note)

        self.logger.debug(f"Found {len(notes)} notes in vault")
        return notes

    def filter_by_project(self, notes: list[ObsidianNote], project_name: str) -> list[ObsidianNote]:
        """
        Filter notes by project name.

        Args:
            notes: List of notes to filter.
            project_name: Project name to match.

        Returns:
            List of notes matching the project.
        """
        matching = [n for n in notes if n.matches_project(project_name)]
        self.logger.debug(
            f"Filtered {len(notes)} notes to {len(matching)} for project '{project_name}'"
        )
        return matching

    def get_note_by_path(self, relative_path: str) -> ObsidianNote | None:
        """
        Get a specific note by its relative path in the vault.

        Args:
            relative_path: Relative path from vault root.

        Returns:
            ObsidianNote if found, None otherwise.
        """
        config = self.config
        if not config:
            return None

        vault_path = config.vault.path
        note_path = vault_path / relative_path

        if not note_path.exists():
            self.logger.debug(f"Note not found: {note_path}")
            return None

        return self._parse_note(note_path, vault_path)

    def get_relevant_notes(self, project_name: str) -> list[ObsidianNote]:
        """
        Get all notes relevant to a project.

        Convenience method that scans and filters in one call.

        Args:
            project_name: Project name to match.

        Returns:
            List of relevant notes.
        """
        all_notes = self.scan_knowledge_folder()
        return self.filter_by_project(all_notes, project_name)

    def _parse_note(self, file_path: Path, vault_root: Path) -> ObsidianNote | None:
        """
        Parse a markdown file into an ObsidianNote.

        Args:
            file_path: Path to the markdown file.
            vault_root: Root path of the vault for relative path calculation.

        Returns:
            ObsidianNote or None if parsing fails.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            relative_path = str(file_path.relative_to(vault_root))

            # Extract frontmatter
            frontmatter = {}
            body = content

            match = self.FRONTMATTER_PATTERN.match(content)
            if match:
                try:
                    frontmatter = yaml.safe_load(match.group(1)) or {}
                except yaml.YAMLError:
                    self.logger.debug(f"Invalid YAML frontmatter in {relative_path}")
                body = content[match.end() :]

            # Extract title (from frontmatter or first heading or filename)
            title = frontmatter.get("title", "")
            if not title:
                heading_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
                if heading_match:
                    title = heading_match.group(1).strip()
                else:
                    title = file_path.stem

            # Extract tags from frontmatter and inline
            tags = []
            if "tags" in frontmatter:
                fm_tags = frontmatter["tags"]
                if isinstance(fm_tags, list):
                    tags.extend(fm_tags)
                elif isinstance(fm_tags, str):
                    tags.append(fm_tags)

            # Find inline tags
            inline_tags = self.TAG_PATTERN.findall(body)
            tags.extend(inline_tags)

            # Deduplicate tags
            tags = list(dict.fromkeys(tags))

            return ObsidianNote(
                path=file_path,
                relative_path=relative_path,
                title=title,
                frontmatter=frontmatter,
                content=body.strip(),
                tags=tags,
            )

        except Exception as e:
            self.logger.debug(f"Failed to parse note {file_path}: {e}")
            return None

    def note_exists(self, relative_path: str) -> bool:
        """
        Check if a note exists at the given relative path.

        Args:
            relative_path: Relative path from vault root.

        Returns:
            True if note exists, False otherwise.
        """
        config = self.config
        if not config:
            return False

        note_path = config.vault.path / relative_path
        return note_path.exists()

    def get_notes_by_tag(self, tag: str) -> list[ObsidianNote]:
        """
        Get all notes with a specific tag.

        Args:
            tag: Tag to search for.

        Returns:
            List of notes with the tag.
        """
        all_notes = self.scan_knowledge_folder()
        tag_lower = tag.lower()
        return [n for n in all_notes if any(t.lower() == tag_lower for t in n.tags)]

    def get_notes_by_category(self, category: str) -> list[ObsidianNote]:
        """
        Get all notes with a specific category.

        Args:
            category: Category to filter by.

        Returns:
            List of notes with the category.
        """
        all_notes = self.scan_knowledge_folder()
        category_lower = category.lower()
        return [n for n in all_notes if n.category and n.category.lower() == category_lower]
