"""
Obsidian Configuration Service for SuperClaude

Loads and validates .obsidian.yaml configuration files for vault integration.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..utils.logger import get_logger


@dataclass
class VaultConfig:
    """Configuration for Obsidian vault paths."""

    path: Path
    read_paths: list[str] = field(default_factory=lambda: ["Knowledge/"])
    output_base: str = "Claude/"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VaultConfig":
        """Create VaultConfig from dictionary."""
        path_str = data.get("path", "~/Documents/Obsidian")
        path = Path(path_str).expanduser()
        return cls(
            path=path,
            read_paths=data.get("read_paths", ["Knowledge/"]),
            output_base=data.get("output_base", "Claude/"),
        )


@dataclass
class RelevanceFilter:
    """Configuration for filtering relevant notes."""

    type: str = "project_name"  # "project_name", "tags", "path"
    field: str = "project"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RelevanceFilter":
        """Create RelevanceFilter from dictionary."""
        return cls(
            type=data.get("type", "project_name"),
            field=data.get("field", "project"),
        )


@dataclass
class ContextConfig:
    """Configuration for context extraction from vault."""

    relevance_filter: RelevanceFilter = field(default_factory=RelevanceFilter)
    extract_fields: list[str] = field(default_factory=lambda: ["summary", "tags", "category"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextConfig":
        """Create ContextConfig from dictionary."""
        filter_data = data.get("relevance_filter", {})
        return cls(
            relevance_filter=RelevanceFilter.from_dict(filter_data),
            extract_fields=data.get("extract_fields", ["summary", "tags", "category"]),
        )


@dataclass
class BacklinksConfig:
    """Configuration for backlink injection."""

    enabled: bool = True
    section: str = "## Claude References"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BacklinksConfig":
        """Create BacklinksConfig from dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            section=data.get("section", "## Claude References"),
        )


