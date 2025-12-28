"""
Skills System for SuperClaude Framework.

Provides Agent Skills format support with bidirectional adapter
between SKILL.md files and Python CommandMetadata registry.
"""

from .adapter import SkillAdapter, SkillMetadata
from .discovery import SkillDiscovery
from .runtime import RuntimeConfig, SkillRuntime

__all__ = [
    "SkillAdapter",
    "SkillDiscovery",
    "SkillMetadata",
    "SkillRuntime",
    "RuntimeConfig",
]

__version__ = "1.0.0"
