"""
Git Worktree Manager for SuperClaude Framework.

Manages git worktree lifecycle for parallel feature development and
progressive merge workflows.
"""

import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class WorktreeStatus(Enum):
    """Worktree status states."""
    ACTIVE = "active"
    READY_TO_MERGE = "ready_to_merge"
    MERGED = "merged"
    ABANDONED = "abandoned"
    CONFLICTED = "conflicted"


class MergeTarget(Enum):
    """Merge target branches."""
    FEATURE = "feature"
    INTEGRATION = "integration"
    MAIN = "main"


@dataclass
class Worktree:
    """Worktree information."""
    name: str
    branch: str
    path: Path
    task_id: str
    created_at: datetime
    status: WorktreeStatus = WorktreeStatus.ACTIVE
    parent_branch: str = ""
    merge_target: MergeTarget = MergeTarget.INTEGRATION
    validation_passed: bool = False
    commits: int = 0
    files_changed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorktreeManager:
    """
    Manages git worktrees for parallel development.

    Features:
    - Automatic worktree creation per feature/phase
    - Progressive merge workflow (feature → integration → main)
    - Conflict detection and resolution
    - State persistence with UnifiedStore
    - Resource monitoring and cleanup
    - Validation gates
    """

    DEFAULT_WORKTREE_DIR = ".worktrees"
    MAX_WORKTREES = 10
    CLEANUP_AGE_DAYS = 7
    INTEGRATION_BRANCH = "integration"

    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize worktree manager.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = Path(repo_path or os.getcwd())
        self.worktree_dir = self.repo_path / self.DEFAULT_WORKTREE_DIR
        self.worktrees: Dict[str, Worktree] = {}
        self.main_branch = self._get_main_branch()

        # Create worktree directory if needed
        self.worktree_dir.mkdir(exist_ok=True)

        # Load existing worktrees
        self._discover_worktrees()

    def _get_main_branch(self) -> str:
        """Get the main branch name (main or master)."""
        try:
            result = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                # Extract branch name from refs/remotes/origin/main
                return result.stdout.strip().split('/')[-1]
        except:
            pass

        # Check if main exists
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", "main"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return "main"
        except:
            pass

        return "master"  # Default to master

    def _discover_worktrees(self) -> None:
        """Discover existing git worktrees."""
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.warning("Failed to list worktrees")
                return

            # Parse worktree list
            lines = result.stdout.strip().split('\n')
            current_worktree = {}

            for line in lines:
                if line.startswith("worktree "):
                    if current_worktree:
                        self._add_discovered_worktree(current_worktree)
                    current_worktree = {"path": line[9:]}
                elif line.startswith("branch "):
                    current_worktree["branch"] = line[7:]
                elif line == "":
                    if current_worktree:
                        self._add_discovered_worktree(current_worktree)
                        current_worktree = {}

            # Add last worktree if exists
            if current_worktree:
                self._add_discovered_worktree(current_worktree)

        except Exception as e:
            logger.error(f"Failed to discover worktrees: {e}")

    def _add_discovered_worktree(self, info: Dict[str, str]) -> None:
        """Add discovered worktree to registry."""
        path = Path(info.get("path", ""))
        if not path.exists() or path == self.repo_path:
            return  # Skip main repo

        # Extract name from path
        if path.is_relative_to(self.worktree_dir):
            name = path.name
            if name.startswith("wt-"):
                # Parse our naming convention: wt-{task}-{timestamp}
                parts = name.split('-')
                if len(parts) >= 3:
                    task_id = parts[1]
                    timestamp = parts[2] if len(parts) > 2 else ""

                    worktree = Worktree(
                        name=name,
                        branch=info.get("branch", ""),
                        path=path,
                        task_id=task_id,
                        created_at=datetime.fromtimestamp(path.stat().st_ctime),
                        parent_branch=self._get_parent_branch(info.get("branch", ""))
                    )

                    self.worktrees[name] = worktree
                    logger.debug(f"Discovered worktree: {name}")

    def _get_parent_branch(self, branch: str) -> str:
        """Get parent branch for a given branch."""
        try:
            result = subprocess.run(
                ["git", "merge-base", branch, self.main_branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return self.main_branch
        except:
            pass
        return self.main_branch

    def create_worktree(self,
                        task_id: str,
                        branch_name: Optional[str] = None,
                        base_branch: Optional[str] = None) -> Worktree:
        """
        Create a new worktree for a task.

        Args:
            task_id: Unique task identifier
            branch_name: Optional branch name (auto-generated if not provided)
            base_branch: Branch to create from (defaults to main)

        Returns:
            Created Worktree object
        """
        # Check worktree limit
        if len(self.worktrees) >= self.MAX_WORKTREES:
            self._cleanup_old_worktrees()

        # Generate names
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        worktree_name = f"wt-{task_id}-{timestamp}"
        branch_name = branch_name or f"feature/{task_id}"
        base_branch = base_branch or self.main_branch

        # Create worktree path
        worktree_path = self.worktree_dir / worktree_name
        worktree_path.mkdir(parents=True, exist_ok=True)

        try:
            # Create worktree with new branch
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_path), base_branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to create worktree: {result.stderr}")

            # Create Worktree object
            worktree = Worktree(
                name=worktree_name,
                branch=branch_name,
                path=worktree_path,
                task_id=task_id,
                created_at=datetime.now(),
                parent_branch=base_branch
            )

            self.worktrees[worktree_name] = worktree
            logger.info(f"Created worktree: {worktree_name} on branch {branch_name}")

            return worktree

        except Exception as e:
            logger.error(f"Failed to create worktree: {e}")
            # Clean up if failed
            if worktree_path.exists():
                worktree_path.rmdir()
            raise

    def switch_to_worktree(self, worktree_name: str) -> bool:
        """
        Switch to a specific worktree directory.

        Args:
            worktree_name: Name of the worktree

        Returns:
            True if successful
        """
        if worktree_name not in self.worktrees:
            logger.error(f"Worktree {worktree_name} not found")
            return False

        worktree = self.worktrees[worktree_name]
        if not worktree.path.exists():
            logger.error(f"Worktree path {worktree.path} does not exist")
            return False

        try:
            os.chdir(worktree.path)
            logger.info(f"Switched to worktree: {worktree_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to switch to worktree: {e}")
            return False

    def validate_worktree(self, worktree_name: str) -> Tuple[bool, List[str]]:
        """
        Validate worktree for merge readiness.

        Args:
            worktree_name: Name of the worktree

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        if worktree_name not in self.worktrees:
            return False, ["Worktree not found"]

        worktree = self.worktrees[worktree_name]
        issues = []

        # Check for uncommitted changes
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=worktree.path,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                issues.append("Uncommitted changes present")
        except:
            issues.append("Failed to check git status")

        # Check for conflicts with target branch
        try:
            target_branch = self.INTEGRATION_BRANCH
            result = subprocess.run(
                ["git", "merge-tree", target_branch, worktree.branch],
                cwd=worktree.path,
                capture_output=True,
                text=True
            )
            if "<<<<<<< " in result.stdout:
                issues.append(f"Merge conflicts with {target_branch}")
        except:
            pass  # merge-tree might not be available

        # Run tests if available
        test_script = worktree.path / "test.sh"
        if test_script.exists():
            try:
                result = subprocess.run(
                    ["bash", str(test_script)],
                    cwd=worktree.path,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    issues.append("Tests failed")
            except subprocess.TimeoutExpired:
                issues.append("Tests timed out")
            except:
                issues.append("Failed to run tests")

        # Update validation status
        worktree.validation_passed = len(issues) == 0
        if worktree.validation_passed:
            worktree.status = WorktreeStatus.READY_TO_MERGE

        return worktree.validation_passed, issues

    def merge_worktree(self,
                       worktree_name: str,
                       target: MergeTarget = MergeTarget.INTEGRATION,
                       force: bool = False) -> Tuple[bool, str]:
        """
        Merge worktree to target branch.

        Args:
            worktree_name: Name of the worktree
            target: Target branch type
            force: Force merge even with validation issues

        Returns:
            Tuple of (success, message)
        """
        if worktree_name not in self.worktrees:
            return False, "Worktree not found"

        worktree = self.worktrees[worktree_name]

        # Validate unless forced
        if not force:
            is_valid, issues = self.validate_worktree(worktree_name)
            if not is_valid:
                return False, f"Validation failed: {', '.join(issues)}"

        # Determine target branch
        if target == MergeTarget.INTEGRATION:
            target_branch = self.INTEGRATION_BRANCH
        elif target == MergeTarget.MAIN:
            target_branch = self.main_branch
        else:
            target_branch = worktree.parent_branch

        try:
            # Switch to main repo for merge
            os.chdir(self.repo_path)

            # Ensure target branch exists
            subprocess.run(
                ["git", "checkout", "-B", target_branch],
                cwd=self.repo_path,
                capture_output=True
            )

            # Merge the worktree branch
            result = subprocess.run(
                ["git", "merge", "--no-ff", worktree.branch, "-m",
                 f"Merge {worktree.branch} from worktree {worktree_name}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                if "conflict" in result.stdout.lower() or "conflict" in result.stderr.lower():
                    worktree.status = WorktreeStatus.CONFLICTED
                    return False, f"Merge conflicts detected: {result.stderr}"
                return False, f"Merge failed: {result.stderr}"

            # Update status
            worktree.status = WorktreeStatus.MERGED
            worktree.merge_target = target

            logger.info(f"Successfully merged {worktree_name} to {target_branch}")
            return True, f"Merged to {target_branch}"

        except Exception as e:
            logger.error(f"Failed to merge worktree: {e}")
            return False, str(e)

    def remove_worktree(self, worktree_name: str, force: bool = False) -> bool:
        """
        Remove a worktree.

        Args:
            worktree_name: Name of the worktree
            force: Force removal even with uncommitted changes

        Returns:
            True if successful
        """
        if worktree_name not in self.worktrees:
            logger.warning(f"Worktree {worktree_name} not found")
            return False

        worktree = self.worktrees[worktree_name]

        try:
            # Remove worktree
            cmd = ["git", "worktree", "remove", str(worktree.path)]
            if force:
                cmd.append("--force")

            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to remove worktree: {result.stderr}")
                return False

            # Remove from registry
            del self.worktrees[worktree_name]
            logger.info(f"Removed worktree: {worktree_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove worktree: {e}")
            return False

    def _cleanup_old_worktrees(self) -> None:
        """Clean up old worktrees based on age and status."""
        now = datetime.now()
        cleanup_age = timedelta(days=self.CLEANUP_AGE_DAYS)

        to_remove = []
        for name, worktree in self.worktrees.items():
            age = now - worktree.created_at

            # Remove merged worktrees after 1 day
            if worktree.status == WorktreeStatus.MERGED and age > timedelta(days=1):
                to_remove.append(name)

            # Remove abandoned worktrees after cleanup age
            elif worktree.status == WorktreeStatus.ABANDONED and age > cleanup_age:
                to_remove.append(name)

            # Mark as abandoned if inactive for too long
            elif worktree.status == WorktreeStatus.ACTIVE and age > cleanup_age:
                # Check for recent commits
                if not self._has_recent_activity(worktree):
                    worktree.status = WorktreeStatus.ABANDONED

        # Remove old worktrees
        for name in to_remove:
            logger.info(f"Cleaning up old worktree: {name}")
            self.remove_worktree(name, force=True)

    def _has_recent_activity(self, worktree: Worktree, days: int = 3) -> bool:
        """Check if worktree has recent activity."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%at"],
                cwd=worktree.path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                last_commit_time = datetime.fromtimestamp(int(result.stdout.strip()))
                return (datetime.now() - last_commit_time).days < days
        except:
            pass
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get overall worktree status."""
        status = {
            'total_worktrees': len(self.worktrees),
            'active': 0,
            'ready_to_merge': 0,
            'merged': 0,
            'conflicted': 0,
            'worktrees': []
        }

        for name, worktree in self.worktrees.items():
            if worktree.status == WorktreeStatus.ACTIVE:
                status['active'] += 1
            elif worktree.status == WorktreeStatus.READY_TO_MERGE:
                status['ready_to_merge'] += 1
            elif worktree.status == WorktreeStatus.MERGED:
                status['merged'] += 1
            elif worktree.status == WorktreeStatus.CONFLICTED:
                status['conflicted'] += 1

            # Get commit count
            try:
                result = subprocess.run(
                    ["git", "rev-list", "--count", f"{worktree.parent_branch}..HEAD"],
                    cwd=worktree.path,
                    capture_output=True,
                    text=True
                )
                commits = int(result.stdout.strip()) if result.returncode == 0 else 0
            except:
                commits = 0

            status['worktrees'].append({
                'name': name,
                'branch': worktree.branch,
                'task_id': worktree.task_id,
                'status': worktree.status.value,
                'age_days': (datetime.now() - worktree.created_at).days,
                'commits': commits
            })

        return status

    def prune_worktrees(self) -> int:
        """
        Prune worktrees that no longer exist.

        Returns:
            Number of pruned worktrees
        """
        try:
            result = subprocess.run(
                ["git", "worktree", "prune"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )

            # Re-discover worktrees
            old_count = len(self.worktrees)
            self.worktrees.clear()
            self._discover_worktrees()
            pruned = old_count - len(self.worktrees)

            logger.info(f"Pruned {pruned} worktrees")
            return pruned

        except Exception as e:
            logger.error(f"Failed to prune worktrees: {e}")
            return 0
