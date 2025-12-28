#!/usr/bin/env python3
"""
SuperClaude Framework - Git Worktree Manager
Manages parallel development with git worktrees for feature isolation
"""

import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from SuperClaude.Quality.quality_scorer import QualityScorer

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
        except Exception as e:
            # Directory creation failed; may already exist or permission issue
            logger.debug(f"Could not create repo_path directory: {e}")
        self.worktree_dir.mkdir(parents=True, exist_ok=True)

        # Load or initialize state
        self.state = self._load_state()
        self.quality_scorer = QualityScorer()

    def _load_state(self) -> dict:
        """Load worktree state from JSON file."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

        return {"worktrees": {}, "merge_history": [], "cleanup_age_days": 7}

    def _save_state(self):
        """Save worktree state to JSON file."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def _run_git(self, *args, cwd: Path | None = None) -> tuple[int, str, str]:
        """
        Run git command and return result.

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = ["git"] + list(args)
        cwd = cwd or self.repo_path

        try:
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    def apply_changes(
        self,
        changes: Sequence[dict[str, Any]],
        *,
        worktree_id: str | None = None,
        mode: str = "replace",
    ) -> dict[str, Any]:
        """Apply proposed changes to the repository or a specific worktree.

        Args:
            changes: Sequence of change descriptors. Each descriptor must include
                a ``path`` (relative to the repository root) and ``content``.
            worktree_id: Optional worktree identifier indicating where to apply
                the changes. When omitted, the main repository is used.
            mode: File write mode – ``replace`` (default) overwrites the file
                contents, ``append`` appends to the existing file.

        Returns:
            Dictionary containing applied paths and any warnings encountered.
        """

        if not changes:
            return {
                "applied": [],
                "warnings": ["No changes provided"],
                "base_path": str(self.repo_path),
            }

        base_path = self.repo_path
        session_id = "repository"

        if worktree_id:
            worktree_info = self.state.get("worktrees", {}).get(worktree_id)
            if not worktree_info:
                return {
                    "applied": [],
                    "warnings": [f"Worktree {worktree_id} not found"],
                    "base_path": str(self.repo_path),
                }
            base_path = Path(worktree_info.get("path", self.repo_path))
            session_id = worktree_id

        applied: list[str] = []
        warnings: list[str] = []

        for change in changes:
            rel_path = change.get("path")
            if not rel_path:
                warnings.append("Change is missing a target path")
                continue

            rel_path = Path(rel_path)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                warnings.append(f"Invalid path outside repository: {rel_path}")
                continue

            target_path = (base_path / rel_path).resolve()

            try:
                target_path.relative_to(base_path.resolve())
            except ValueError:
                warnings.append(f"Path escapes base directory: {rel_path}")
                continue

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                warnings.append(f"Failed creating directories for {rel_path}: {exc}")
                continue

            content = change.get("content", "")
            encoding = change.get("encoding", "utf-8")
            write_mode = change.get("mode", mode)

            try:
                if write_mode == "append" and target_path.exists():
                    with target_path.open("a", encoding=encoding) as handle:
                        handle.write(content)
                else:
                    target_path.write_text(str(content), encoding=encoding)
            except Exception as exc:
                warnings.append(f"Failed to write {rel_path}: {exc}")
                continue

            applied.append(str(target_path.relative_to(self.repo_path)))

        return {
            "applied": applied,
            "warnings": warnings,
            "base_path": str(base_path),
            "session": session_id,
        }

    async def create_worktree(self, task_id: str, branch: str) -> dict:
        """
        Create a new worktree for a task.

        Args:
            task_id: Unique identifier for the task
            branch: Branch name for the worktree

        Returns:
            Dict with worktree information
        """
        # Check if we've reached max worktrees
        active_worktrees = [
            w for w in self.state["worktrees"].values() if w["status"] == "active"
        ]
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
                "ready_to_merge": False,
            },
        }

        self.state["worktrees"][worktree_name] = worktree_info
        self._save_state()

        logger.info(f"Created worktree: {worktree_name}")
        return worktree_info

    async def list_worktrees(self) -> list[dict]:
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
                    "created": datetime.now().isoformat(),
                }

        # Mark missing worktrees as removed
        for wt_name, wt_info in self.state["worktrees"].items():
            if wt_info["path"] not in git_worktrees and wt_info["status"] == "active":
                wt_info["status"] = "removed"

        self._save_state()

        # Return active worktrees
        return [
            wt for wt in self.state["worktrees"].values() if wt["status"] == "active"
        ]

    def _parse_worktree_list(self, output: str) -> list[str]:
        """Parse git worktree list output."""
        worktrees = []
        for line in output.split("\n"):
            if line.startswith("worktree "):
                worktrees.append(line.split(" ", 1)[1])
        return worktrees

    def _run_tests(self, worktree_path: Path) -> dict[str, Any]:
        """Run the project's test suite inside the worktree."""
        command_str = os.environ.get("SUPERCLAUDE_WORKTREE_TEST_CMD")
        command = (
            shlex.split(command_str)
            if command_str
            else [sys.executable, "-m", "pytest", "--maxfail=1", "-q"]
        )
        env = os.environ.copy()
        env.setdefault("PYENV_DISABLE_REHASH", "1")

        def _to_text(value: bytes | None) -> str:
            if value is None:
                return ""
            return (
                value.decode("utf-8", errors="ignore")
                if isinstance(value, bytes)
                else value
            )

        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=600,
                env=env,
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            duration = time.time() - start_time
        except FileNotFoundError as exc:
            return {
                "passed": False,
                "return_code": 127,
                "stdout": "",
                "stderr": str(exc),
                "duration": 0.0,
                "command": " ".join(command),
                "errors": [str(exc)],
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_errored": 0,
                "tests_skipped": 0,
                "tests_collected": 0,
                "pass_rate": 0.0,
                "summary": None,
                "coverage": None,
            }
        except subprocess.TimeoutExpired as exc:
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr)
            duration = time.time() - start_time
            summary = self._parse_test_summary(f"{stdout}\n{stderr}")
            summary.update(
                {
                    "passed": False,
                    "return_code": 124,
                    "stdout": stdout,
                    "stderr": stderr or "Test command timed out",
                    "duration": duration,
                    "command": " ".join(command),
                }
            )
            summary.setdefault("errors", []).append("Test command timed out")
            if summary.get("pass_rate") is None:
                summary["pass_rate"] = 0.0
            return summary

        summary = self._parse_test_summary(f"{stdout}\n{stderr}")
        passed = result.returncode == 0
        if summary.get("pass_rate") is None:
            summary["pass_rate"] = 1.0 if passed else 0.0

        errors: list[str] = summary.get("errors", [])
        if summary.get("tests_failed", 0):
            errors.append(f"{summary['tests_failed']} test(s) failed")
        if summary.get("tests_errored", 0):
            errors.append(f"{summary['tests_errored']} test(s) errored")
        if not passed and not errors and stderr.strip():
            errors.append(stderr.strip().splitlines()[-1])

        summary.update(
            {
                "passed": passed,
                "return_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration": duration,
                "command": " ".join(command),
                "errors": errors,
            }
        )

        return summary

    def _parse_test_summary(self, output: str) -> dict[str, Any]:
        """Parse pytest summary output into structured metrics."""
        summary: dict[str, Any] = {
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_errored": 0,
            "tests_skipped": 0,
            "tests_collected": None,
            "pass_rate": None,
            "summary": None,
            "coverage": None,
        }

        lines = output.splitlines()
        summary_line = None
        for line in lines:
            stripped = line.strip()
            if re.match(r"=+\s+.+\s+ =+", stripped):
                summary_line = stripped
        if summary_line:
            summary["summary"] = summary_line

        collected_match = re.search(r"collected\s+(\d+)\s+items?", output)
        if collected_match:
            summary["tests_collected"] = int(collected_match.group(1))

        for count, label in re.findall(
            r"(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed)", output
        ):
            value = int(count)
            normalized = label.rstrip("s")
            if normalized == "passed":
                summary["tests_passed"] += value
            elif normalized == "failed":
                summary["tests_failed"] += value
            elif normalized == "error":
                summary["tests_errored"] += value
            elif normalized == "skipped" or normalized == "xfailed":
                summary["tests_skipped"] += value
            elif normalized == "xpassed":
                summary["tests_passed"] += value

        executed = (
            summary["tests_passed"] + summary["tests_failed"] + summary["tests_errored"]
        )
        if summary["tests_collected"] is None and executed:
            summary["tests_collected"] = executed + summary["tests_skipped"]
        if executed:
            summary["pass_rate"] = summary["tests_passed"] / executed

        coverage_match = re.search(
            r"coverage[:\s]+(\d+(?:\.\d+)?)%", output, re.IGNORECASE
        )
        if not coverage_match:
            coverage_match = re.search(
                r"TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%", output
            )
        if coverage_match:
            try:
                summary["coverage"] = float(coverage_match.group(1)) / 100.0
            except (TypeError, ValueError):
                summary["coverage"] = None

        return summary

    def _build_quality_context(
        self,
        test_results: dict[str, Any],
        validation: dict[str, Any],
        worktree_path: Path,
    ) -> dict[str, Any]:
        """Build context dictionary for quality scoring."""
        pass_rate = test_results.get("pass_rate")
        if pass_rate is None:
            pass_rate = 1.0 if test_results.get("passed") else 0.0

        tests_collected = test_results.get("tests_collected")
        if tests_collected is None:
            tests_collected = (
                test_results.get("tests_passed", 0)
                + test_results.get("tests_failed", 0)
                + test_results.get("tests_errored", 0)
            )

        context: dict[str, Any] = {
            "test_results": {
                "pass_rate": pass_rate,
                "tests_collected": tests_collected,
                "coverage": test_results.get("coverage"),
                "summary": test_results.get("summary"),
                "passed": test_results.get("passed", False),
            },
            "metrics": {},
        }

        duration = test_results.get("duration")
        if isinstance(duration, (int, float)):
            # Convert seconds to milliseconds for comparison against 1000ms target
            context["metrics"]["response_time"] = duration * 1000.0

        return context

    async def validate_worktree(self, worktree_id: str) -> dict:
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
            "issues": [],
        }

        # Check for uncommitted changes
        rc, stdout, stderr = self._run_git("status", "--porcelain", cwd=worktree_path)
        if stdout:
            validation["issues"].append("Uncommitted changes present")

        # Check for merge conflicts with integration branch
        rc, stdout, stderr = self._run_git(
            "merge-tree", "integration", worktree_info["branch"], cwd=worktree_path
        )
        if rc != 0 or "conflict" in stdout.lower():
            validation["has_conflicts"] = True
            validation["issues"].append("Merge conflicts detected")

        # Run tests and capture detailed results
        test_results = self._run_tests(worktree_path)
        validation["test_results"] = test_results
        validation["tests_passed"] = test_results.get("passed", False)

        if not validation["tests_passed"]:
            validation["issues"].append("Test suite failed")
            if test_results.get("errors"):
                validation["issues"].extend(test_results["errors"])

        # Calculate quality score using quality scorer
        quality_context = self._build_quality_context(
            test_results, validation, worktree_path
        )
        output_summary = {
            "success": validation["tests_passed"] and not validation["has_conflicts"],
            "errors": test_results.get("errors", []),
        }

        assessment = self.quality_scorer.evaluate(output_summary, quality_context)
        validation["quality_score"] = round(assessment.overall_score, 2)
        validation["quality_threshold"] = self.quality_scorer.threshold
        validation["quality_dimensions"] = {
            metric.dimension.value: {
                "score": round(metric.score, 2),
                "issues": metric.issues,
                "suggestions": metric.suggestions,
            }
            for metric in assessment.metrics
        }
        validation["improvements"] = assessment.improvements_needed

        if not assessment.passed:
            validation["issues"].append("Quality threshold not met")
            if assessment.improvements_needed:
                validation["issues"].extend(assessment.improvements_needed[:3])

        # Determine if ready to merge
        validation["ready_to_merge"] = (
            validation["tests_passed"]
            and validation["quality_score"] >= validation.get("quality_threshold", 70)
            and not validation["has_conflicts"]
            and len(validation["issues"]) == 0
        )

        # Update state
        worktree_info["validation"] = validation
        self._save_state()

        return {
            "id": worktree_id,
            "status": "validated",
            "ready": validation["ready_to_merge"],
            "validation": validation,
        }

    async def progressive_merge(
        self, worktree_id: str, target_branch: str = "integration"
    ) -> dict:
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
                "validation": validation,
            }

        # Perform the merge
        source_branch = worktree_info["branch"]

        # Switch to target branch
        rc, stdout, stderr = self._run_git("checkout", target_branch)
        if rc != 0:
            return {
                "success": False,
                "error": f"Failed to checkout {target_branch}: {stderr}",
            }

        # Merge the worktree branch
        rc, stdout, stderr = self._run_git(
            "merge",
            "--no-ff",
            source_branch,
            "-m",
            f"Merge {source_branch} to {target_branch}",
        )

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
            "validation_score": worktree_info["validation"]["quality_score"],
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
            "worktree_id": worktree_id,
        }

    async def cleanup_old_worktrees(self, age_days: int | None = None):
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

            if created_date < cutoff_date and wt_info["status"] in [
                "merged",
                "abandoned",
                "removed",
            ]:
                # Remove the worktree
                worktree_path = Path(wt_info["path"])

                if worktree_path.exists():
                    # Remove from git
                    rc, stdout, stderr = self._run_git(
                        "worktree", "remove", str(worktree_path)
                    )

                    if rc == 0:
                        cleaned.append(wt_id)
                        del self.state["worktrees"][wt_id]
                        logger.info(f"Cleaned up worktree: {wt_id}")
                    else:
                        logger.error(f"Failed to remove worktree {wt_id}: {stderr}")

        self._save_state()

        return {"cleaned": cleaned, "count": len(cleaned)}

    async def get_worktree_status(self, worktree_id: str) -> dict:
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
        rc, stdout, stderr = self._run_git(
            "branch", "--show-current", cwd=worktree_path
        )
        current_branch = stdout if rc == 0 else "unknown"

        # Get commit info
        rc, stdout, stderr = self._run_git("log", "-1", "--oneline", cwd=worktree_path)
        last_commit = stdout if rc == 0 else "No commits"

        # Get diff stats
        rc, stdout, stderr = self._run_git(
            "diff", "--stat", "integration", cwd=worktree_path
        )
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
            "validation": worktree_info.get("validation", {}),
        }
