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
    - create_obsidian_hooks(): Factory for Obsidian vault integration hooks
"""

from .events_hooks import EventsTracker, create_events_hooks, create_iteration_callback
from .evidence import EvidenceCollector
from .hooks import create_evidence_hooks, create_safety_hooks, create_sdk_hooks
from .loop_runner import LoopConfig, LoopResult, run_agentic_loop
from .obsidian_hooks import create_obsidian_hooks, merge_obsidian_hooks
from .quality import QualityAssessment, assess_quality

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
    # Obsidian integration
    "create_obsidian_hooks",
    "merge_obsidian_hooks",
    # Events integration (Zed panel)
    "EventsTracker",
    "create_events_hooks",
    "create_iteration_callback",
]
