"""
Behavioral Modes System for SuperClaude Framework

Provides different operational modes that change how the framework behaves,
from exploratory brainstorming to ultra-efficient token compression.
"""

from .behavioral_manager import (
    BehavioralMode,
    BehavioralModeManager,
    ModeConfiguration,
    ModeTransition,
)

__all__ = [
    "BehavioralMode",
    "BehavioralModeManager",
    "ModeConfiguration",
    "ModeTransition",
]

__version__ = "1.0.0"
