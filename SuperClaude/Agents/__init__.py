"""
SuperClaude Agent System

A modular agent framework for specialized task execution with
context-aware selection and delegation capabilities.

Features:
- 130+ agents across core and extended categories
- Intelligent agent selection with multi-criteria scoring
- Lazy loading with LRU cache optimization
- 10 specialized categories
- Performance-optimized with access pattern tracking
"""

from .base import BaseAgent

# Import core agents
from .core import (
    GeneralPurposeAgent,
    LearningGuide,
    PerformanceEngineer,
    RefactoringExpert,
    RootCauseAnalyst,
    TechnicalWriter,
)

# Extended agent system
from .extended_loader import (
    AgentCategory,
    AgentMetadata,
    ExtendedAgentLoader,
    MatchScore,
)
from .generic import GenericMarkdownAgent
from .loader import AgentLoader
from .parser import AgentMarkdownParser
from .registry import AgentRegistry
from .selector import AgentSelector

__all__ = [
    # Base classes
    "BaseAgent",
    # System components
    "AgentRegistry",
    "AgentSelector",
    "AgentLoader",
    "AgentMarkdownParser",
    "GenericMarkdownAgent",
    # Extended agent system
    "ExtendedAgentLoader",
    "AgentCategory",
    "AgentMetadata",
    "MatchScore",
    # Core agents
    "GeneralPurposeAgent",
    "RootCauseAnalyst",
    "RefactoringExpert",
    "TechnicalWriter",
    "PerformanceEngineer",
    "LearningGuide",
]

# Version information
__version__ = "6.0.0-alpha"
