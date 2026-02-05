"""
Obsidian CLAUDE.md Integration Service for SuperClaude

Manages @OBSIDIAN.md file and integrates with CLAUDE.md imports.
"""

from pathlib import Path

from ..utils.logger import get_logger
from .claude_md import CLAUDEMdService
from .obsidian_config import ObsidianConfigService
from .obsidian_context import ObsidianContextGenerator


class ObsidianMdService:
    """
    Service for managing @OBSIDIAN.md and CLAUDE.md integration.

    Handles:
    - Generating @OBSIDIAN.md from vault content
    - Adding @OBSIDIAN.md import to CLAUDE.md
    - Refreshing context when vault changes
    """

    OBSIDIAN_MD_FILENAME = "OBSIDIAN.md"
    CATEGORY_NAME = "Obsidian Context"

    def __init__(
        self,
        install_dir: Path,
        project_root: Path | None = None,
        project_name: str | None = None,
    ):
        """
        Initialize ObsidianMdService.

        Args:
            install_dir: Installation directory (typically ~/.claude).
            project_root: Project root for config lookup. Defaults to cwd.
            project_name: Name of project. Defaults to project root folder name.
        """
        self.install_dir = install_dir
        self.project_root = project_root or Path.cwd()
        self.project_name = project_name or self.project_root.name
        self.logger = get_logger()

        # Services
        self._config_service = ObsidianConfigService(self.project_root)
        self._claude_md_service = CLAUDEMdService(install_dir)

    @property
    def obsidian_md_path(self) -> Path:
        """Path to @OBSIDIAN.md file."""
        return self.install_dir / self.OBSIDIAN_MD_FILENAME

    def is_configured(self) -> bool:
        """Check if Obsidian integration is configured."""
        return self._config_service.config_exists()

    def setup_obsidian_context(self) -> bool:
        """
        Generate @OBSIDIAN.md and add import to CLAUDE.md.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_configured():
            self.logger.debug("Obsidian not configured, skipping context setup")
            return False

        try:
            # Validate vault exists
            if not self._config_service.validate_vault_path():
                self.logger.warning("Obsidian vault path not found, skipping")
                return False

            # Generate context content
            generator = ObsidianContextGenerator(
                project_name=self.project_name,
                config_service=self._config_service,
            )
            content = generator.generate_context()

            if not content:
                self.logger.debug("No Obsidian context generated")
                return False

            # Write @OBSIDIAN.md
            self.install_dir.mkdir(parents=True, exist_ok=True)
            self.obsidian_md_path.write_text(content, encoding="utf-8")
            self.logger.info(f"Generated {self.OBSIDIAN_MD_FILENAME}")

            # Add import to CLAUDE.md
            success = self._claude_md_service.add_imports(
                files=[self.OBSIDIAN_MD_FILENAME],
                category=self.CATEGORY_NAME,
            )

            if success:
                note_count = generator.get_note_count()
                self.logger.success(
                    f"Obsidian context integrated ({note_count} notes)"
                )

            return success

        except Exception as e:
            self.logger.error(f"Failed to setup Obsidian context: {e}")
            return False

    def refresh_context(self) -> bool:
        """
        Refresh @OBSIDIAN.md if vault content has changed.

        Returns:
            True if refreshed, False if no changes or error.
        """
        if not self.is_configured():
            return False

        try:
            # Read existing content
            existing_content = ""
            if self.obsidian_md_path.exists():
                existing_content = self.obsidian_md_path.read_text(encoding="utf-8")

            # Check if regeneration needed
            generator = ObsidianContextGenerator(
                project_name=self.project_name,
                config_service=self._config_service,
            )

            if not generator.should_regenerate(existing_content):
                self.logger.debug("Obsidian context is up to date")
                return False

            # Regenerate
            content = generator.generate_context()
            if not content:
                return False

            self.obsidian_md_path.write_text(content, encoding="utf-8")
            self.logger.info("Refreshed Obsidian context")
            return True

        except Exception as e:
            self.logger.error(f"Failed to refresh Obsidian context: {e}")
            return False

    def remove_obsidian_context(self) -> bool:
        """
        Remove @OBSIDIAN.md and its import from CLAUDE.md.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Remove import from CLAUDE.md
            self._claude_md_service.remove_imports([self.OBSIDIAN_MD_FILENAME])

            # Remove @OBSIDIAN.md file
            if self.obsidian_md_path.exists():
                self.obsidian_md_path.unlink()
                self.logger.info(f"Removed {self.OBSIDIAN_MD_FILENAME}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to remove Obsidian context: {e}")
            return False

    def get_status(self) -> dict:
        """
        Get current Obsidian integration status.

        Returns:
            Status dictionary with configuration and content info.
        """
        status = {
            "configured": self.is_configured(),
            "vault_exists": False,
            "context_exists": self.obsidian_md_path.exists(),
            "note_count": 0,
            "categories": [],
            "vault_path": None,
        }

        if not status["configured"]:
            return status

        config = self._config_service.load_config()
        if config:
            status["vault_path"] = str(config.vault.path)
            status["vault_exists"] = config.vault.path.exists()

        if status["vault_exists"]:
            generator = ObsidianContextGenerator(
                project_name=self.project_name,
                config_service=self._config_service,
            )
            status["note_count"] = generator.get_note_count()
            status["categories"] = generator.get_categories()

        return status


def setup_obsidian_integration(
    install_dir: Path,
    project_root: Path | None = None,
    project_name: str | None = None,
) -> bool:
    """
    Convenience function to setup Obsidian integration.

    Args:
        install_dir: Installation directory (typically ~/.claude).
        project_root: Project root for config lookup.
        project_name: Name of project.

    Returns:
        True if successful, False otherwise.
    """
    service = ObsidianMdService(
        install_dir=install_dir,
        project_root=project_root,
        project_name=project_name,
    )
    return service.setup_obsidian_context()
