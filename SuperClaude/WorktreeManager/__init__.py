"""
Git Worktree Management System for SuperClaude Framework.

Provides automated worktree lifecycle management for parallel feature
development with progressive merge workflows.
"""

from .manager import MergeTarget, Worktree, WorktreeManager, WorktreeStatus
from .state import WorktreeState, WorktreeStateManager

__all__ = [
    "MergeTarget",
    "Worktree",
    "WorktreeManager",
    "WorktreeState",
    "WorktreeStateManager",
    "WorktreeStatus",
]

__version__ = "1.0.0"
