"""
Core Agents for SuperClaude Framework

This module exports all core agent implementations that provide
fundamental capabilities for the framework.
"""

from .general_purpose import GeneralPurposeAgent
from .learning_guide import LearningGuide
from .performance import PerformanceEngineer
from .refactoring import RefactoringExpert
from .root_cause import RootCauseAnalyst
from .technical_writer import TechnicalWriter

__all__ = [
    "GeneralPurposeAgent",
    "LearningGuide",
    "PerformanceEngineer",
    "RefactoringExpert",
    "RootCauseAnalyst",
    "TechnicalWriter",
]

# Agent metadata for discovery
CORE_AGENTS = {
    "general-purpose": GeneralPurposeAgent,
    "root-cause-analyst": RootCauseAnalyst,
    "refactoring-expert": RefactoringExpert,
    "technical-writer": TechnicalWriter,
    "performance-engineer": PerformanceEngineer,
    "learning-guide": LearningGuide,
}
