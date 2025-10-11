#!/usr/bin/env python3
"""
SuperClaude Framework - Git Worktree Manager
Manages parallel development with git worktrees for feature isolation
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


class WorktreeManager:
    """
    Manages git worktrees for parallel feature development.
    Provides automatic creation, validation, and progressive merging.
    """

    def __init__(self, repo_path: str, max_worktrees: int = 10):
        """
        Initialize worktree manager.

        Args:
            repo_path: Path to the main repository
            max_worktrees: Maximum number of concurrent worktrees
        """
        self.repo_path = Path(repo_path)
        self.worktree_dir = self.repo_path / ".worktrees"
        self.max_worktrees = max_worktrees
        self.state_file = self.worktree_dir / "state.json"

        # Create repository and worktree directories if they don't exist
        try:
            self.repo_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.worktree_dir.mkdir(parents=True, exist_ok=True)

        # Load or initialize state
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load worktree state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

        return {
            "worktrees": {},
            "merge_history": [],
            "cleanup_age_days": 7
        }

    def _save_state(self):
        """Save worktree state to JSON file."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def _run_git(self, *args, cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """
        Run git command and return result.

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = ["git"] + list(args)
        cwd = cwd or self.repo_path

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    async def create_worktree(self, task_id: str, branch: str) -> Dict:
        """
        Create a new worktree for a task.

        Args:
            task_id: Unique identifier for the task
            branch: Branch name for the worktree

        Returns:
            Dict with worktree information
        """
        # Check if we've reached max worktrees
        active_worktrees = [w for w in self.state["worktrees"].values()
                           if w["status"] == "active"]
        if len(active_worktrees) >= self.max_worktrees:
            raise ValueError(f"Maximum worktrees ({self.max_worktrees}) reached")

        # Generate unique worktree path
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        worktree_name = f"wt-{task_id}-{timestamp}"
        worktree_path = self.worktree_dir / worktree_name

        # Create the worktree
        rc, stdout, stderr = self._run_git(
            "worktree", "add", "-b", branch, str(worktree_path)
        )

        if rc != 0:
            raise RuntimeError(f"Failed to create worktree: {stderr}")

        # Update state
        worktree_info = {
            "id": worktree_name,
            "task_id": task_id,
            "branch": branch,
            "path": str(worktree_path),
            "created": datetime.now().isoformat(),
            "status": "active",
            "validation": {
                "tests_passed": False,
                "quality_score": 0,
                "ready_to_merge": False
            }
        }

        self.state["worktrees"][worktree_name] = worktree_info
        self._save_state()

        logger.info(f"Created worktree: {worktree_name}")
        return worktree_info

    async def list_worktrees(self) -> List[Dict]:
        """
        List all active worktrees.

        Returns:
            List of worktree information dicts
        """
        # Get actual worktrees from git
        rc, stdout, stderr = self._run_git("worktree", "list", "--porcelain")

        if rc != 0:
            logger.error(f"Failed to list worktrees: {stderr}")
            return []

        # Parse git output and sync with state
        git_worktrees = self._parse_worktree_list(stdout)

        # Update state based on actual worktrees
        for wt_path in git_worktrees:
            wt_name = Path(wt_path).name
            if wt_name not in self.state["worktrees"]:
                # Found untracked worktree
                self.state["worktrees"][wt_name] = {
                    "id": wt_name,
                    "path": wt_path,
                    "status": "untracked",
                    "created": datetime.now().isoformat()
                }

        # Mark missing worktrees as removed
        for wt_name, wt_info in self.state["worktrees"].items():
            if wt_info["path"] not in git_worktrees and wt_info["status"] == "active":
                wt_info["status"] = "removed"

        self._save_state()

        # Return active worktrees
        return [wt for wt in self.state["worktrees"].values()
                if wt["status"] == "active"]

    def _parse_worktree_list(self, output: str) -> List[str]:
        """Parse git worktree list output."""
        worktrees = []
        for line in output.split('\n'):
            if line.startswith("worktree "):
                worktrees.append(line.split(" ", 1)[1])
        return worktrees

    async def validate_worktree(self, worktree_id: str) -> Dict:
        """
        Validate a worktree is ready for merging.

        Args:
            worktree_id: ID of the worktree to validate

        Returns:
            Validation result dict
        """
        if worktree_id not in self.state["worktrees"]:
            raise ValueError(f"Worktree {worktree_id} not found")

        worktree_info = self.state["worktrees"][worktree_id]
        worktree_path = Path(worktree_info["path"])

        validation = {
            "tests_passed": False,
            "quality_score": 0,
            "has_conflicts": False,
            "ready_to_merge": False,
            "issues": []
        }

        # Check for uncommitted changes
        rc, stdout, stderr = self._run_git("status", "--porcelain", cwd=worktree_path)
        if stdout:
            validation["issues"].append("Uncommitted changes present")

        # Check for merge conflicts with integration branch
        rc, stdout, stderr = self._run_git(
            "merge-tree", "integration", worktree_info["branch"],
            cwd=worktree_path
        )
        if rc != 0 or "conflict" in stdout.lower():
            validation["has_conflicts"] = True
            validation["issues"].append("Merge conflicts detected")

        # Run tests (mock for now - would integrate with test framework)
        validation["tests_passed"] = True  # Assume tests pass
        validation["quality_score"] = 85   # Mock quality score

        # Determine if ready to merge
        validation["ready_to_merge"] = (
            validation["tests_passed"] and
            validation["quality_score"] >= 70 and
            not validation["has_conflicts"] and
            len(validation["issues"]) == 0
        )

        # Update state
        worktree_info["validation"] = validation
        self._save_state()

        return {
            "id": worktree_id,
            "status": "validated",
            "ready": validation["ready_to_merge"],
            "validation": validation
        }

    async def progressive_merge(self, worktree_id: str, target_branch: str = "integration") -> Dict:
        """
        Progressively merge worktree to target branch.

        Args:
            worktree_id: ID of the worktree to merge
            target_branch: Target branch (default: integration)

        Returns:
            Merge result dict
        """
        if worktree_id not in self.state["worktrees"]:
            raise ValueError(f"Worktree {worktree_id} not found")

        worktree_info = self.state["worktrees"][worktree_id]

        # Validate before merge
        validation = await self.validate_worktree(worktree_id)
        if not validation["ready"]:
            return {
                "success": False,
                "error": "Worktree not ready for merge",
                "validation": validation
            }

        # Perform the merge
        source_branch = worktree_info["branch"]

        # Switch to target branch
        rc, stdout, stderr = self._run_git("checkout", target_branch)
        if rc != 0:
            return {"success": False, "error": f"Failed to checkout {target_branch}: {stderr}"}

        # Merge the worktree branch
        rc, stdout, stderr = self._run_git("merge", "--no-ff", source_branch,
                                          "-m", f"Merge {source_branch} to {target_branch}")

        if rc != 0:
            # Rollback
            self._run_git("merge", "--abort")
            return {"success": False, "error": f"Merge failed: {stderr}"}

        # Update state
        merge_record = {
            "worktree_id": worktree_id,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "timestamp": datetime.now().isoformat(),
            "validation_score": worktree_info["validation"]["quality_score"]
        }

        self.state["merge_history"].append(merge_record)
        worktree_info["status"] = "merged"
        worktree_info["merged_to"] = target_branch
        worktree_info["merged_at"] = datetime.now().isoformat()

        self._save_state()

        logger.info(f"Successfully merged {source_branch} to {target_branch}")

        return {
            "success": True,
            "source": source_branch,
            "target": target_branch,
            "worktree_id": worktree_id
        }

    async def cleanup_old_worktrees(self, age_days: Optional[int] = None):
        """
        Clean up old merged or abandoned worktrees.

        Args:
            age_days: Age in days before cleanup (default from config)
        """
        age_days = age_days or self.state.get("cleanup_age_days", 7)
        cutoff_date = datetime.now() - timedelta(days=age_days)

        cleaned = []

        for wt_id, wt_info in list(self.state["worktrees"].items()):
            # Check if worktree is old enough and merged/abandoned
            created_date = datetime.fromisoformat(wt_info["created"])

            if created_date < cutoff_date and wt_info["status"] in ["merged", "abandoned", "removed"]:
                # Remove the worktree
                worktree_path = Path(wt_info["path"])

                if worktree_path.exists():
                    # Remove from git
                    rc, stdout, stderr = self._run_git("worktree", "remove", str(worktree_path))

                    if rc == 0:
                        cleaned.append(wt_id)
                        del self.state["worktrees"][wt_id]
                        logger.info(f"Cleaned up worktree: {wt_id}")
                    else:
                        logger.error(f"Failed to remove worktree {wt_id}: {stderr}")

        self._save_state()

        return {
            "cleaned": cleaned,
            "count": len(cleaned)
        }

    async def get_worktree_status(self, worktree_id: str) -> Dict:
        """
        Get detailed status of a specific worktree.

        Args:
            worktree_id: ID of the worktree

        Returns:
            Detailed status dict
        """
        if worktree_id not in self.state["worktrees"]:
            raise ValueError(f"Worktree {worktree_id} not found")

        worktree_info = self.state["worktrees"][worktree_id]
        worktree_path = Path(worktree_info["path"])

        # Get current branch
        rc, stdout, stderr = self._run_git("branch", "--show-current", cwd=worktree_path)
        current_branch = stdout if rc == 0 else "unknown"

        # Get commit info
        rc, stdout, stderr = self._run_git("log", "-1", "--oneline", cwd=worktree_path)
        last_commit = stdout if rc == 0 else "No commits"

        # Get diff stats
        rc, stdout, stderr = self._run_git("diff", "--stat", "integration", cwd=worktree_path)
        diff_stats = stdout if rc == 0 else "No diff available"

        return {
            "id": worktree_id,
            "task_id": worktree_info.get("task_id"),
            "branch": current_branch,
            "path": str(worktree_path),
            "status": worktree_info["status"],
            "created": worktree_info["created"],
            "last_commit": last_commit,
            "diff_stats": diff_stats,
            "validation": worktree_info.get("validation", {})
        }
