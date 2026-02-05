"""
SuperClaude Services Module
Business logic services for the SuperClaude installation system
"""

from .claude_md import CLAUDEMdService
from .config import ConfigService
from .files import FileService
from .obsidian_artifact import DecisionRecord, ObsidianArtifactWriter
from .obsidian_config import ObsidianConfig, ObsidianConfigService
from .obsidian_context import ObsidianContextGenerator, generate_obsidian_context
from .obsidian_md import ObsidianMdService, setup_obsidian_integration
from .obsidian_vault import ObsidianNote, ObsidianVaultService
from .settings import SettingsService

__all__ = [
    "CLAUDEMdService",
    "ConfigService",
    "FileService",
    "SettingsService",
    # Obsidian integration
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
