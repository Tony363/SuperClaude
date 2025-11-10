"""
Core component for SuperClaude framework files installation
"""

from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
import shutil

from ..core.base import Component
from ..services.claude_md import CLAUDEMdService
from setup import __version__

class CoreComponent(Component):
    """Core SuperClaude framework files component"""

    MINIMAL_FILES = [
        "AGENTS.md",
        "CHEATSHEET.md",
        "CLAUDE_CORE.md",
        "FLAGS.md",
        "PRINCIPLES.md",
        "QUICKSTART.md",
        "RULES.md",
        "RULES_CRITICAL.md",
        "RULES_RECOMMENDED.md",
        "TOOLS.md",
        "WORKFLOWS_SUMMARY.md",
        "OPERATIONS_SUMMARY.md",
    ]
    
    def __init__(self, install_dir: Optional[Path] = None):
        """Initialize core component"""
        self._selected_profile = "minimal"
        super().__init__(install_dir)
    
    def get_metadata(self) -> Dict[str, str]:
        """Get component metadata"""
        return {
            "name": "core",
            "version": __version__,
            "description": "SuperClaude framework documentation and core files",
            "category": "core"
        }
    
    def get_metadata_modifications(self) -> Dict[str, Any]:
        """Get metadata modifications for SuperClaude"""
        return {
            "framework": {
                "version": __version__,
                "name": "SuperClaude",
                "description": "AI-enhanced development framework for Claude Code",
                "installation_type": "global",
                "components": ["core"]
            },
            "superclaude": {
                "enabled": True,
                "version": __version__,
                "profile": "default",
                "auto_update": False
            }
        }
    
    def _install(self, config: Dict[str, Any]) -> bool:
        """Install core component"""
        self.logger.info("Installing SuperClaude core framework files...")

        profile = (config or {}).get("memory_profile", "minimal").lower()
        all_files = set(self._discover_component_files())

        if profile == "full":
            selected_files = sorted(all_files)
            self.logger.debug("Using full memory profile for core component")
        else:
            minimal_files = [fname for fname in self.MINIMAL_FILES if fname in all_files]
            missing = [fname for fname in self.MINIMAL_FILES if fname not in all_files]
            if missing:
                self.logger.warning(
                    "Minimal profile files missing from source directory: %s",
                    missing,
                )
            selected_files = minimal_files or sorted(all_files)
            self.logger.info(
                "Applying minimal memory profile for core component (%d files)",
                len(selected_files)
            )

        self.component_files = selected_files
        self._selected_profile = profile

        return super()._install(config)

    def _post_install(self) -> bool:
        # Create or update metadata with corruption recovery
        try:
            # Check for corrupted metadata and recover if needed
            metadata_file = self.install_dir / '.superclaude-metadata.json'
            if metadata_file.exists():
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        json.load(f)
                    self.logger.debug("Existing metadata is valid")
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.warning(f"Corrupted metadata detected: {e}")
                    # Backup corrupted file
                    backup_path = metadata_file.with_suffix(f'.json.corrupted.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                    shutil.move(str(metadata_file), str(backup_path))
                    self.logger.info(f"Corrupted metadata backed up to: {backup_path.name}")

            # Update metadata with framework configuration
            metadata_mods = self.get_metadata_modifications()
            self.settings_manager.update_metadata(metadata_mods)
            self.logger.info("Updated metadata with framework configuration")

            # Add component registration to metadata
            self.settings_manager.add_component_registration("core", {
                "version": __version__,
                "category": "core",
                "files_count": len(self.component_files),
                "files": list(self.component_files),
                "memory_profile": getattr(self, "_selected_profile", "minimal"),
            })

            self.logger.info("Updated metadata with core component registration")

            # Migrate any existing SuperClaude data from settings.json
            if self.settings_manager.migrate_superclaude_data():
                self.logger.info("Migrated existing SuperClaude data from settings.json")

        except Exception as e:
            self.logger.error(f"Failed to update metadata: {e}")
            # Don't fail installation for metadata issues - log warning and continue
            self.logger.warning("Installation continuing without metadata update. Run 'SuperClaude clean --metadata' if issues persist.")
            # Return True to allow installation to complete

        # Create additional directories for other components
        additional_dirs = ["commands", "backups", "logs"]
        for dirname in additional_dirs:
            dir_path = self.install_dir / dirname
            if not self.file_manager.ensure_directory(dir_path):
                self.logger.warning(f"Could not create directory: {dir_path}")
        
        # Update CLAUDE.md with core framework imports
        try:
            manager = CLAUDEMdService(self.install_dir)
            manager.add_imports(self.component_files, category="Core Framework")
            self.logger.info("Updated CLAUDE.md with core framework imports")
        except Exception as e:
            self.logger.warning(f"Failed to update CLAUDE.md with core framework imports: {e}")
            # Don't fail the whole installation for this

        return True

    
    def uninstall(self) -> bool:
        """Uninstall core component"""
        try:
            self.logger.info("Uninstalling SuperClaude core component...")
            
            # Remove framework files
            removed_count = 0
            for filename in self.component_files:
                file_path = self.install_dir / filename
                if self.file_manager.remove_file(file_path):
                    removed_count += 1
                    self.logger.debug(f"Removed {filename}")
                else:
                    self.logger.warning(f"Could not remove {filename}")
            
            # Update metadata to remove core component
            try:
                if self.settings_manager.is_component_installed("core"):
                    self.settings_manager.remove_component_registration("core")
                    metadata_mods = self.get_metadata_modifications()
                    metadata = self.settings_manager.load_metadata()
                    for key in metadata_mods.keys():
                        if key in metadata:
                            del metadata[key]

                    self.settings_manager.save_metadata(metadata)
                    self.logger.info("Removed core component from metadata")
            except Exception as e:
                self.logger.warning(f"Could not update metadata: {e}")
            
            self.logger.info(f"✓ Core component uninstalled ({removed_count} files removed)")
            return True
            
        except Exception as e:
            self.logger.exception(f"Unexpected error during core uninstallation: {e}")
            return False
    
    def get_dependencies(self) -> List[str]:
        """Get component dependencies (core has none)"""
        return []
    
    def update(self, config: Dict[str, Any]) -> bool:
        """Update core component"""
        try:
            self.logger.info("Updating SuperClaude core component...")
            
            # Check current version
            current_version = self.settings_manager.get_component_version("core")
            target_version = self.get_metadata()["version"]
            
            if current_version == target_version:
                self.logger.info(f"Core component already at version {target_version}")
                return True
            
            self.logger.info(f"Updating core component from {current_version} to {target_version}")
            
            # Create backup of existing files
            backup_files = []
            for filename in self.component_files:
                file_path = self.install_dir / filename
                if file_path.exists():
                    backup_path = self.file_manager.backup_file(file_path)
                    if backup_path:
                        backup_files.append(backup_path)
                        self.logger.debug(f"Backed up {filename}")
            
            # Perform installation (overwrites existing files)
            success = self.install(config)
            
            if success:
                # Remove backup files on successful update
                for backup_path in backup_files:
                    try:
                        backup_path.unlink()
                    except Exception:
                        pass  # Ignore cleanup errors
                
                self.logger.info(f"✓ Core component updated to version {target_version}")
            else:
                # Restore from backup on failure
                self.logger.warning("Update failed, restoring from backup...")
                for backup_path in backup_files:
                    try:
                        original_path = backup_path.with_suffix('')
                        shutil.move(str(backup_path), str(original_path))
                        self.logger.debug(f"Restored {original_path.name}")
                    except Exception as e:
                        self.logger.error(f"Could not restore {backup_path}: {e}")
            
            return success
            
        except Exception as e:
            self.logger.exception(f"Unexpected error during core update: {e}")
            return False
    
    def validate_installation(self) -> Tuple[bool, List[str]]:
        """Validate core component installation"""
        errors = []

        files_to_check = self._get_installed_file_manifest() or self.component_files

        # Check if all framework files exist
        for filename in files_to_check:
            file_path = self.install_dir / filename
            if not file_path.exists():
                errors.append(f"Missing framework file: {filename}")
            elif not file_path.is_file():
                errors.append(f"Framework file is not a regular file: {filename}")
        
        # Check metadata registration
        if not self.settings_manager.is_component_installed("core"):
            errors.append("Core component not registered in metadata")
        else:
            # Check version matches
            installed_version = self.settings_manager.get_component_version("core")
            expected_version = self.get_metadata()["version"]
            if installed_version != expected_version:
                errors.append(f"Version mismatch: installed {installed_version}, expected {expected_version}")
        
        # Check metadata structure
        try:
            framework_config = self.settings_manager.get_metadata_setting("framework")
            if not framework_config:
                errors.append("Missing framework configuration in metadata")
            else:
                required_keys = ["version", "name", "description"]
                for key in required_keys:
                    if key not in framework_config:
                        errors.append(f"Missing framework.{key} in metadata")
        except Exception as e:
            errors.append(f"Could not validate metadata: {e}")

        return len(errors) == 0, errors

    def _get_installed_file_manifest(self) -> Optional[List[str]]:
        try:
            components = self.settings_manager.get_installed_components()
            info = components.get("core") or {}
            files = info.get("files")
            if isinstance(files, list) and files:
                return files
        except Exception as exc:
            self.logger.debug(f"Could not read installed file manifest: {exc}")
        return None
    
    def _get_source_dir(self):
        """Get source directory for framework files"""
        # Assume we're in SuperClaude/setup/components/core.py
        # and framework files are in SuperClaude/SuperClaude/Core/
        project_root = Path(__file__).parent.parent.parent
        return project_root / "SuperClaude" / "Core"
    
    def get_size_estimate(self) -> int:
        """Get estimated installation size"""
        total_size = 0
        source_dir = self._get_source_dir()
        
        for filename in self.component_files:
            file_path = source_dir / filename
            if file_path.exists():
                total_size += file_path.stat().st_size
        
        # Add overhead for settings.json and directories
        total_size += 10240  # ~10KB overhead
        
        return total_size
    
    def get_installation_summary(self) -> Dict[str, Any]:
        """Get installation summary"""
        return {
            "component": self.get_metadata()["name"],
            "version": self.get_metadata()["version"],
            "files_installed": len(self.component_files),
            "framework_files": self.component_files,
            "estimated_size": self.get_size_estimate(),
            "install_directory": str(self.install_dir),
            "dependencies": self.get_dependencies()
        }
