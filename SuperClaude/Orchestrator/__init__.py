"""
SuperClaude Orchestrator - Agentic Loop with Official Anthropic Agent SDK

This module provides programmatic control over Claude execution using the
Official Anthropic Agent SDK hooks system.

Architecture:
    User -> superclaude --loop -> SDK query() with hooks -> Claude executes
           (SuperClaude orchestrates)

Key Components:
    - EvidenceCollector: Accumulates evidence from SDK hooks during execution
    - create_sdk_hooks(): Factory for safety and evidence collection hooks
    - run_agentic_loop(): Main entry point for iterative execution
    - assess_quality(): Scores output based on collected evidence
"""

from .evidence import EvidenceCollector
from .hooks import create_sdk_hooks, create_safety_hooks, create_evidence_hooks
from .quality import assess_quality, QualityAssessment
from .loop_runner import run_agentic_loop, LoopResult, LoopConfig

__all__ = [
    "EvidenceCollector",
    "create_sdk_hooks",
    "create_safety_hooks",
    "create_evidence_hooks",
    "assess_quality",
    "QualityAssessment",
    "run_agentic_loop",
    "LoopResult",
    "LoopConfig",
]
