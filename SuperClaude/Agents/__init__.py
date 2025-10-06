"""
SuperClaude Agent System

A modular agent framework for specialized task execution with
context-aware selection and delegation capabilities.
"""

from .base import BaseAgent
from .registry import AgentRegistry
from .selector import AgentSelector
from .loader import AgentLoader
from .parser import AgentMarkdownParser
from .generic import GenericMarkdownAgent

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

    # Core agents
    'GeneralPurposeAgent',
    'RootCauseAnalyst',
    'RefactoringExpert',
    'TechnicalWriter',
    'PerformanceEngineer'
]

# Version information
__version__ = '5.0.0-alpha'