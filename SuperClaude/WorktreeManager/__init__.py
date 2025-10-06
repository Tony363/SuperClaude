"""
Git Worktree Management System for SuperClaude Framework.

Provides automated worktree lifecycle management for parallel feature
development with progressive merge workflows.
"""

from .manager import WorktreeManager, Worktree, WorktreeStatus, MergeTarget
from .state import WorktreeStateManager, WorktreeState

__all__ = [
    'WorktreeManager',
    'Worktree',
    'WorktreeStatus',
    'MergeTarget',
    'WorktreeStateManager',
    'WorktreeState'
]

__version__ = '1.0.0'