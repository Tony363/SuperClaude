"""
SuperClaude Core - Lightweight Loop Orchestration

This module provides the agentic loop functionality for SuperClaude v6.0.0.
It implements a hybrid architecture where Python orchestrates loop mechanics
while Skills (SKILL.md) define what agents do.

Key components:
- LoopOrchestrator: Main loop controller with safety mechanisms
- TerminationReason: Enum of loop termination conditions
- QualityAssessor: Integration with evidence_gate.py for scoring
- PALReviewSignal: Signal generation for PAL MCP integration

Safety guarantees:
- HARD_MAX_ITERATIONS = 5 (cannot be overridden)
- Oscillation detection (prevents infinite back-and-forth)
- Stagnation detection (stops when no progress)
- Minimum improvement threshold (stops if < 5 point gain)
"""

from .types import (
    TerminationReason,
    LoopConfig,
    LoopResult,
    IterationResult,
    QualityAssessment,
)
from .termination import detect_oscillation, detect_stagnation
from .quality_assessment import QualityAssessor
from .pal_integration import PALReviewSignal
from .loop_orchestrator import LoopOrchestrator

__all__ = [
    # Types
    "TerminationReason",
    "LoopConfig",
    "LoopResult",
    "IterationResult",
    "QualityAssessment",
    # Functions
    "detect_oscillation",
    "detect_stagnation",
    # Classes
    "QualityAssessor",
    "PALReviewSignal",
    "LoopOrchestrator",
]

__version__ = "6.0.0"
