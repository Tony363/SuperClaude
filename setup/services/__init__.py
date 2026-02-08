"""
SuperClaude Services Module
Business logic services for the SuperClaude installation system
"""

# Core services (no optional dependencies)
from .claude_md import CLAUDEMdService
from .config import ConfigService
from .files import FileService
from .settings import SettingsService

# Obsidian services require PyYAML (optional) — lazy-loaded via __getattr__
_OBSIDIAN_IMPORTS = {
    "DecisionRecord": "obsidian_artifact",
    "ObsidianArtifactWriter": "obsidian_artifact",
    "ObsidianConfig": "obsidian_config",
    "ObsidianConfigService": "obsidian_config",
    "ObsidianContextGenerator": "obsidian_context",
    "generate_obsidian_context": "obsidian_context",
    "ObsidianMdService": "obsidian_md",
    "setup_obsidian_integration": "obsidian_md",
    "ObsidianNote": "obsidian_vault",
    "ObsidianVaultService": "obsidian_vault",
}


def __getattr__(name: str):
    if name in _OBSIDIAN_IMPORTS:
        import importlib

        module = importlib.import_module(f".{_OBSIDIAN_IMPORTS[name]}", __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CLAUDEMdService",
    "ConfigService",
    "FileService",
    "SettingsService",
    "ObsidianConfig",
    "ObsidianConfigService",
    "ObsidianVaultService",
    "ObsidianNote",
    "ObsidianContextGenerator",
    "generate_obsidian_context",
    "ObsidianMdService",
    "setup_obsidian_integration",
    "ObsidianArtifactWriter",
    "DecisionRecord",
]
