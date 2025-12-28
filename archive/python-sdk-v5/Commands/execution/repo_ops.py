"""
Repository operations service for SuperClaude Commands.

Handles Git snapshot, diff, and apply operations.
"""

import logging
import os
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RepoAndWorktreeService:
    """
    Service for repository and worktree operations.

    Handles:
    - Git snapshot and diff operations
    - Change plan application
    - Build artifact cleanup
    - Static validation
    """

    def __init__(
        self,
        repo_root: Path | None = None,
        worktree_manager: Any | None = None,
    ):
        """
        Initialize repo operations service.

        Args:
            repo_root: Repository root path
            worktree_manager: Optional WorktreeManager instance
        """
        self.repo_root = repo_root or Path.cwd()
        self.worktree_manager = worktree_manager

    def snapshot_repo_changes(self) -> set[str]:
        """Capture current git worktree changes for comparison."""
        if not self.repo_root or not (self.repo_root / ".git").exists():
            return set()

        snapshot: set[str] = set()
        commands = [
            ["git", "diff", "--name-status"],
            ["git", "diff", "--name-status", "--cached"],
        ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd, cwd=self.repo_root, capture_output=True, text=True, check=False
                )
            except Exception as exc:
                logger.debug(f"Failed to run {' '.join(cmd)}: {exc}")
                return set()

            if result.returncode != 0:
                continue

            for line in result.stdout.splitlines():
                entry = line.strip()
                if entry:
                    snapshot.add(entry)

        try:
            result = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    path = line.strip()
                    if path:
                        snapshot.add(f"??\t{path}")
        except Exception as exc:
            logger.debug(f"Failed to list untracked files: {exc}")

        return snapshot

    def diff_snapshots(self, before: set[str], after: set[str]) -> list[str]:
        """Return new repo changes detected between snapshots."""
        if not after:
            return []
        if not before:
            return sorted(after)
        return sorted(after - before)

    def partition_change_entries(
        self, entries: Iterable[str]
    ) -> tuple[list[str], list[str]]:
        """Separate artifact-only changes from potential evidence."""
        artifact_entries: list[str] = []
        evidence_entries: list[str] = []

        for entry in entries:
            if self._is_artifact_change(entry):
                artifact_entries.append(entry)
            else:
                evidence_entries.append(entry)

        return artifact_entries, evidence_entries

    def _is_artifact_change(self, entry: str) -> bool:
        """Heuristically detect whether a change originates from command artifacts."""
        parts = entry.split("\t")
        if len(parts) < 2:
            return False

        candidate = parts[-1].strip()
        return candidate.startswith("SuperClaude/Generated/") or candidate.startswith(
            ".worktrees/"
        )

    def format_change_entry(self, entry: str) -> str:
        """Convert a git name-status entry into a human readable description."""
        parts = entry.split("\t")
        if not parts:
            return entry

        code = parts[0]
        code_letter = code[0] if code else "?"

        if code.startswith("??") and len(parts) >= 2:
            return f"add {parts[1]}"

        if code_letter == "M" and len(parts) >= 2:
            return f"modify {parts[1]}"

        if code_letter == "A" and len(parts) >= 2:
            return f"add {parts[1]}"

        if code_letter == "D" and len(parts) >= 2:
            return f"delete {parts[1]}"

        if code_letter == "R" and len(parts) >= 3:
            return f"rename {parts[1]} -> {parts[2]}"

        if code_letter == "C" and len(parts) >= 3:
            return f"copy {parts[1]} -> {parts[2]}"

        if len(parts) >= 2:
            return f"{code_letter.lower()} {parts[1]}"

        return entry

    def run_command(
        self,
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: dict[str, Any] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a system command and capture its output.

        Returns:
            Dictionary containing command metadata, stdout, stderr, exit code, duration,
            and an optional error indicator.
        """
        args = [str(part) for part in command]
        working_dir = Path(cwd or self.repo_root or Path.cwd())
        runtime_env = os.environ.copy()
        runtime_env.setdefault("PYENV_DISABLE_REHASH", "1")
        if env:
            runtime_env.update({str(key): str(value) for key, value in env.items()})

        start = datetime.now()
        try:
            result = subprocess.run(
                args,
                cwd=str(working_dir),
                capture_output=True,
                text=True,
                env=runtime_env,
                timeout=timeout,
                check=False,
            )
            duration = (datetime.now() - start).total_seconds()
            stdout_text = (result.stdout or "").strip()
            stderr_text = (result.stderr or "").strip()
            output = {
                "command": " ".join(args),
                "args": args,
                "cwd": str(working_dir),
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": result.returncode,
                "duration_s": duration,
            }
            if result.returncode != 0:
                output["error"] = f"exit code {result.returncode}"
            return output
        except subprocess.TimeoutExpired as exc:
            duration = (datetime.now() - start).total_seconds()
            stdout_text = getattr(exc, "stdout", "") or ""
            stderr_text = getattr(exc, "stderr", "") or ""
            return {
                "command": " ".join(args),
                "args": args,
                "cwd": str(working_dir),
                "stdout": stdout_text.strip(),
                "stderr": (stderr_text or "Command timed out").strip(),
                "exit_code": None,
                "duration_s": duration,
                "error": "timeout",
            }
        except Exception as exc:
            duration = (datetime.now() - start).total_seconds()
            return {
                "command": " ".join(args),
                "args": args,
                "cwd": str(working_dir),
                "stdout": "",
                "stderr": str(exc),
                "exit_code": None,
                "duration_s": duration,
                "error": str(exc),
            }

    def collect_diff_stats(self) -> list[str]:
        """Collect diff statistics for working and staged changes."""
        if not self.repo_root or not (self.repo_root / ".git").exists():
            return []

        stats: list[str] = []
        commands = [
            ("working", ["git", "diff", "--stat"]),
            ("staged", ["git", "diff", "--stat", "--cached"]),
        ]

        for label, cmd in commands:
            try:
                result = subprocess.run(
                    cmd, cwd=self.repo_root, capture_output=True, text=True, check=False
                )
            except Exception as exc:
                logger.debug(f"Failed to gather diff stats ({label}): {exc}")
                continue

            output = result.stdout.strip()
            if output:
                truncated = self._truncate_output(output)
                stats.append(f"diff --stat ({label}): {truncated}")

        return stats

    def _truncate_output(self, text: str, max_len: int = 500) -> str:
        """Truncate output text to max length."""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."

    def clean_build_artifacts(self, repo_root: Path) -> tuple[list[str], list[str]]:
        """Remove common build artifacts when a clean build is requested."""
        removed: list[str] = []
        errors: list[str] = []
        targets = [
            "build",
            "dist",
            "htmlcov",
            ".pytest_cache",
            "SuperClaude.egg-info",
        ]

        for target in targets:
            path = repo_root / target
            if not path.exists():
                continue
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed.append(str(path.relative_to(repo_root)))
            except Exception as exc:
                errors.append(f"{target}: {exc}")

        return removed, errors

    def git_has_modifications(self, file_path: Path) -> bool:
        """Check whether git reports pending changes for the path."""
        if not self.repo_root or not (self.repo_root / ".git").exists():
            return False

        try:
            rel_path = file_path.relative_to(self.repo_root)
        except ValueError:
            return False

        try:
            result = subprocess.run(
                ["git", "status", "--short", "--", str(rel_path)],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return False

        if result.returncode != 0:
            return False

        output = result.stdout.strip()
        if not output:
            return False

        status = output.splitlines()[0][:2]
        if status == "??":
            return False
        return True

    def extract_changed_paths(
        self, repo_entries: list[str], applied_changes: list[str]
    ) -> list[Path]:
        """Derive candidate file paths that were reported as changed."""
        if not self.repo_root:
            return []

        candidates: list[str] = []

        for entry in repo_entries:
            parts = entry.split("\t")
            if not parts:
                continue
            code = parts[0]
            if code.startswith("??") and len(parts) >= 2:
                candidates.append(parts[1])
            elif (code.startswith("R") or code.startswith("C")) and len(parts) >= 3:
                candidates.append(parts[2])
            elif len(parts) >= 2:
                candidates.append(parts[1])

        for change in applied_changes:
            tokens = change.split()
            if not tokens:
                continue
            verb = tokens[0].lower()
            if (verb in {"add", "modify", "delete"} and len(tokens) >= 2) or (
                verb in {"rename", "copy"} and len(tokens) >= 3
            ):
                candidates.append(tokens[-1])

        seen: set[str] = set()
        paths: list[Path] = []
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate or candidate.startswith("diff"):
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            path = (self.repo_root / candidate).resolve()
            try:
                path.relative_to(self.repo_root)
            except ValueError:
                continue
            paths.append(path)

        return paths

    def relative_to_repo_path(self, path: Path | str) -> str:
        """Convert path to relative path from repo root."""
        path = Path(path)
        try:
            return str(path.relative_to(self.repo_root))
        except ValueError:
            return str(path)
