"""
Worktree State Management for SuperClaude Framework.

Provides state persistence and tracking using the UnifiedStore backend.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from SuperClaude.Core.unified_store import UnifiedStore

logger = logging.getLogger(__name__)


@dataclass
class WorktreeState:
    """State information for a worktree."""

    worktree_name: str
    task_id: str
    branch: str
    created_at: str
    last_updated: str
    status: str
    validation_status: Dict[str, Any] = field(default_factory=dict)
    merge_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorktreeStateManager:
    """
    Manages persistent state for worktrees.

    Features:
    - State serialization and persistence
    - UnifiedStore-backed project memory
    - Validation tracking
    - Merge history
    - Resource monitoring
    """

    STATE_FILE = ".worktrees/state.json"

    def __init__(
        self, repo_path: Optional[str] = None, store: Optional[UnifiedStore] = None
    ):
        """
        Initialize state manager.

        Args:
            repo_path: Path to repository
            store: Optional UnifiedStore instance for dependency injection
        """
        self.repo_path = Path(repo_path or ".")
        self.state_file = self.repo_path / self.STATE_FILE
        self.store = store or UnifiedStore()
        self.states: Dict[str, WorktreeState] = {}

        # Load existing state
        self.load_state()

    def load_state(self) -> None:
        """Load state from disk and UnifiedStore."""
        # Load from disk
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    for name, state_data in data.get("worktrees", {}).items():
                        self.states[name] = WorktreeState(**state_data)
                logger.info(f"Loaded {len(self.states)} worktree states")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

        self._load_from_store()

    def _load_from_store(self) -> None:
        """Load state from UnifiedStore."""
        try:
            memories = self.store.list_memories(prefix="worktree_")
            for memory_key in memories:
                memory_data = self.store.read_memory(memory_key)
                if memory_data and "worktree_name" in memory_data:
                    state = WorktreeState(**memory_data)
                    self.states[state.worktree_name] = state
                    logger.debug(
                        f"Loaded worktree state from store: {state.worktree_name}"
                    )
        except Exception as e:  # pragma: no cover - defensive logging
            logger.warning(f"Failed to load worktree states from UnifiedStore: {e}")

    def save_state(self) -> None:
        """Save state to disk and UnifiedStore."""
        # Prepare data
        data = {
            "version": "1.0.0",
            "updated_at": datetime.now().isoformat(),
            "worktrees": {name: asdict(state) for name, state in self.states.items()},
        }

        # Save to disk
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.states)} worktree states to disk")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

        self._save_to_store()

    def _save_to_store(self) -> None:
        """Persist worktree state to UnifiedStore."""
        try:
            for name, state in self.states.items():
                memory_key = f"worktree_{name}"
                self.store.write_memory(memory_key, asdict(state))
                logger.debug(f"Saved worktree state to store: {name}")

        except Exception as e:  # pragma: no cover - defensive logging
            logger.warning(f"Failed to save worktree states to UnifiedStore: {e}")

    def update_state(self, worktree_name: str, **kwargs) -> WorktreeState:
        """
        Update or create worktree state.

        Args:
            worktree_name: Name of the worktree
            **kwargs: State fields to update

        Returns:
            Updated WorktreeState
        """
        if worktree_name in self.states:
            state = self.states[worktree_name]
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            state.last_updated = datetime.now().isoformat()
        else:
            # Create new state
            state = WorktreeState(
                worktree_name=worktree_name,
                task_id=kwargs.get("task_id", ""),
                branch=kwargs.get("branch", ""),
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                status=kwargs.get("status", "active"),
                validation_status=kwargs.get("validation_status", {}),
                merge_history=kwargs.get("merge_history", []),
                metadata=kwargs.get("metadata", {}),
            )
            self.states[worktree_name] = state

        # Auto-save
        self.save_state()

        return state

    def get_state(self, worktree_name: str) -> Optional[WorktreeState]:
        """
        Get state for a worktree.

        Args:
            worktree_name: Name of the worktree

        Returns:
            WorktreeState or None
        """
        return self.states.get(worktree_name)

    def remove_state(self, worktree_name: str) -> None:
        """
        Remove state for a worktree.

        Args:
            worktree_name: Name of the worktree
        """
        if worktree_name in self.states:
            del self.states[worktree_name]

            try:
                memory_key = f"worktree_{worktree_name}"
                self.store.delete_memory(memory_key)
            except Exception:
                pass

            self.save_state()
            logger.debug(f"Removed state for worktree: {worktree_name}")

    def record_validation(
        self, worktree_name: str, passed: bool, issues: List[str]
    ) -> None:
        """
        Record validation results for a worktree.

        Args:
            worktree_name: Name of the worktree
            passed: Whether validation passed
            issues: List of validation issues
        """
        state = self.get_state(worktree_name)
        if not state:
            state = self.update_state(worktree_name)

        state.validation_status = {
            "passed": passed,
            "issues": issues,
            "checked_at": datetime.now().isoformat(),
        }

        if passed:
            state.status = "ready_to_merge"

        self.save_state()

    def record_merge(
        self, worktree_name: str, target_branch: str, success: bool, message: str
    ) -> None:
        """
        Record merge operation for a worktree.

        Args:
            worktree_name: Name of the worktree
            target_branch: Target branch for merge
            success: Whether merge succeeded
            message: Merge result message
        """
        state = self.get_state(worktree_name)
        if not state:
            state = self.update_state(worktree_name)

        merge_record = {
            "target_branch": target_branch,
            "success": success,
            "message": message,
            "merged_at": datetime.now().isoformat(),
        }

        state.merge_history.append(merge_record)

        if success:
            state.status = "merged"

        self.save_state()

    def get_task_worktrees(self, task_id: str) -> List[WorktreeState]:
        """
        Get all worktrees for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of WorktreeState objects
        """
        return [state for state in self.states.values() if state.task_id == task_id]

    def get_active_worktrees(self) -> List[WorktreeState]:
        """Get all active worktrees."""
        return [state for state in self.states.values() if state.status == "active"]

    def get_ready_to_merge(self) -> List[WorktreeState]:
        """Get worktrees ready to merge."""
        return [
            state for state in self.states.values() if state.status == "ready_to_merge"
        ]

    def get_resource_usage(self) -> Dict[str, Any]:
        """
        Calculate resource usage across all worktrees.

        Returns:
            Resource usage statistics
        """
        usage = {
            "total_worktrees": len(self.states),
            "active": 0,
            "ready_to_merge": 0,
            "merged": 0,
            "disk_usage_mb": 0,
            "oldest_worktree": None,
            "newest_worktree": None,
        }

        oldest_date = None
        newest_date = None

        for state in self.states.values():
            # Count by status
            if state.status == "active":
                usage["active"] += 1
            elif state.status == "ready_to_merge":
                usage["ready_to_merge"] += 1
            elif state.status == "merged":
                usage["merged"] += 1

            # Track oldest/newest
            created = datetime.fromisoformat(state.created_at)
            if not oldest_date or created < oldest_date:
                oldest_date = created
                usage["oldest_worktree"] = state.worktree_name

            if not newest_date or created > newest_date:
                newest_date = created
                usage["newest_worktree"] = state.worktree_name

        # Calculate disk usage (approximate)
        worktree_dir = self.repo_path / ".worktrees"
        if worktree_dir.exists():
            try:
                total_size = sum(
                    f.stat().st_size for f in worktree_dir.rglob("*") if f.is_file()
                )
                usage["disk_usage_mb"] = total_size / (1024 * 1024)
            except:
                pass

        return usage

    def cleanup_old_states(self, days: int = 30) -> int:
        """
        Clean up states older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of states cleaned up
        """
        cutoff_date = datetime.now()
        removed = 0

        to_remove = []
        for name, state in self.states.items():
            if state.status == "merged":
                last_updated = datetime.fromisoformat(state.last_updated)
                age_days = (cutoff_date - last_updated).days
                if age_days > days:
                    to_remove.append(name)

        for name in to_remove:
            self.remove_state(name)
            removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old worktree states")

        return removed

    def export_summary(self) -> str:
        """
        Export summary of all worktree states.

        Returns:
            Formatted summary string
        """
        lines = ["# Worktree State Summary\n"]

        # Group by status
        by_status = {}
        for state in self.states.values():
            if state.status not in by_status:
                by_status[state.status] = []
            by_status[state.status].append(state)

        # Format each group
        for status, states in by_status.items():
            lines.append(f"\n## {status.upper()} ({len(states)} worktrees)")
            for state in states:
                lines.append(f"- **{state.worktree_name}**")
                lines.append(f"  - Task: {state.task_id}")
                lines.append(f"  - Branch: {state.branch}")
                lines.append(f"  - Created: {state.created_at}")
                if state.validation_status:
                    passed = state.validation_status.get("passed", False)
                    lines.append(
                        f"  - Validation: {'✅ Passed' if passed else '❌ Failed'}"
                    )

        # Add resource usage
        usage = self.get_resource_usage()
        lines.append("\n## Resource Usage")
        lines.append(f"- Total Worktrees: {usage['total_worktrees']}")
        lines.append(f"- Disk Usage: {usage['disk_usage_mb']:.2f} MB")

        return "\n".join(lines)

    def cleanup(self) -> None:
        """Release any resources held by the manager."""
        try:
            self.store.close()
        except Exception:
            pass

    def __del__(self) -> None:
        self.cleanup()
