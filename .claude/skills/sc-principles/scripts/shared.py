#!/usr/bin/env python3
"""Shared utilities for principle validators.

Centralizes common functionality used across all principle validators
(SOLID, KISS, Purity, Let It Crash) to eliminate code duplication.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def find_python_files(scope_root: Path, changed_only: bool = True) -> list[Path]:
    """Find Python files to analyze.

    Uses a single git command to get all changed files (staged, unstaged,
    untracked) instead of 3 separate subprocess calls.

    Args:
        scope_root: Root directory to search from.
        changed_only: If True, only return files changed in git.
            Falls back to rglob if git is unavailable or no files found.

    Returns:
        List of Python file paths to analyze.
    """
    if changed_only:
        try:
            # Single git status call replaces 3 separate subprocess calls.
            # --porcelain=v1 gives stable, parseable output.
            # -uall shows individual untracked files.
            result = subprocess.run(
                ["git", "status", "--porcelain=v1", "-uall"],
                capture_output=True,
                text=True,
                cwd=scope_root,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                all_files: set[str] = set()
                for line in result.stdout.strip().split("\n"):
                    if len(line) < 4:
                        continue
                    # porcelain format: XY filename
                    # or XY orig -> renamed for renames
                    file_part = line[3:]
                    if " -> " in file_part:
                        file_part = file_part.split(" -> ")[-1]
                    all_files.add(file_part)

                py_files = [
                    scope_root / f
                    for f in all_files
                    if f.endswith(".py") and (scope_root / f).exists()
                ]

                if py_files:
                    return sorted(py_files)
        # LET-IT-CRASH-EXCEPTION: OPTIONAL_FEATURE - git may not be installed
        # or directory may not be a repo; fall back to rglob for broad scanning
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(
                f"Warning: git-based file discovery failed ({e}); falling back to rglob.",
                file=sys.stderr,
            )

    return sorted(scope_root.rglob("*.py"))
