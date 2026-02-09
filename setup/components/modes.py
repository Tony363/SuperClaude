"""
Modes component for SuperClaude behavioral modes
"""

from pathlib import Path
from typing import Any

from setup import __version__

from ..core.base import Component
from ..services.claude_md import CLAUDEMdService


class ModesComponent(Component):
    """SuperClaude behavioral modes component"""

    def __init__(self, install_dir: Path | None = None):
        """Initialize modes component"""
        super().__init__(install_dir, Path(""))

    def get_metadata(self) -> dict[str, str]:
        """Get component metadata"""
        return {
            "name": "modes",
            "version": __version__,
            "description": "SuperClaude behavioral modes (Brainstorming, Introspection, Task Management, Token Efficiency)",
            "category": "modes",
        }

    def _install(self, config: dict[str, Any]) -> bool:
        """Install modes component.

        In v7, behavioral modes are managed by the Python behavioral_manager.
        No markdown mode files need to be copied — this only registers metadata.
        """
        self.logger.info("Installing SuperClaude behavioral modes...")
        self.logger.info("Modes managed by Python behavioral_manager — no source files to copy")
        return self._post_install()

    def _post_install(self) -> bool:
        """Post-installation tasks"""
        try:
            # Update metadata
            metadata_mods = {
                "components": {
                    "modes": {
                        "version": __version__,
                        "installed": True,
                        "files_count": len(self.component_files),
                        "files": list(self.component_files),
                        "memory_profile": getattr(self, "_selected_profile", "minimal"),
                    }
                }
            }
            self.settings_manager.update_metadata(metadata_mods)
            self.settings_manager.add_component_registration(
                "modes",
                {
                    "version": __version__,
                    "category": "modes",
                    "files_count": len(self.component_files),
                    "files": list(self.component_files),
                    "memory_profile": getattr(self, "_selected_profile", "minimal"),
                },
            )
            self.logger.info("Updated metadata with modes component registration")

            # Update CLAUDE.md with mode imports
            try:
                manager = CLAUDEMdService(self.install_dir)
                manager.add_imports(self.component_files, category="Behavioral Modes")
                self.logger.info("Updated CLAUDE.md with mode imports")
            except Exception as e:
                self.logger.warning(f"Failed to update CLAUDE.md with mode imports: {e}")
                # Don't fail the whole installation for this

            return True
        except Exception as e:
            self.logger.error(f"Failed to update metadata: {e}")
            return False

    def validate_installation(self) -> tuple[bool, list[str]]:
        """Validate modes component installation."""
        errors: list[str] = []
        files_to_check = self._get_installed_file_manifest() or self.component_files

        for filename in files_to_check:
            target = self.install_component_subdir / filename
            if not target.exists():
                errors.append(f"Missing mode file: {target}")
            elif not target.is_file():
                errors.append(f"Mode file is not a regular file: {target}")

        if not self.settings_manager.is_component_installed("modes"):
            errors.append("Modes component not registered in metadata")

        return len(errors) == 0, errors

    def _get_installed_file_manifest(self) -> list[str] | None:
        try:
            components = self.settings_manager.get_installed_components()
            info = components.get("modes") or {}
            files = info.get("files")
            if isinstance(files, list) and files:
                return files
        except Exception as exc:
            self.logger.debug(f"Could not read installed modes file manifest: {exc}")
        return None

    def uninstall(self) -> bool:
        """Uninstall modes component"""
        try:
            self.logger.info("Uninstalling SuperClaude modes component...")

            # Strip mode @imports from CLAUDE.md before removing files
            try:
                files_to_strip = [f for _, f in self.get_files_to_install()]
                filenames = [f.name for f in files_to_strip]
                if filenames:
                    manager = CLAUDEMdService(self.install_dir)
                    manager.remove_imports(filenames)
                    self.logger.debug("Stripped mode imports from CLAUDE.md")
            except Exception as e:
                self.logger.warning(f"Could not clean CLAUDE.md mode imports: {e}")

            # Remove mode files
            removed_count = 0
            for _, target in self.get_files_to_install():
                if self.file_manager.remove_file(target):
                    removed_count += 1
                    self.logger.debug(f"Removed {target.name}")

            # Remove modes directory if empty
            try:
                if self.install_component_subdir.exists():
                    remaining_files = list(self.install_component_subdir.iterdir())
                    if not remaining_files:
                        self.install_component_subdir.rmdir()
                        self.logger.debug("Removed empty modes directory")
            except Exception as e:
                self.logger.warning(f"Could not remove modes directory: {e}")

            # Update settings.json
            try:
                if self.settings_manager.is_component_installed("modes"):
                    self.settings_manager.remove_component_registration("modes")
                    self.logger.info("Removed modes component from settings.json")
            except Exception as e:
                self.logger.warning(f"Could not update settings.json: {e}")

            self.logger.success(f"Modes component uninstalled ({removed_count} files removed)")
            return True

        except Exception as e:
            self.logger.exception(f"Unexpected error during modes uninstallation: {e}")
            return False

    def get_dependencies(self) -> list[str]:
        """Get dependencies"""
        return ["core"]

    def validate_prerequisites(self, installSubPath: Path | None = None) -> tuple[bool, list[str]]:
        """No prerequisites if mode source files don't exist yet."""
        source_dir = self._get_source_dir()
        if source_dir is None:
            return True, []
        return super().validate_prerequisites(installSubPath)

    def _get_source_dir(self) -> Path | None:
        """Get source directory for mode files"""
        project_root = Path(__file__).parent.parent.parent
        modes_dir = project_root / "SuperClaude" / "Modes"

        if not modes_dir.exists():
            return None

        return modes_dir

    def get_size_estimate(self) -> int:
        """Get estimated installation size"""
        source_dir = self._get_source_dir()
        total_size = 0

        if source_dir and source_dir.exists():
            for filename in self.component_files:
                file_path = source_dir / filename
                if file_path.exists():
                    total_size += file_path.stat().st_size

        # Minimum size estimate
        total_size = max(total_size, 20480)  # At least 20KB

        return total_size
