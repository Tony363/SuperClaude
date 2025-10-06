"""
Core Agents for SuperClaude Framework

This module exports all core agent implementations that provide
fundamental capabilities for the framework.
"""

from .general_purpose import GeneralPurposeAgent
from .root_cause import RootCauseAnalyst
from .refactoring import RefactoringExpert
from .technical_writer import TechnicalWriter
from .performance import PerformanceEngineer

__all__ = [
    'GeneralPurposeAgent',
    'RootCauseAnalyst',
    'RefactoringExpert',
    'TechnicalWriter',
    'PerformanceEngineer'
]

# Agent metadata for discovery
CORE_AGENTS = {
    'general-purpose': GeneralPurposeAgent,
    'root-cause-analyst': RootCauseAnalyst,
    'refactoring-expert': RefactoringExpert,
    'technical-writer': TechnicalWriter,
    'performance-engineer': PerformanceEngineer
}