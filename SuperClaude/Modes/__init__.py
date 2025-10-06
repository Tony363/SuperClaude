"""
Behavioral Modes System for SuperClaude Framework

Provides different operational modes that change how the framework behaves,
from exploratory brainstorming to ultra-efficient token compression.
"""

from .behavioral_manager import (
    BehavioralModeManager,
    BehavioralMode,
    ModeConfiguration,
    ModeTransition
)

__all__ = [
    'BehavioralModeManager',
    'BehavioralMode',
    'ModeConfiguration',
    'ModeTransition'
]

__version__ = '1.0.0'