@dataclass
class ArtifactConfig:
    """Configuration for artifact syncing."""

    sync_on: str = "task_completion"  # "task_completion", "manual", "never"
    types: list[str] = field(default_factory=lambda: ["decisions"])
    output_paths: dict[str, str] = field(default_factory=lambda: {"decisions": "Claude/Decisions/"})
    backlinks: BacklinksConfig = field(default_factory=BacklinksConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactConfig":
        """Create ArtifactConfig from dictionary."""
        backlinks_data = data.get("backlinks", {})
        return cls(
            sync_on=data.get("sync_on", "task_completion"),
            types=data.get("types", ["decisions"]),
            output_paths=data.get("output_paths", {"decisions": "Claude/Decisions/"}),
            backlinks=BacklinksConfig.from_dict(backlinks_data),
        )


@dataclass
class NoteConfig:
    """Configuration for note formatting."""

    format: str = "rich"  # "rich", "minimal"
    frontmatter_include: list[str] = field(
        default_factory=lambda: [
            "title",
            "type",
            "decision_type",
            "project",
            "created",
            "session_id",
            "tags",
            "related",
        ]
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NoteConfig":
        """Create NoteConfig from dictionary."""
        return cls(
            format=data.get("format", "rich"),
            frontmatter_include=data.get(
                "frontmatter_include",
                [
                    "title",
                    "type",
                    "decision_type",
                    "project",
                    "created",
                    "session_id",
                    "tags",
                    "related",
                ],
            ),
        )


@dataclass
class ObsidianConfig:
    """Complete Obsidian integration configuration."""

    vault: VaultConfig
    context: ContextConfig = field(default_factory=ContextConfig)
    artifacts: ArtifactConfig = field(default_factory=ArtifactConfig)
    notes: NoteConfig = field(default_factory=NoteConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObsidianConfig":
        """Create ObsidianConfig from dictionary."""
        vault_data = data.get("vault", {})
        if not vault_data:
            raise ValueError("Obsidian config must include 'vault' section")

        return cls(
            vault=VaultConfig.from_dict(vault_data),
            context=ContextConfig.from_dict(data.get("context", {})),
            artifacts=ArtifactConfig.from_dict(data.get("artifacts", {})),
            notes=NoteConfig.from_dict(data.get("notes", {})),
        )

    @classmethod
    def default(cls) -> "ObsidianConfig":
        """Create default configuration."""
        return cls(
            vault=VaultConfig(path=Path.home() / "Documents" / "Obsidian"),
            context=ContextConfig(),
            artifacts=ArtifactConfig(),
            notes=NoteConfig(),
        )


class ObsidianConfigService:
    """Service for loading and managing Obsidian configuration."""

    CONFIG_FILENAME = ".obsidian.yaml"

    def __init__(self, project_root: Path | None = None):
        """
        Initialize ObsidianConfigService.

        Args:
            project_root: Project root directory to look for config.
                         If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()
        self.logger = get_logger()
        self._config_cache: ObsidianConfig | None = None

    @property
    def config_path(self) -> Path:
        """Path to the .obsidian.yaml config file."""
        return self.project_root / self.CONFIG_FILENAME

    def config_exists(self) -> bool:
        """Check if .obsidian.yaml exists in project root."""
        return self.config_path.exists()

    def load_config(self, force_reload: bool = False) -> ObsidianConfig | None:
        """
        Load Obsidian configuration from .obsidian.yaml.

        Args:
            force_reload: Force reload from file even if cached.

        Returns:
            ObsidianConfig if loaded successfully, None if no config file.

        Raises:
            ValueError: If config file is invalid.
        """
        if self._config_cache is not None and not force_reload:
            return self._config_cache

        if not self.config_exists():
            self.logger.debug(f"No Obsidian config found at {self.config_path}")
            return None

        try:
            with open(self.config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError("Config file must contain a YAML mapping")

            self._config_cache = ObsidianConfig.from_dict(data)
            self.logger.debug(f"Loaded Obsidian config from {self.config_path}")
            return self._config_cache

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {self.config_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load Obsidian config: {e}") from e

    def clear_cache(self) -> None:
        """Clear cached configuration."""
        self._config_cache = None

    def validate_vault_path(self) -> bool:
        """
        Validate that the configured vault path exists.

        Returns:
            True if vault path exists, False otherwise.
        """
        config = self.load_config()
        if not config:
            return False

        vault_path = config.vault.path
        if not vault_path.exists():
            self.logger.warning(f"Obsidian vault not found at {vault_path}")
            return False

        return True

    def get_vault_path(self) -> Path | None:
        """
        Get the configured vault path.

        Returns:
            Path to vault if config exists, None otherwise.
        """
        config = self.load_config()
        return config.vault.path if config else None

    def get_read_paths(self) -> list[Path]:
        """
        Get absolute paths to read from in the vault.

        Returns:
            List of absolute paths to read directories.
        """
        config = self.load_config()
        if not config:
            return []

        vault_path = config.vault.path
        return [vault_path / rp for rp in config.vault.read_paths]

    def get_output_path(self, artifact_type: str = "decisions") -> Path | None:
        """
        Get the output path for a specific artifact type.

        Args:
            artifact_type: Type of artifact (e.g., "decisions").

        Returns:
            Absolute path to output directory, None if not configured.
        """
        config = self.load_config()
        if not config:
            return None

        output_rel = config.artifacts.output_paths.get(artifact_type)
        if not output_rel:
            return None

        return config.vault.path / output_rel

    def create_default_config(self) -> Path:
        """
        Create a default .obsidian.yaml in the project root.

        Returns:
            Path to created config file.
        """
        default_content = """\
# Obsidian Integration Configuration for SuperClaude
# See: https://github.com/anthropics/superclaude/docs/obsidian.md

vault:
  path: ~/Documents/Obsidian
  read_paths:
    - Knowledge/
  output_base: Claude/

context:
  relevance_filter:
    type: project_name
    field: project
  extract_fields:
    - summary
    - tags
    - category

artifacts:
  sync_on: task_completion  # task_completion, manual, never
  types:
    - decisions
  output_paths:
    decisions: Claude/Decisions/
  backlinks:
    enabled: true
    section: "## Claude References"

notes:
  format: rich  # rich, minimal
  frontmatter_include:
    - title
    - type
    - decision_type
    - project
    - created
    - session_id
    - tags
    - related
"""
        self.config_path.write_text(default_content, encoding="utf-8")
        self.logger.success(f"Created default Obsidian config at {self.config_path}")
        self.clear_cache()
        return self.config_path
