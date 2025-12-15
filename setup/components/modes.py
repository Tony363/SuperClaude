"""
Modes component for SuperClaude behavioral modes
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from setup import __version__

from ..core.base import Component
from ..services.claude_md import CLAUDEMdService


class ModesComponent(Component):
    """SuperClaude behavioral modes component"""

    MINIMAL_FILES = [
        "MODE_Normal.md",
        "MODE_Task_Management.md",
        "MODE_Token_Efficiency.md",
    ]

    def __init__(self, install_dir: Optional[Path] = None):
        """Initialize modes component"""
        self._selected_profile = "minimal"
        super().__init__(install_dir, Path(""))

    def get_metadata(self) -> Dict[str, str]:
        """Get component metadata"""
        return {
            "name": "modes",
            "version": __version__,
            "description": "SuperClaude behavioral modes (Brainstorming, Introspection, Task Management, Token Efficiency)",
            "category": "modes",
        }

    def _install(self, config: Dict[str, Any]) -> bool:
        """Install modes component"""
        self.logger.info("Installing SuperClaude behavioral modes...")

        profile = (config or {}).get("memory_profile", "minimal").lower()
        all_files = set(self._discover_component_files())

        if profile == "full":
            selected_files = sorted(all_files)
            self.logger.debug("Using full memory profile for modes component")
        else:
            minimal_files = [
                fname for fname in self.MINIMAL_FILES if fname in all_files
            ]
            missing = [fname for fname in self.MINIMAL_FILES if fname not in all_files]
            if missing:
                self.logger.warning(
                    "Minimal mode files missing from source directory: %s",
                    missing,
                )
            selected_files = minimal_files or sorted(all_files)
            self.logger.info(
                "Applying minimal memory profile for modes component (%d files)",
                len(selected_files),
            )

        self.component_files = selected_files
        self._selected_profile = profile

        # Validate installation
        success, errors = self.validate_prerequisites()
        if not success:
            for error in errors:
                self.logger.error(error)
            return False

        # Get files to install
        files_to_install = self.get_files_to_install()

        if not files_to_install:
            self.logger.warning("No mode files found to install")
            return False

        # Copy mode files
        success_count = 0
        for source, target in files_to_install:
            self.logger.debug(f"Copying {source.name} to {target}")

            if self.file_manager.copy_file(source, target):
                success_count += 1
                self.logger.debug(f"Successfully copied {source.name}")
            else:
                self.logger.error(f"Failed to copy {source.name}")

        if success_count != len(files_to_install):
            self.logger.error(
                f"Only {success_count}/{len(files_to_install)} mode files copied successfully"
            )
            return False

        self.logger.success(
            f"Modes component installed successfully ({success_count} mode files)"
        )

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
                self.logger.warning(
                    f"Failed to update CLAUDE.md with mode imports: {e}"
                )
                # Don't fail the whole installation for this

            return True
        except Exception as e:
            self.logger.error(f"Failed to update metadata: {e}")
            return False

    def validate_installation(self) -> Tuple[bool, List[str]]:
        """Validate modes component installation."""
        errors: List[str] = []
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

    def _get_installed_file_manifest(self) -> Optional[List[str]]:
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

            self.logger.success(
                f"Modes component uninstalled ({removed_count} files removed)"
            )
            return True

        except Exception as e:
            self.logger.exception(f"Unexpected error during modes uninstallation: {e}")
            return False

    def get_dependencies(self) -> List[str]:
        """Get dependencies"""
        return ["core"]

    def _get_source_dir(self) -> Optional[Path]:
        """Get source directory for mode files"""
        # Assume we're in SuperClaude/setup/components/modes.py
        # and mode files are in SuperClaude/SuperClaude/Modes/
        project_root = Path(__file__).parent.parent.parent
        modes_dir = project_root / "SuperClaude" / "Modes"

        # Return None if directory doesn't exist to prevent warning
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
