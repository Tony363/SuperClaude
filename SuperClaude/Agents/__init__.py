"""
SuperClaude Agent System

A modular agent framework for specialized task execution with
context-aware selection and delegation capabilities.

Features:
- 141-agent system (14 core + 127 extended)
- Intelligent agent selection with multi-criteria scoring
- Lazy loading with LRU cache optimization
- 10 specialized categories
- Performance-optimized with access pattern tracking
"""

from .base import BaseAgent
from .registry import AgentRegistry
from .selector import AgentSelector
from .loader import AgentLoader
from .parser import AgentMarkdownParser
from .generic import GenericMarkdownAgent

# Extended agent system
from .extended_loader import (
    ExtendedAgentLoader,
    AgentCategory,
    AgentMetadata,
    MatchScore
)

# Import core agents
from .core import (
    GeneralPurposeAgent,
    RootCauseAnalyst,
    RefactoringExpert,
    TechnicalWriter,
    PerformanceEngineer
)

__all__ = [
    # Base classes
    'BaseAgent',

    # System components
    'AgentRegistry',
    'AgentSelector',
    'AgentLoader',
    'AgentMarkdownParser',
    'GenericMarkdownAgent',

    # Extended agent system
    'ExtendedAgentLoader',
    'AgentCategory',
    'AgentMetadata',
    'MatchScore',

    # Core agents
    'GeneralPurposeAgent',
    'RootCauseAnalyst',
    'RefactoringExpert',
    'TechnicalWriter',
    'PerformanceEngineer'
]

# Version information
__version__ = '6.0.0-alpha'
